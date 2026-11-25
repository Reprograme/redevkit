// Write lock of one installation (B14). init, update, target add/remove, rollback and uninstall
// take it before reading the manifest, so two of them never interleave on the same project.
//
// - The lock is `.redevkit/redevkit.lock`, created exclusively ("wx") with the owner's pid, host,
//   command and start time. While held, its mtime is refreshed (heartbeat) so a long prompt is not
//   mistaken for an abandoned lock.
// - A second command waits (polling) up to REDEVKIT_LOCK_WAIT_MS (default 15 s) and then fails with
//   a clear message, having changed nothing. The commands are short, so waiting turns two
//   simultaneous invocations into the serial result.
// - An orphan lock is taken over: owner process gone (same host), lock older than LOCK_STALE_MS
//   without a heartbeat, or an unreadable lock older than a few seconds.
// - It is released in `finally`, on process exit and on SIGINT (cli.js).
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { crossesLink, exists, readText } from "./fsutil.js";
import { setLang, t } from "./i18n.js";

export const LOCK_REL = ".redevkit/redevkit.lock";
export const LOCK_STALE_MS = 5 * 60 * 1000;
export const DEFAULT_LOCK_WAIT_MS = 15 * 1000;
const HEARTBEAT_MS = 30 * 1000;
const POLL_MS = 100;
const UNREADABLE_STALE_MS = 10 * 1000;

const held = new Map(); // lock path -> { timer, dir, createdDir, token }

export const lockWaitMs = () => {
  const v = Number(process.env.REDEVKIT_LOCK_WAIT_MS);
  return process.env.REDEVKIT_LOCK_WAIT_MS !== undefined && Number.isFinite(v) && v >= 0 ? v : DEFAULT_LOCK_WAIT_MS;
};

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

const pidAlive = (pid) => {
  if (!Number.isInteger(pid) || pid <= 0) return false;
  try {
    process.kill(pid, 0);
    return true;
  } catch (err) {
    return err.code === "EPERM"; // exists, owned by someone else
  }
};

/** Current lock: { raw, info (parsed or null), mtimeMs }, or null when there is none. */
const readLock = (abs) => {
  try {
    const st = fs.statSync(abs);
    const raw = fs.readFileSync(abs, "utf8");
    let info = null;
    try {
      info = JSON.parse(raw);
    } catch {
      info = null;
    }
    return { raw, info: info && typeof info === "object" ? info : null, mtimeMs: st.mtimeMs };
  } catch {
    return null;
  }
};

export const isStaleLock = (lock, now = Date.now()) => {
  const age = now - lock.mtimeMs;
  if (age > LOCK_STALE_MS) return true;
  if (!lock.info) return age > UNREADABLE_STALE_MS; // being written, or corrupt
  if (lock.info.host && lock.info.host !== os.hostname()) return false; // another machine: only age tells
  return !pidAlive(lock.info.pid);
};

/** Remove a stale lock, but only if it is still the very lock judged stale (same content and mtime). */
const removeStale = (abs, seen) => {
  const again = readLock(abs);
  if (!again || again.raw !== seen.raw || again.mtimeMs !== seen.mtimeMs) return;
  try {
    fs.unlinkSync(abs);
  } catch {
    // someone else removed it first
  }
};

export class LockBusyError extends Error {
  constructor(info) {
    super("Another REDEVKIT operation is running in this project");
    this.info = info ?? {};
  }
}

/**
 * Take the write lock of `projectDir`. Resolves to a handle with release(); rejects with
 * LockBusyError when another live operation still holds it after `waitMs`.
 * `onWait(info)` is called once when the lock is busy and the command starts waiting.
 */
export const acquireLock = async (projectDir, { command = "", waitMs = lockWaitMs(), onWait = null } = {}) => {
  const dir = path.join(projectDir, ".redevkit");
  const abs = path.join(dir, path.basename(LOCK_REL));
  if (held.has(abs)) return { path: abs, release: () => {} }; // re-entrant within one process
  if (crossesLink(projectDir, abs)) throw new Error(`Refusing to write through a symbolic link: ${LOCK_REL}`);
  const createdDir = !exists(dir);
  fs.mkdirSync(dir, { recursive: true });
  const token = `${process.pid}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
  const deadline = Date.now() + waitMs;
  let waited = false;
  for (;;) {
    try {
      const fd = fs.openSync(abs, "wx");
      try {
        fs.writeSync(fd, `${JSON.stringify({ pid: process.pid, host: os.hostname(), command, startedAt: new Date().toISOString(), token })}\n`);
      } finally {
        fs.closeSync(fd);
      }
      break;
    } catch (err) {
      // EPERM/EACCES/EBUSY: Windows, the previous lock is being deleted. Retry like EEXIST.
      if (!["EEXIST", "EPERM", "EACCES", "EBUSY"].includes(err.code)) {
        if (createdDir) pruneDir(dir);
        throw err;
      }
    }
    const current = readLock(abs);
    if (current && isStaleLock(current)) {
      removeStale(abs, current);
      continue;
    }
    if (Date.now() >= deadline) {
      if (createdDir) pruneDir(dir);
      throw new LockBusyError(current?.info);
    }
    if (!waited && current && onWait) onWait(current.info ?? {});
    waited = true;
    await sleep(current ? POLL_MS : 10);
  }
  const timer = setInterval(() => {
    try {
      const now = new Date();
      fs.utimesSync(abs, now, now);
    } catch {
      // best effort
    }
  }, HEARTBEAT_MS);
  timer.unref();
  held.set(abs, { timer, dir, createdDir, token });
  return { path: abs, release: () => releaseLock(abs) };
};

const pruneDir = (dir) => {
  try {
    fs.rmdirSync(dir); // only when empty
  } catch {
    // not empty or already gone
  }
};

export const releaseLock = (abs) => {
  const h = held.get(abs);
  if (!h) return;
  held.delete(abs);
  clearInterval(h.timer);
  const current = readLock(abs);
  if (current?.info?.token === h.token) {
    try {
      fs.unlinkSync(abs);
    } catch {
      // already gone
    }
  }
  // .redevkit/ left empty (a refused first init, an uninstall without backups): remove it.
  pruneDir(h.dir);
};

export const releaseAllLocks = () => {
  for (const abs of [...held.keys()]) releaseLock(abs);
};

process.on("exit", releaseAllLocks);

/**
 * Run `fn` holding the write lock (B14). The manifest must be read inside `fn`, after the lock.
 * A busy lock becomes an error with exitCode 1 and a localized message; nothing was changed.
 */
export const withWriteLock = async (projectDir, command, fn, { log = console.log } = {}) => {
  let handle;
  try {
    handle = await acquireLock(projectDir, { command, onWait: (info) => log(t("lockWaiting", { pid: info.pid ?? "?", command: info.command || "?" })) });
  } catch (err) {
    if (!(err instanceof LockBusyError)) throw err;
    // Messages in the installation language, as the command would have used.
    try {
      const m = JSON.parse(readText(path.join(projectDir, ".redevkit", "manifest.json")));
      if (m && typeof m.lang === "string") setLang(m.lang);
    } catch {
      // keep the current language
    }
    const e = new Error(t("lockBusy", { pid: err.info.pid ?? "?", command: err.info.command || "?", since: err.info.startedAt ?? "?", file: LOCK_REL }));
    e.exitCode = 1;
    throw e;
  }
  try {
    return await fn();
  } finally {
    handle.release();
  }
};
