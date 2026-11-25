// Three-way managed-file plan, backup and rollback.
// Ported from AG Kit cli/lib/managed-tree.js (MIT, VUDOVN): same decision table, but the
// managed set is an explicit list of project-relative files instead of a whole directory,
// so user files living next to managed ones are never touched.
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import {
  assertRemovable,
  assertWritable,
  atomicWrite,
  contentHash,
  crossesLink,
  exists,
  hashFileIfExists,
  isSafeRelative,
  listFiles,
  readText,
  removeInside,
  resolveInside,
  sha256,
  writeInside,
} from "./fsutil.js";
import { MANIFEST_REL } from "./manifest.js";

export const BACKUP_ROOT = ".redevkit/backups";
export const CONFLICT_ROOT = ".redevkit/conflicts";
export const BACKUP_META = "_backup.json";
export const PRE_ROLLBACK = "pre-rollback-";

let lastStamp = "";
let stampSeq = 0;

/**
 * Run (and backup) id: the UTC time to the millisecond, then a per-process sequence and a random
 * suffix (N02). Two calls in the same millisecond, in one process or in two, never get the same id,
 * and ids still sort in chronological order (the time comes first; the sequence orders the calls of
 * one process within a millisecond).
 */
export const createRunId = (date = new Date()) => {
  const pad = (v, n = 2) => String(v).padStart(n, "0");
  const stamp = `${date.getUTCFullYear()}${pad(date.getUTCMonth() + 1)}${pad(date.getUTCDate())}-${pad(date.getUTCHours())}${pad(
    date.getUTCMinutes(),
  )}${pad(date.getUTCSeconds())}-${pad(date.getUTCMilliseconds(), 3)}`;
  if (stamp === lastStamp) stampSeq += 1;
  else {
    lastStamp = stamp;
    stampSeq = 0;
  }
  return `${stamp}-${stampSeq.toString(36).padStart(3, "0")}${crypto.randomBytes(3).toString("hex")}`;
};

/** A backup that cannot be restored as it is: `code` is an i18n key, `vars` its values. */
export class BackupError extends Error {
  constructor(code, vars, message) {
    super(message);
    this.code = code;
    this.vars = vars;
  }
}

const act = (type, file, reason) => ({ type, file, reason });

/** Plan reasons other modules look for. */
export const DELETED_LOCALLY = "managed file deleted locally";
export const DELETED_AND_CHANGED = "file deleted locally and changed upstream";
export const RESTORED = "restored: managed file deleted locally";

/** Managed files that stay missing after the plan is applied (deleted locally, deletion honoured). */
export const missingAfterPlan = (plan) =>
  [...plan.preserved.filter((p) => p.reason === DELETED_LOCALLY), ...plan.conflicts.filter((c) => c.reason === DELETED_AND_CHANGED)].map((x) => x.file).sort();

/**
 * Build the update plan.
 * @param projectDir project root
 * @param incoming Map<rel, string|Buffer> rendered files
 * @param previous { rel: sha256 } from the manifest (empty object on a fresh install)
 * @param hasManifest whether a previous installation exists
 * @param force overwrite conflicting files (after backup)
 * @param restore re-add managed files that are missing locally (never overwrites a local change)
 *
 * Hashes are content hashes (fsutil contentHash): a text file hashes the same with LF or CRLF.
 */
export const createPlan = ({ projectDir, incoming, previous = {}, hasManifest = false, force = false, restore = false }) => {
  const incomingHashes = {};
  for (const [rel, content] of incoming) incomingHashes[rel] = contentHash(content);
  const rawIncoming = (rel) => sha256(typeof incoming.get(rel) === "string" ? Buffer.from(incoming.get(rel), "utf8") : incoming.get(rel));
  const all = [...new Set([...Object.keys(previous), ...Object.keys(incomingHashes)])].sort();
  const actions = [];
  const conflicts = [];
  const preserved = [];
  const unchanged = [];

  for (const file of all) {
    if (!isSafeRelative(file)) throw new Error(`Unsafe managed path: ${file}`);
    const abs = resolveInside(projectDir, file);
    const inc = incomingHashes[file];
    let old = previous[file];
    let cur = hashFileIfExists(abs, old);
    // Baseline written by CLI <= 1.0.3 (raw bytes) for the very content being installed now, which
    // has CRLF in it: nothing changed upstream, so compare everything by content hash.
    if (old !== undefined && inc !== undefined && old !== inc && old === rawIncoming(file)) {
      if (cur === old) cur = inc;
      old = inc;
    }
    const conflict = (reason) => {
      if (force && inc !== undefined && cur !== "symlink") actions.push(act("update", file, `forced: ${reason}`));
      else conflicts.push({ file, reason, currentHash: cur ?? null, incomingHash: inc ?? null, oldHash: old ?? null });
    };

    if (cur === "symlink" || cur === "not-a-file") {
      conflicts.push({ file, reason: "path is a symbolic link or not a regular file; never written through", currentHash: null, incomingHash: inc ?? null, oldHash: old ?? null });
      continue;
    }

    if (old === undefined) {
      // Not managed before (fresh install, or a new file in this version).
      if (cur === undefined && inc !== undefined) actions.push(act("add", file, hasManifest ? "new managed file" : "fresh install"));
      else if (cur !== undefined && inc === undefined) preserved.push({ file, reason: "user-owned file" });
      else if (cur === inc) unchanged.push(file);
      else conflict("existing user file differs from the managed version");
      continue;
    }
    if (cur === undefined) {
      if (inc === undefined) unchanged.push(file);
      else if (restore) actions.push(act("add", file, RESTORED)); // nothing local to overwrite
      else if (inc === old) preserved.push({ file, reason: DELETED_LOCALLY });
      else conflict(DELETED_AND_CHANGED);
      continue;
    }
    if (inc === undefined) {
      if (cur === old) actions.push(act("delete", file, "removed upstream and unchanged locally"));
      else conflict("file changed locally but removed upstream");
      continue;
    }
    if (cur === inc) unchanged.push(file);
    else if (cur === old) actions.push(act("update", file, "changed upstream and unchanged locally"));
    else if (inc === old) preserved.push({ file, reason: "changed locally only" });
    else conflict("changed both locally and upstream");
  }
  return { actions, conflicts, preserved, unchanged, incomingHashes };
};

/** Next files map for the manifest after applying a plan. */
export const nextManifestFiles = (plan, previous = {}) => {
  const files = {};
  const conflictFiles = new Set(plan.conflicts.map((c) => c.file));
  for (const [file, hash] of Object.entries(plan.incomingHashes)) {
    if (conflictFiles.has(file)) {
      if (previous[file]) files[file] = previous[file]; // keep baseline: still a conflict next time
      continue;
    }
    files[file] = hash;
  }
  for (const p of plan.preserved) {
    if (p.reason === DELETED_LOCALLY && previous[p.file]) files[p.file] = previous[p.file];
  }
  return files;
};

/**
 * Copy the given project-relative files (those that exist) into .redevkit/backups/<runId>/.
 * `manifestFiles` is the managed set before the run: a rollback removes only managed files the run
 * added, never the ones it left untouched (which are not in the backup).
 * With `recordAbsent`, the listed files that do not exist yet are recorded as `absent`: the run is
 * about to create them, so a rollback removes them again.
 * `adopted` lists files that already existed with the managed content and become managed in this run:
 * the run did not create them, so a rollback never removes them.
 * `link` ties the backup to the state history (B02): `previousRunId` is the manifest's lastRunId the
 * backup returns to (null: no manifest), `resultRunId` the lastRunId the operation leaves (null: no
 * manifest). A backup is restored directly only while the current state is its `resultRunId`.
 * `missingBefore` lists the managed files already missing before the operation (deleted locally): a
 * rollback to this backup does not bring them back, every other managed file must exist afterwards.
 * The backup directory is created exclusively: an id already in use is an error, never a merge (N02).
 * Returns the backup directory or null when there was nothing to save.
 */
export const createBackup = ({
  projectDir,
  files,
  runId = createRunId(),
  reason = "update",
  version = "unknown",
  manifestFiles = null,
  recordAbsent = false,
  adopted = null,
  link = null,
  missingBefore = null,
}) => {
  const safe = [...new Set(files)].filter((rel) => isSafeRelative(rel));
  const state = new Map(safe.map((rel) => [rel, hashFileIfExists(resolveInside(projectDir, rel))]));
  const existing = safe.filter((rel) => state.get(rel) && state.get(rel) !== "symlink" && state.get(rel) !== "not-a-file");
  if (existing.length === 0) return null;
  const backupRel = `${BACKUP_ROOT}/${runId}`;
  const backupAbs = resolveInside(projectDir, backupRel);
  if (crossesLink(projectDir, backupAbs)) throw new Error(`Refusing to write through a symbolic link: ${backupRel}`);
  fs.mkdirSync(path.dirname(backupAbs), { recursive: true });
  try {
    fs.mkdirSync(backupAbs);
  } catch (err) {
    if (err.code === "EEXIST") throw new Error(`Backup id already in use: ${runId}`);
    throw err;
  }
  for (const rel of existing) {
    writeInside(projectDir, `${backupRel}/${rel}`, fs.readFileSync(resolveInside(projectDir, rel)));
  }
  const meta = { schemaVersion: 1, createdAt: new Date().toISOString(), reason, version, files: existing.sort(), managedFiles: manifestFiles };
  if (recordAbsent) meta.absent = safe.filter((rel) => state.get(rel) === undefined).sort();
  if (Array.isArray(adopted) && adopted.length) meta.adopted = [...new Set(adopted)].filter((rel) => isSafeRelative(rel)).sort();
  if (link) {
    meta.runId = link.runId ?? runId;
    if (link.previousRunId !== undefined) meta.previousRunId = link.previousRunId;
    if (link.resultRunId !== undefined) meta.resultRunId = link.resultRunId;
  }
  if (Array.isArray(missingBefore)) meta.missingBefore = [...new Set(missingBefore)].sort();
  writeInside(projectDir, `${backupRel}/${BACKUP_META}`, `${JSON.stringify(meta, null, 2)}\n`);
  return path.join(projectDir, ...backupRel.split("/"));
};

/** Apply file actions; conflicting incoming versions are saved under .redevkit/conflicts/<runId>/. */
export const applyPlan = ({ projectDir, plan, incoming, runId }) => {
  for (const a of plan.actions) {
    if (a.type === "delete") removeInside(projectDir, a.file);
    else writeInside(projectDir, a.file, incoming.get(a.file));
  }
  const written = [];
  for (const c of plan.conflicts) {
    if (c.incomingHash && incoming.has(c.file)) {
      const rel = `${CONFLICT_ROOT}/${runId}/${c.file}`;
      writeInside(projectDir, rel, incoming.get(c.file));
      written.push(rel);
    }
  }
  return { conflictCopies: written };
};

export const listBackups = (projectDir) => {
  const root = path.join(projectDir, ...BACKUP_ROOT.split("/"));
  if (!exists(root)) return [];
  const out = [];
  for (const e of fs.readdirSync(root, { withFileTypes: true })) {
    if (!e.isDirectory()) continue;
    const metaPath = path.join(root, e.name, BACKUP_META);
    let meta = null;
    try {
      meta = JSON.parse(readText(metaPath));
    } catch {
      continue; // not a REDEVKIT backup
    }
    if (!isPlainObject(meta)) continue;
    out.push({ id: e.name, path: path.join(root, e.name), createdAt: meta.createdAt ?? "", reason: meta.reason ?? "", meta });
  }
  return out.sort((a, b) => b.createdAt.localeCompare(a.createdAt) || b.id.localeCompare(a.id));
};

const isPreRollback = (b) => b.id.startsWith(PRE_ROLLBACK);
const isPlainObject = (v) => typeof v === "object" && v !== null && !Array.isArray(v);
const listOf = (v) => (Array.isArray(v) ? v : []);

/** The manifest saved in a backup: null when the backup has none, undefined when it cannot be read. */
const savedManifest = (b) => {
  const p = path.join(b.path, ...MANIFEST_REL.split("/"));
  if (!exists(p)) return null;
  try {
    const data = JSON.parse(readText(p));
    return isPlainObject(data) ? data : undefined;
  } catch {
    return undefined;
  }
};

/**
 * Where a backup sits in the state history (B02): `result` is the state (manifest lastRunId) the
 * operation left, `previous` the state the backup returns to; null = no manifest, undefined = unknown.
 * Backups written before these fields existed are read from what they hold: the id of an update/init
 * backup is its run id, an uninstall leaves no manifest, and the saved manifest has the previous id.
 */
export const backupLink = (b) => {
  if (b.link) return b.link;
  const m = b.meta;
  const has = (k) => Object.prototype.hasOwnProperty.call(m, k);
  let result;
  if (has("resultRunId")) result = m.resultRunId;
  else if (!isPreRollback(b)) result = m.reason === "uninstall" ? null : b.id;
  let previous;
  if (has("previousRunId")) previous = m.previousRunId;
  else {
    const saved = savedManifest(b);
    previous = saved === null ? null : typeof saved?.lastRunId === "string" ? saved.lastRunId : undefined;
  }
  b.link = { result, previous };
  return b.link;
};

/**
 * B10: a backup is restorable only when its metadata is coherent and every file it lists is in it.
 * Returns the list of files to restore; throws BackupError otherwise (nothing has been touched yet).
 */
export const checkBackup = (b) => {
  const m = b.meta;
  const fail = (code, vars) => {
    throw new BackupError(code, { id: b.id, ...vars }, code === "backupIncomplete" ? `Backup ${b.id} is incomplete: ${vars.file} is missing` : `Backup ${b.id} is incoherent: ${vars.detail}`);
  };
  const safeList = (v) => Array.isArray(v) && v.every((rel) => isSafeRelative(rel));
  for (const k of ["files", "absent", "adopted", "missingBefore"]) {
    if (m[k] !== undefined && !safeList(m[k])) fail("backupIncoherent", { detail: `"${k}" in ${BACKUP_META} is not a list of project paths` });
  }
  if (m.managedFiles !== undefined && m.managedFiles !== null && !safeList(m.managedFiles)) {
    fail("backupIncoherent", { detail: `"managedFiles" in ${BACKUP_META} is not a list of project paths` });
  }
  const files = m.files ?? listFiles(b.path).filter((f) => f !== BACKUP_META);
  const absent = new Set(listOf(m.absent));
  for (const rel of files) {
    if (absent.has(rel)) fail("backupIncoherent", { detail: `${rel} is listed both as saved and as absent` });
    let st = null;
    try {
      st = fs.lstatSync(path.join(b.path, ...rel.split("/")));
    } catch {
      // missing: reported below
    }
    if (!st?.isFile()) fail("backupIncomplete", { file: rel });
  }
  if (files.includes(MANIFEST_REL)) {
    const saved = savedManifest(b);
    if (saved === undefined || !isPlainObject(saved.files)) fail("backupIncoherent", { detail: `the saved ${MANIFEST_REL} is not a readable manifest` });
    if (Array.isArray(m.managedFiles)) {
      const savedFiles = Object.keys(saved.files);
      const listed = new Set(m.managedFiles);
      if (savedFiles.length !== listed.size || !savedFiles.every((f) => listed.has(f))) {
        fail("backupIncoherent", { detail: `"managedFiles" in ${BACKUP_META} does not match the saved ${MANIFEST_REL}` });
      }
    }
    if (typeof m.previousRunId === "string" && saved.lastRunId !== m.previousRunId) {
      fail("backupIncoherent", { detail: `the saved ${MANIFEST_REL} (lastRunId ${saved.lastRunId}) is not the state ${BACKUP_META} records (${m.previousRunId})` });
    }
  }
  return files;
};

/**
 * Decide which backups a rollback restores, newest first (B02).
 * `state` is the current state ({ known, runId }, see manifest.readStateId); without it (library use)
 * the chosen backup is restored as it is.
 * - A backup is restored directly only when it undid the last operation: its `result` is the current
 *   state. With no --backup, that backup is the one restored ("undo the last operation").
 * - An older backup is reached through the chain: the backup of the last operation, then the backup of
 *   the operation before it, and so on, each one returning to the state the next one left. A missing
 *   link (an operation run with --no-backup) stops the rollback before anything is written.
 * - With an unreadable manifest the chain cannot be checked: only the most recent backup is allowed.
 */
export const planRollback = ({ projectDir, backupId = null, state = undefined, backups = listBackups(projectDir) }) => {
  let target = null;
  if (backupId) {
    target = backups.find((b) => b.id === backupId);
    if (!target) {
      // Like a short git SHA: an unambiguous prefix names a backup (ids carry a unique suffix).
      const matches = backups.filter((b) => b.id.startsWith(backupId));
      if (matches.length > 1) {
        throw new BackupError("backupAmbiguous", { id: backupId, list: matches.map((b) => b.id).join(", ") }, `Backup id ${backupId} is ambiguous`);
      }
      target = matches[0] ?? null;
    }
    if (!target) {
      const dir = isSafeRelative(backupId) && !backupId.includes("/") ? path.join(projectDir, ...BACKUP_ROOT.split("/"), backupId) : null;
      if (dir && exists(dir)) throw new BackupError("backupIncoherent", { id: backupId, detail: `${BACKUP_META} is missing or unreadable` }, `Backup ${backupId} is incoherent`);
      throw new Error(`Backup not found: ${backupId}`);
    }
  }
  if (!backups.length) throw new Error("No backups found");
  const newestUpdate = backups.find((b) => !isPreRollback(b)) ?? backups[0];
  if (state === undefined) return { selected: target ?? newestUpdate, chain: [target ?? newestUpdate] };
  if (!state.known) {
    const selected = target ?? newestUpdate;
    if (selected !== newestUpdate && selected !== backups[0]) {
      throw new BackupError("rollbackUnknownState", { v: newestUpdate.id, id: selected.id }, `The current manifest is unreadable: only ${newestUpdate.id} can be restored`);
    }
    return { selected, chain: [selected] };
  }
  const start = state.runId;
  const leaves = (b, id) => backupLink(b).result !== undefined && backupLink(b).result === id;
  if (!target) {
    const direct = backups.find((b) => !isPreRollback(b) && leaves(b, start));
    if (!direct) {
      const redo = backups.find((b) => isPreRollback(b) && leaves(b, start));
      throw new BackupError("rollbackNothingToUndo", { state: start ?? "-", redo: redo?.id ?? null }, `No backup undoes the last operation (${start ?? "-"})`);
    }
    return { selected: direct, chain: [direct] };
  }
  // A pre-rollback backup written before the state fields existed: only as the newest backup.
  if (backupLink(target).result === undefined && target === backups[0]) return { selected: target, chain: [target] };
  const chain = [];
  const used = new Set();
  let cur = start;
  for (;;) {
    if (leaves(target, cur)) {
      chain.push(target);
      break;
    }
    const candidates = backups.filter((b) => b !== target && !used.has(b.id) && leaves(b, cur));
    // Prefer undoing an operation over redoing a reverted one (pre-rollback backups).
    const next = candidates.find((b) => !isPreRollback(b)) ?? candidates[0];
    const broken = (at) => new BackupError("rollbackChainBroken", { target: target.id, state: start ?? "-", at }, `Backup ${target.id} cannot be reached from the current state`);
    if (!next) throw broken(cur ?? "-");
    if (backupLink(next).previous === undefined) throw broken(next.id);
    chain.push(next);
    used.add(next.id);
    cur = backupLink(next).previous;
  }
  return { selected: target, chain };
};

/**
 * Restore a backup (or a chain of backups, newest first, see planRollback): every backup is checked
 * (B10) and every step is planned before anything is written; then the current state is saved
 * (safety backup) and each step removes the files its run created (managed files that were neither
 * in the backup, nor managed before the run, nor adopted by it, and files recorded as absent) and
 * copies the backup files back.
 */
export const restoreBackup = ({ projectDir, backupId = null, currentManaged = [], extraFiles = [], dryRun = false, runId = createRunId(), state = undefined }) => {
  const { selected, chain } = planRollback({ projectDir, backupId, state });
  const filesOf = new Map(chain.map((b) => [b.id, checkBackup(b)]));

  // Simulate the steps: which files exist after each one, and which manifest is in place.
  const overlay = new Map();
  const present = (rel) => (overlay.has(rel) ? overlay.get(rel) : exists(resolveInside(projectDir, rel)));
  const touched = new Set([...currentManaged, ...extraFiles]);
  const steps = [];
  let managed = currentManaged;
  for (const b of chain) {
    const backupFiles = filesOf.get(b.id);
    const backupSet = new Set(backupFiles);
    // Managed before the run but not in the backup = left untouched by the run: keep it.
    const managedBefore = new Set(listOf(b.meta.managedFiles));
    const absent = listOf(b.meta.absent);
    // Pre-existing files the run adopted unchanged (A12): not created by the run, never removed.
    const adopted = new Set(listOf(b.meta.adopted));
    const remove = [...new Set([...managed.filter((f) => !managedBefore.has(f) && !adopted.has(f)), ...absent])].filter(
      (f) => !backupSet.has(f) && isSafeRelative(f) && present(f),
    );
    steps.push({ id: b.id, restore: backupFiles, remove });
    for (const f of [...managed, ...backupFiles, ...absent]) touched.add(f);
    for (const f of remove) overlay.set(f, false);
    for (const f of backupFiles) overlay.set(f, true);
    if (backupSet.has(MANIFEST_REL)) managed = Object.keys(savedManifest(b).files).filter((f) => isSafeRelative(f));
    else if (!present(MANIFEST_REL)) managed = [];
  }
  for (const s of steps) {
    for (const f of s.remove) assertRemovable(projectDir, f);
    for (const f of s.restore) assertWritable(projectDir, f);
  }
  const restore = [...new Set(steps.flatMap((s) => s.restore))];
  const remove = [...new Set(steps.flatMap((s) => s.remove))].filter((f) => overlay.get(f) === false);
  // Missing after the restore is expected for files deleted locally before the undone operation, or
  // already missing now (the restore does not create or remove them); anything else is a defect.
  const missingNow = currentManaged.filter((f) => isSafeRelative(f) && !exists(resolveInside(projectDir, f)));
  const expectedMissing = Array.isArray(selected.meta.missingBefore) ? [...new Set([...selected.meta.missingBefore, ...missingNow])] : null;
  if (dryRun) return { selected, steps, restore, remove, safetyBackupDir: null, expectedMissing };

  const safetyId = `${PRE_ROLLBACK}${runId}`;
  const safetyBackupDir = createBackup({
    projectDir,
    files: [...touched],
    runId: safetyId,
    reason: "pre-rollback",
    recordAbsent: true,
    link: { runId: safetyId, previousRunId: state?.known ? state.runId : undefined, resultRunId: backupLink(selected).previous },
    missingBefore: missingNow,
  });
  for (const s of steps) {
    const b = chain.find((x) => x.id === s.id);
    for (const rel of s.remove) removeInside(projectDir, rel);
    for (const rel of s.restore) writeInside(projectDir, rel, fs.readFileSync(path.join(b.path, ...rel.split("/"))));
  }
  return { selected, steps, restore, remove, safetyBackupDir, expectedMissing };
};

export { atomicWrite };
