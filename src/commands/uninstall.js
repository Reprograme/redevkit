// redevkit uninstall [--dry-run] [--yes]  (§10)
// Removes managed files and managed config entries. Keeps .redevkit/memory/, specs/, DESIGN.md,
// the AGENTS.md notes and the CLAUDE.md pointer. Locally modified managed files are kept too.
import { removeAgentsBlock } from "../core/context-files.js";
import { assertRemovable, assertWritable, exists, hashFileIfExists, readText, removeInside, resolveInside, writeInside } from "../core/fsutil.js";
import { isYes, t } from "../core/i18n.js";
import { CONFIG_FILES, CONTEXT_FILES } from "../core/install.js";
import { withWriteLock } from "../core/lock.js";
import { createBackup, createRunId } from "../core/managed-tree.js";
import { MANIFEST_REL } from "../core/manifest.js";
import { ask, isInteractive } from "../core/prompt.js";
import { unmergeClaudeSettings, unmergeCodexConfig } from "../core/runtime-config.js";
import { CliError } from "./init.js";
import { requireManifest } from "./update.js";

/**
 * Every change to AGENTS.md, .claude/settings.json and .codex/config.toml, computed before anything
 * is removed (B11). Returns { ops: [{ type: "write"|"remove", rel, data }], warnings }; throws a
 * CliError (nothing touched) when AGENTS.md has a malformed REDEVKIT block.
 */
export const planUninstallContext = (projectDir, manifest) => {
  const ops = [];
  const warnings = [];
  const agentsAbs = resolveInside(projectDir, "AGENTS.md");
  if (exists(agentsAbs)) {
    const before = readText(agentsAbs);
    let after;
    try {
      after = removeAgentsBlock(before);
    } catch {
      throw new CliError(t("agentsMalformed"), 1);
    }
    if (!after.trim()) ops.push({ type: "remove", rel: "AGENTS.md", pruneParents: false });
    else if (after !== before) ops.push({ type: "write", rel: "AGENTS.md", data: after });
  }
  const settingsAbs = resolveInside(projectDir, CONFIG_FILES.claude);
  if (manifest.config?.claudeAllow?.length && exists(settingsAbs)) {
    const r = unmergeClaudeSettings(readText(settingsAbs), manifest.config.claudeAllow, { deleteIfEmpty: Boolean(manifest.config.claudeSettingsCreated) });
    if (!r.ok) warnings.push(`! ${CONFIG_FILES.claude}: ${r.error}`);
    else if (r.text === null) ops.push({ type: "remove", rel: CONFIG_FILES.claude });
    else if (r.text !== undefined) ops.push({ type: "write", rel: CONFIG_FILES.claude, data: r.text });
  }
  // A16: touch .codex/config.toml only when the kit managed entries in it, and never delete a file
  // from which nothing was removed (an empty or user-only config is the user's).
  const codexAbs = resolveInside(projectDir, CONFIG_FILES.codex);
  const codexManaged = manifest.targets.includes("codex") || Boolean(manifest.config?.codexKeys?.length);
  if (codexManaged && exists(codexAbs)) {
    const r = unmergeCodexConfig(readText(codexAbs));
    if (r.removed > 0) {
      if (r.text === null) ops.push({ type: "remove", rel: CONFIG_FILES.codex });
      else if (r.text !== undefined) ops.push({ type: "write", rel: CONFIG_FILES.codex, data: r.text });
    }
  }
  return { ops, warnings };
};

export const runUninstall = async (opts, { log = console.log, projectDir = process.cwd() } = {}) => {
  if (opts.dryRun) return uninstall(opts, log, projectDir);
  return withWriteLock(projectDir, "uninstall", () => uninstall(opts, log, projectDir), { log });
};

const uninstall = async (opts, log, projectDir) => {
  const manifest = requireManifest(projectDir);
  const remove = [];
  const keptModified = [];
  const missing = [];
  for (const [rel, hash] of Object.entries(manifest.files)) {
    const cur = hashFileIfExists(resolveInside(projectDir, rel), hash);
    if (cur === undefined) {
      missing.push(rel);
      continue;
    }
    if (cur === hash || opts.force) remove.push(rel);
    else keptModified.push(rel);
  }
  // B11: compute and validate every transformation before the first removal (and in --dry-run).
  const { ops, warnings } = planUninstallContext(projectDir, manifest);
  for (const rel of remove) assertRemovable(projectDir, rel);
  for (const op of ops) {
    if (op.type === "write") assertWritable(projectDir, op.rel);
    else assertRemovable(projectDir, op.rel);
  }
  assertRemovable(projectDir, MANIFEST_REL);

  log(`${remove.length} managed file(s) to remove; ${keptModified.length} locally modified kept.`);
  for (const f of keptModified) log(`  kept (modified): ${f}`);
  for (const w of warnings) log(w);
  if (opts.dryRun) {
    for (const f of remove) log(`  remove ${f}`);
    for (const op of ops) log(`  ${op.type === "write" ? "update" : "remove"} ${op.rel}`);
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
    // B02: an uninstall leaves no manifest (state null); its backup returns to the installed state.
    link: { runId, previousRunId: manifest.lastRunId, resultRunId: null },
    missingBefore: missing,
  });
  for (const rel of remove) removeInside(projectDir, rel);
  for (const op of ops) {
    if (op.type === "write") writeInside(projectDir, op.rel, op.data);
    else removeInside(projectDir, op.rel, { pruneParents: op.pruneParents !== false });
  }
  removeInside(projectDir, MANIFEST_REL, { pruneParents: false });
  log(t("uninstallDone"));
  if (backupDir) log(t("backupAt", { v: backupDir }));
  return { removed: remove, keptModified, backupDir };
};
