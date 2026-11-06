// Three-way managed-file plan, backup and rollback.
// Ported from AG Kit cli/lib/managed-tree.js (MIT, VUDOVN): same decision table, but the
// managed set is an explicit list of project-relative files instead of a whole directory,
// so user files living next to managed ones are never touched.
import fs from "node:fs";
import path from "node:path";
import {
  atomicWrite,
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

export const BACKUP_ROOT = ".redevkit/backups";
export const CONFLICT_ROOT = ".redevkit/conflicts";
export const BACKUP_META = "_backup.json";

export const createRunId = (date = new Date()) => {
  const pad = (v, n = 2) => String(v).padStart(n, "0");
  return `${date.getUTCFullYear()}${pad(date.getUTCMonth() + 1)}${pad(date.getUTCDate())}-${pad(date.getUTCHours())}${pad(
    date.getUTCMinutes(),
  )}${pad(date.getUTCSeconds())}-${pad(date.getUTCMilliseconds(), 3)}`;
};

const act = (type, file, reason) => ({ type, file, reason });

/**
 * Build the update plan.
 * @param projectDir project root
 * @param incoming Map<rel, string|Buffer> rendered files
 * @param previous { rel: sha256 } from the manifest (empty object on a fresh install)
 * @param hasManifest whether a previous installation exists
 * @param force overwrite conflicting files (after backup)
 */
export const createPlan = ({ projectDir, incoming, previous = {}, hasManifest = false, force = false }) => {
  const incomingHashes = {};
  for (const [rel, content] of incoming) incomingHashes[rel] = sha256(typeof content === "string" ? Buffer.from(content, "utf8") : content);
  const all = [...new Set([...Object.keys(previous), ...Object.keys(incomingHashes)])].sort();
  const actions = [];
  const conflicts = [];
  const preserved = [];
  const unchanged = [];

  for (const file of all) {
    if (!isSafeRelative(file)) throw new Error(`Unsafe managed path: ${file}`);
    const abs = resolveInside(projectDir, file);
    const cur = hashFileIfExists(abs);
    const inc = incomingHashes[file];
    const old = previous[file];
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
      else if (inc === old) preserved.push({ file, reason: "managed file deleted locally" });
      else conflict("file deleted locally and changed upstream");
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
    if (p.reason === "managed file deleted locally" && previous[p.file]) files[p.file] = previous[p.file];
  }
  return files;
};

/**
 * Copy the given project-relative files (those that exist) into .redevkit/backups/<runId>/.
 * Returns the backup directory or null when there was nothing to save.
 */
export const createBackup = ({ projectDir, files, runId = createRunId(), reason = "update", version = "unknown", manifestFiles = null }) => {
  const existing = [...new Set(files)].filter((rel) => isSafeRelative(rel) && hashFileIfExists(resolveInside(projectDir, rel)) && hashFileIfExists(resolveInside(projectDir, rel)) !== "symlink");
  if (existing.length === 0) return null;
  const backupRel = `${BACKUP_ROOT}/${runId}`;
  for (const rel of existing) {
    writeInside(projectDir, `${backupRel}/${rel}`, fs.readFileSync(resolveInside(projectDir, rel)));
  }
  const meta = { schemaVersion: 1, createdAt: new Date().toISOString(), reason, version, files: existing.sort(), managedFiles: manifestFiles };
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
    out.push({ id: e.name, path: path.join(root, e.name), createdAt: meta.createdAt ?? "", reason: meta.reason ?? "", meta });
  }
  return out.sort((a, b) => b.createdAt.localeCompare(a.createdAt) || b.id.localeCompare(a.id));
};

/**
 * Restore a backup: first save the current state (safety backup), then remove managed files
 * that did not exist in the backup, then copy the backup files back.
 */
export const restoreBackup = ({ projectDir, backupId = null, currentManaged = [], extraFiles = [], dryRun = false, runId = createRunId() }) => {
  const backups = listBackups(projectDir);
  const selected = backupId ? backups.find((b) => b.id === backupId) : backups.find((b) => !b.id.startsWith("pre-rollback-")) ?? backups[0];
  if (!selected) throw new Error(backupId ? `Backup not found: ${backupId}` : "No backups found");
  const backupFiles = selected.meta.files ?? listFiles(selected.path).filter((f) => f !== BACKUP_META);
  const backupSet = new Set(backupFiles);
  const toRemove = currentManaged.filter((f) => !backupSet.has(f) && exists(resolveInside(projectDir, f)));
  if (dryRun) return { selected, restore: backupFiles, remove: toRemove, safetyBackupDir: null };
  const safetyBackupDir = createBackup({
    projectDir,
    files: [...new Set([...currentManaged, ...backupFiles, ...extraFiles])],
    runId: `pre-rollback-${runId}`,
    reason: "pre-rollback",
  });
  for (const rel of toRemove) removeInside(projectDir, rel);
  for (const rel of backupFiles) {
    const src = path.join(selected.path, ...rel.split("/"));
    if (!exists(src)) continue;
    writeInside(projectDir, rel, fs.readFileSync(src));
  }
  return { selected, restore: backupFiles, remove: toRemove, safetyBackupDir };
};

export { atomicWrite };
