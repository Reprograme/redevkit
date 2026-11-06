// redevkit uninstall [--dry-run] [--yes]  (§10)
// Removes managed files and managed config entries. Keeps .redevkit/memory/, specs/, DESIGN.md,
// the AGENTS.md notes and the CLAUDE.md pointer. Locally modified managed files are kept too.
import { removeAgentsBlock } from "../core/context-files.js";
import { exists, hashFileIfExists, readText, removeInside, resolveInside, writeInside } from "../core/fsutil.js";
import { isYes, t } from "../core/i18n.js";
import { CONFIG_FILES, CONTEXT_FILES } from "../core/install.js";
import { createBackup, createRunId } from "../core/managed-tree.js";
import { MANIFEST_REL } from "../core/manifest.js";
import { ask, isInteractive } from "../core/prompt.js";
import { unmergeClaudeSettings, unmergeCodexConfig } from "../core/runtime-config.js";
import { CliError } from "./init.js";
import { requireManifest } from "./update.js";

export const runUninstall = async (opts, { log = console.log, projectDir = process.cwd() } = {}) => {
  const manifest = requireManifest(projectDir);
  const remove = [];
  const keptModified = [];
  for (const [rel, hash] of Object.entries(manifest.files)) {
    const cur = hashFileIfExists(resolveInside(projectDir, rel));
    if (cur === undefined) continue;
    if (cur === hash || opts.force) remove.push(rel);
    else keptModified.push(rel);
  }
  log(`${remove.length} managed file(s) to remove; ${keptModified.length} locally modified kept.`);
  for (const f of keptModified) log(`  kept (modified): ${f}`);
  if (opts.dryRun) {
    for (const f of remove) log(`  remove ${f}`);
    log(t("dryRun"));
    return { dryRun: true, remove, keptModified };
  }
  if (!opts.yes) {
    if (!isInteractive()) throw new CliError(t("noTtyNeedsYes"), 2);
    if (!isYes(await ask(t("uninstallAsk")))) {
      log(t("aborted"));
      return { aborted: true };
    }
  }
  const runId = createRunId();
  const backupDir = createBackup({
    projectDir,
    files: [...remove, ...CONTEXT_FILES, ...Object.values(CONFIG_FILES), MANIFEST_REL],
    runId,
    reason: "uninstall",
    version: manifest.version,
    manifestFiles: Object.keys(manifest.files),
  });
  for (const rel of remove) removeInside(projectDir, rel);

  const agentsAbs = resolveInside(projectDir, "AGENTS.md");
  if (exists(agentsAbs)) {
    const after = removeAgentsBlock(readText(agentsAbs));
    if (after.trim()) writeInside(projectDir, "AGENTS.md", after);
    else removeInside(projectDir, "AGENTS.md", { pruneParents: false });
  }
  const settingsAbs = resolveInside(projectDir, CONFIG_FILES.claude);
  if (manifest.config?.claudeAllow?.length && exists(settingsAbs)) {
    const r = unmergeClaudeSettings(readText(settingsAbs), manifest.config.claudeAllow, { deleteIfEmpty: Boolean(manifest.config.claudeSettingsCreated) });
    if (!r.ok) log(`! ${CONFIG_FILES.claude}: ${r.error}`);
    else if (r.text === null) removeInside(projectDir, CONFIG_FILES.claude);
    else if (r.text !== undefined) writeInside(projectDir, CONFIG_FILES.claude, r.text);
  }
  const codexAbs = resolveInside(projectDir, CONFIG_FILES.codex);
  if (exists(codexAbs)) {
    const r = unmergeCodexConfig(readText(codexAbs));
    if (r.text === null) removeInside(projectDir, CONFIG_FILES.codex);
    else if (r.text !== undefined && r.removed) writeInside(projectDir, CONFIG_FILES.codex, r.text);
  }
  removeInside(projectDir, MANIFEST_REL, { pruneParents: false });
  log(t("uninstallDone"));
  if (backupDir) log(t("backupAt", { v: backupDir }));
  return { removed: remove, keptModified, backupDir };
};
