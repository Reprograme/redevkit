// redevkit update  (§10): three-way merge of managed files; never touches memory, specs or DESIGN.md.
import path from "node:path";
import { applySync, computeSync } from "../core/install.js";
import { setLang, t } from "../core/i18n.js";
import { writeInside } from "../core/fsutil.js";
import { createRunId } from "../core/managed-tree.js";
import { loadManifest } from "../core/manifest.js";
import { packageVersion } from "../core/render.js";
import { CliError } from "./init.js";
import { printConfigPreview, printMessages, printMissing, printOutcome, printPlan, writeConflictReport } from "./sync-report.js";

export const requireManifest = (projectDir) => {
  const { manifest, error } = loadManifest(projectDir);
  if (error) throw new CliError(t("manifestError", { v: error }), 1);
  if (!manifest) throw new CliError(t("notInstalled"), 1);
  setLang(manifest.lang);
  return manifest;
};

/** Shared by update and target add/remove. */
export const runSync = (projectDir, manifest, targets, opts, log) => {
  const sync = computeSync({ projectDir, targets, lang: manifest.lang, restore: Boolean(opts.restore), previousManifest: manifest });
  printPlan(sync, { verbose: Boolean(opts.verbose), out: log });
  printConfigPreview(sync, { out: log });
  const runId = createRunId();
  if (opts.conflictReport) {
    const rep = writeConflictReport(projectDir, opts.conflictReport, sync, runId);
    if (!opts.dryRun) {
      const rel = path.relative(projectDir, rep.path).split(path.sep).join("/");
      if (rel.startsWith("..")) throw new CliError("--conflict-report must be inside the project", 2);
      writeInside(projectDir, rel, rep.text);
    }
    log(`conflict report: ${rep.path}`);
  }
  if (opts.dryRun) {
    printMissing(sync, { out: log });
    log(t("dryRun"));
    return { dryRun: true, sync };
  }
  // update never migrates CLAUDE.md; init and `target add claude --yes` do (D40).
  const result = applySync(sync, { projectDir, previousManifest: manifest, migrateClaude: Boolean(opts.migrateClaude), backup: opts.backup !== false, runId });
  printMessages(result.messages.filter((m) => opts.migrateClaude !== undefined || m.key !== "claudeMigrateSkipped"), { out: log });
  if (result.backupDir) log(t("backupAt", { v: path.relative(projectDir, result.backupDir) }));
  return { dryRun: false, sync, result };
};

export const runUpdate = async (opts, { log = console.log, projectDir = process.cwd() } = {}) => {
  const manifest = requireManifest(projectDir);
  const r = runSync(projectDir, manifest, manifest.targets, opts, log);
  if (!r.dryRun) printOutcome(r.sync, { key: r.result.noop ? "upToDate" : "updated", vars: { version: packageVersion() }, out: log });
  return r;
};
