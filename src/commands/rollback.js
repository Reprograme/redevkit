// redevkit rollback [--backup <id>] [--dry-run]  (§10)
import path from "node:path";
import { t, getLang } from "../core/i18n.js";
import { CONFIG_FILES, CONTEXT_FILES } from "../core/install.js";
import { listBackups, restoreBackup } from "../core/managed-tree.js";
import { loadManifest } from "../core/manifest.js";
import { CliError } from "./init.js";

export const runRollback = async (opts, { log = console.log, projectDir = process.cwd() } = {}) => {
  const { manifest } = loadManifest(projectDir);
  if (opts.list) {
    const backups = listBackups(projectDir);
    if (!backups.length) log(t("noBackups"));
    for (const b of backups) log(`${b.id}  ${b.createdAt}  ${b.reason}`);
    return { backups };
  }
  if (!listBackups(projectDir).length) throw new CliError(t("noBackups"), 1);
  const currentManaged = manifest ? Object.keys(manifest.files) : [];
  const extraFiles = [...CONTEXT_FILES, ...Object.values(CONFIG_FILES), ".redevkit/manifest.json"];
  const r = restoreBackup({ projectDir, backupId: opts.backup ?? null, currentManaged, extraFiles, dryRun: Boolean(opts.dryRun) });
  if (opts.dryRun) {
    log(`${getLang() === "pt-BR" ? "Restauraria" : "Would restore"} ${r.selected.id}: ${r.restore.length} ${getLang() === "pt-BR" ? "arquivo(s)" : "file(s)"}`);
    for (const f of r.restore) log(`  restore ${f}`);
    for (const f of r.remove) log(`  remove  ${f}`);
    log(t("dryRun"));
    return r;
  }
  log(t("rollbackDone", { v: r.selected.id, safety: r.safetyBackupDir ? path.relative(projectDir, r.safetyBackupDir) : "-" }));
  return r;
};
