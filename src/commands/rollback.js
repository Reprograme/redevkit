// redevkit rollback [--backup <id>] [--dry-run]  (§10)
import path from "node:path";
import { exists, resolveInside } from "../core/fsutil.js";
import { t, getLang, setLang } from "../core/i18n.js";
import { CONFIG_FILES, CONTEXT_FILES } from "../core/install.js";
import { withWriteLock } from "../core/lock.js";
import { BackupError, listBackups, restoreBackup } from "../core/managed-tree.js";
import { loadManifest, readStateId } from "../core/manifest.js";
import { CliError } from "./init.js";

export const runRollback = async (opts, { log = console.log, projectDir = process.cwd() } = {}) => {
  if (opts.list || opts.dryRun) return rollback(opts, log, projectDir);
  return withWriteLock(projectDir, "rollback", () => rollback(opts, log, projectDir), { log });
};

const sample = (list) => list.slice(0, 3).join(", ") + (list.length > 3 ? ", ..." : "");

const rollback = async (opts, log, projectDir) => {
  const { manifest, error } = loadManifest(projectDir);
  if (manifest?.lang) setLang(manifest.lang); // messages in the manifest language, like the other commands
  // An invalid manifest must not block the recovery path (rollback restores the previous manifest),
  // but without it the files the reverted run added cannot be told apart: say so (A13).
  if (error && !opts.list) log(t("rollbackManifestInvalid", { v: error }));
  if (opts.list) {
    const backups = listBackups(projectDir);
    if (!backups.length) log(t("noBackups"));
    for (const b of backups) log(`${b.id}  ${b.createdAt}  ${b.reason}`);
    return { backups };
  }
  if (!opts.backup && !listBackups(projectDir).length) throw new CliError(t("noBackups"), 1);
  const currentManaged = manifest ? Object.keys(manifest.files) : [];
  const extraFiles = [...CONTEXT_FILES, ...Object.values(CONFIG_FILES), ".redevkit/manifest.json"];
  let r;
  try {
    // B02/B10: the backup (or the chain of backups down to it) is chosen from the current state and
    // every backup is checked before anything is written; --dry-run reports the same errors.
    r = restoreBackup({ projectDir, backupId: opts.backup ?? null, currentManaged, extraFiles, dryRun: Boolean(opts.dryRun), state: readStateId(projectDir) });
  } catch (err) {
    if (!(err instanceof BackupError)) throw err;
    let text = t(err.code, err.vars);
    if (err.code === "rollbackNothingToUndo" && err.vars.redo) text += ` ${t("rollbackRedoHint", { v: err.vars.redo })}`;
    throw new CliError(text, 1);
  }
  if (r.steps.length > 1) log(t("rollbackChain", { v: r.selected.id, chain: r.steps.map((s) => s.id).join(" -> ") }));
  if (opts.dryRun) {
    log(`${getLang() === "pt-BR" ? "Restauraria" : "Would restore"} ${r.selected.id}: ${r.restore.length} ${getLang() === "pt-BR" ? "arquivo(s)" : "file(s)"}`);
    for (const f of r.restore) log(`  restore ${f}`);
    for (const f of r.remove) log(`  remove  ${f}`);
    log(t("dryRun"));
    return r;
  }
  const safety = r.safetyBackupDir ? path.relative(projectDir, r.safetyBackupDir) : "-";
  log(t("rollbackDone", { v: r.selected.id, safety }));

  // B02: every file of the restored manifest must exist, except the ones that were already missing
  // (deleted locally) before the operation that was undone.
  const restored = loadManifest(projectDir).manifest;
  if (restored) {
    const missing = Object.keys(restored.files).filter((f) => !exists(resolveInside(projectDir, f)));
    if (missing.length) {
      if (!r.expectedMissing) log(t("rollbackMissingUnverified", { n: missing.length, ex: sample(missing) }));
      else {
        const expected = new Set(r.expectedMissing);
        const unexpected = missing.filter((f) => !expected.has(f));
        if (unexpected.length) {
          throw new CliError(t("rollbackMissing", { n: unexpected.length, ex: sample(unexpected), safety: r.safetyBackupDir ? path.basename(r.safetyBackupDir) : "-" }), 1);
        }
        log(t("missingManaged", { n: missing.length }));
      }
    }
  }
  return r;
};
