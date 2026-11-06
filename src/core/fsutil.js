// File-system helpers: atomic writes, symlink-safe removal, hashing, path normalization.
import crypto from "node:crypto";
import fs from "node:fs";
import fsp from "node:fs/promises";
import path from "node:path";

/** Temp files created by atomic writes that are still in flight (cleaned on SIGINT, C2). */
const pendingTemps = new Set();

export const toPosix = (value) => value.split(path.sep).join("/").replace(/\\/g, "/");

export const sha256 = (data) => crypto.createHash("sha256").update(data).digest("hex");

/** Files that must never break or be counted by any command (Y12). */
export const JUNK_FILES = new Set(["desktop.ini", "thumbs.db", ".ds_store"]);
export const isJunk = (name) => JUNK_FILES.has(name.toLowerCase());

/** A relative POSIX path that stays inside its root. */
export const isSafeRelative = (rel) => {
  if (typeof rel !== "string" || !rel || rel.includes("\0")) return false;
  const norm = toPosix(rel);
  if (path.posix.isAbsolute(norm) || path.win32.isAbsolute(rel) || /^[a-zA-Z]:/.test(norm)) return false;
  return !norm.split("/").some((seg) => seg === ".." || seg === "" || seg === ".");
};

export const resolveInside = (root, rel) => {
  if (!isSafeRelative(rel)) throw new Error(`Unsafe relative path: ${rel}`);
  const abs = path.resolve(root, ...toPosix(rel).split("/"));
  const rootAbs = path.resolve(root);
  if (abs !== rootAbs && !abs.startsWith(rootAbs + path.sep)) throw new Error(`Path escapes root: ${rel}`);
  return abs;
};

export const exists = (p) => {
  try {
    fs.lstatSync(p);
    return true;
  } catch {
    return false;
  }
};

export const readText = (p) => {
  const raw = fs.readFileSync(p, "utf8");
  return raw.charCodeAt(0) === 0xfeff ? raw.slice(1) : raw;
};

export const readIfExists = (p) => (exists(p) ? fs.readFileSync(p) : null);

/**
 * True when `abs` or any directory between `root` and `abs` is a symbolic link or junction.
 * Used before writing or deleting so we never follow a link out of the project (Y3, Y9).
 */
export const crossesLink = (root, abs) => {
  const rootAbs = path.resolve(root);
  const rel = path.relative(rootAbs, path.resolve(abs));
  if (rel.startsWith("..") || path.isAbsolute(rel)) return true;
  let current = rootAbs;
  for (const seg of rel.split(path.sep).filter(Boolean)) {
    current = path.join(current, seg);
    let st;
    try {
      st = fs.lstatSync(current);
    } catch {
      return false; // does not exist yet: nothing below can be a link
    }
    if (st.isSymbolicLink()) return true;
  }
  return false;
};

/** Write a file atomically: temp file in the same directory + rename (Y18, C2). */
export const atomicWrite = (abs, data) => {
  const dir = path.dirname(abs);
  fs.mkdirSync(dir, { recursive: true });
  const tmp = path.join(dir, `.${path.basename(abs)}.redevkit-${process.pid}-${crypto.randomBytes(4).toString("hex")}.tmp`);
  pendingTemps.add(tmp);
  try {
    fs.writeFileSync(tmp, data);
    try {
      fs.renameSync(tmp, abs);
    } catch (err) {
      // Windows can refuse rename over a file held open by another process; fall back to copy.
      if (err.code === "EPERM" || err.code === "EACCES" || err.code === "EBUSY") {
        fs.copyFileSync(tmp, abs);
        fs.rmSync(tmp, { force: true });
      } else {
        throw err;
      }
    }
  } finally {
    pendingTemps.delete(tmp);
    if (fs.existsSync(tmp)) fs.rmSync(tmp, { force: true });
  }
};

/** Write a project-relative file, refusing to write through links. */
export const writeInside = (root, rel, data) => {
  const abs = resolveInside(root, rel);
  if (crossesLink(root, abs)) throw new Error(`Refusing to write through a symbolic link: ${rel}`);
  atomicWrite(abs, data);
};

/** Delete one project-relative file, never following links; prune empty parents up to root. */
export const removeInside = (root, rel, { pruneParents = true } = {}) => {
  const abs = resolveInside(root, rel);
  const parent = path.dirname(abs);
  if (crossesLink(root, parent)) throw new Error(`Refusing to delete through a symbolic link: ${rel}`);
  let st;
  try {
    st = fs.lstatSync(abs);
  } catch {
    return false;
  }
  if (st.isDirectory()) throw new Error(`Refusing to delete a directory as a file: ${rel}`);
  fs.unlinkSync(abs); // for a link this removes the link itself, never its target
  if (pruneParents) pruneEmptyParents(root, parent);
  return true;
};

export const pruneEmptyParents = (root, startDir) => {
  const rootAbs = path.resolve(root);
  let current = path.resolve(startDir);
  while (current.startsWith(rootAbs + path.sep)) {
    let entries;
    try {
      entries = fs.readdirSync(current);
    } catch {
      break;
    }
    const meaningful = entries.filter((e) => !isJunk(e));
    if (meaningful.length > 0) break;
    for (const junk of entries) fs.rmSync(path.join(current, junk), { force: true });
    try {
      fs.rmdirSync(current);
    } catch {
      break;
    }
    current = path.dirname(current);
  }
};

/** Recursive file listing (POSIX relative paths), skipping junk files and never following links. */
export const listFiles = (root, { skipDirs = new Set(["node_modules", ".git", "__pycache__"]) } = {}) => {
  const out = [];
  if (!exists(root)) return out;
  const visit = (dir) => {
    const entries = fs.readdirSync(dir, { withFileTypes: true }).sort((a, b) => (a.name < b.name ? -1 : a.name > b.name ? 1 : 0));
    for (const e of entries) {
      if (isJunk(e.name)) continue;
      const abs = path.join(dir, e.name);
      if (e.isDirectory()) {
        if (!skipDirs.has(e.name)) visit(abs);
      } else if (e.isFile()) {
        out.push(toPosix(path.relative(root, abs)));
      }
    }
  };
  visit(root);
  return out;
};

export const hashFileIfExists = (abs) => {
  try {
    const st = fs.lstatSync(abs);
    if (st.isSymbolicLink()) return "symlink";
    if (!st.isFile()) return "not-a-file";
    return sha256(fs.readFileSync(abs));
  } catch {
    return undefined;
  }
};

export const cleanupPendingTemps = () => {
  for (const tmp of pendingTemps) {
    try {
      fs.rmSync(tmp, { force: true });
    } catch {
      // best effort
    }
  }
  pendingTemps.clear();
};

export const pendingTempCount = () => pendingTemps.size;

export const copyFileInside = (root, srcAbs, rel) => {
  writeInside(root, rel, fs.readFileSync(srcAbs));
};

export const mkdirp = (p) => fsp.mkdir(p, { recursive: true });
