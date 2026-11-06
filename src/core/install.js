// Shared install/update engine used by init, update and target add/remove.
import path from "node:path";
import { appendMigratedNotes, blockInner, isPointer, migratableContent, simpleDiff, upsertAgentsBlock } from "./context-files.js";
import { exists, readText, removeInside, resolveInside, sha256, writeInside } from "./fsutil.js";
import { applyPlan, createBackup, createPlan, createRunId, nextManifestFiles } from "./managed-tree.js";
import { loadManifest, newManifest, writeManifest } from "./manifest.js";
import { KIT_ROOT, loadRuntimeEntries, packageVersion, renderAgentsBlock, renderAll, renderClaudePointer } from "./render.js";
import { mergeClaudeSettings, mergeCodexConfig, unmergeClaudeSettings, unmergeCodexConfig } from "./runtime-config.js";

export const CONTEXT_FILES = ["AGENTS.md", "CLAUDE.md"];
export const CONFIG_FILES = { claude: ".claude/settings.json", codex: ".codex/config.toml" };

const readRel = (projectDir, rel) => {
  const abs = resolveInside(projectDir, rel);
  return exists(abs) ? readText(abs) : null;
};

export const today = () => new Date().toISOString().slice(0, 10);

/** What already exists in the project (init reporting). */
export const detectProject = (projectDir) => {
  const found = [];
  for (const rel of ["AGENTS.md", "CLAUDE.md", ".claude", ".agents", ".codex", "specs", "DESIGN.md"]) {
    if (exists(path.join(projectDir, rel))) found.push(rel);
  }
  const legacy = [];
  for (const rel of ["memory-bank", ".agents/memory", ".specify/memory"]) {
    if (exists(path.join(projectDir, ...rel.split("/")))) legacy.push(rel);
  }
  return { found, legacy };
};

/**
 * Compute everything an install/update would do, without writing.
 * opts: { projectDir, targets, lang, force, kitRoot, version }
 */
export const computeSync = ({ projectDir, targets, lang, force = false, kitRoot = KIT_ROOT, version = packageVersion(), previousManifest = null }) => {
  const { files: incoming } = renderAll({ targets, lang, version, kitRoot });
  const previous = previousManifest?.files ?? {};
  const plan = createPlan({ projectDir, incoming, previous, hasManifest: Boolean(previousManifest), force });

  // AGENTS.md block
  const block = renderAgentsBlock({ targets, lang, version, kitRoot });
  const agentsBefore = readRel(projectDir, "AGENTS.md");
  let agentsAfter = upsertAgentsBlock(agentsBefore, block, lang);
  const userEditedBlock =
    previousManifest?.context?.agentsBlockHash && agentsBefore && blockInner(agentsBefore) !== null &&
    sha256(blockInner(agentsBefore)) !== previousManifest.context.agentsBlockHash;

  // CLAUDE.md pointer and migration (D40)
  let claude = { action: "none" };
  if (targets.includes("claude")) {
    const pointer = renderClaudePointer({ lang, kitRoot });
    const pointers = ["pt-BR", "en"].map((l) => renderClaudePointer({ lang: l, kitRoot }));
    const before = readRel(projectDir, "CLAUDE.md");
    if (before === null) claude = { action: "create", after: pointer };
    else if (isPointer(before, pointers)) claude = before.replace(/\r\n?/g, "\n") === pointer ? { action: "none" } : { action: "none", note: "pointer-variant" };
    else {
      const migrated = migratableContent(before);
      claude = { action: "migrate", before, after: pointer, migrated, diff: simpleDiff(before, pointer) };
    }
  }

  // Runtime config (D51)
  const entries = loadRuntimeEntries(kitRoot);
  const config = {};
  if (targets.includes("claude")) {
    const before = readRel(projectDir, CONFIG_FILES.claude);
    config.claude = { before, ...mergeClaudeSettings(before, entries.claudeAllow) };
  }
  if (targets.includes("codex")) {
    const before = readRel(projectDir, CONFIG_FILES.codex);
    config.codex = { before, ...mergeCodexConfig(before, entries.codexEntries) };
  }
  // Targets being removed: unmerge their config.
  const removedTargets = (previousManifest?.targets ?? []).filter((t) => !targets.includes(t));
  const unconfig = {};
  if (removedTargets.includes("claude")) {
    const before = readRel(projectDir, CONFIG_FILES.claude);
    unconfig.claude = { before, ...unmergeClaudeSettings(before, previousManifest.config?.claudeAllow ?? [], { deleteIfEmpty: Boolean(previousManifest.config?.claudeSettingsCreated) }) };
  }
  if (removedTargets.includes("codex")) {
    const before = readRel(projectDir, CONFIG_FILES.codex);
    unconfig.codex = { before, ...unmergeCodexConfig(before) };
  }

  return { incoming, plan, block, agentsBefore, agentsAfter, userEditedBlock, claude, config, unconfig, removedTargets, version, targets, lang };
};

/** Summary counts for messages. */
export const summarize = (plan) => ({
  add: plan.actions.filter((a) => a.type === "add").length,
  update: plan.actions.filter((a) => a.type === "update").length,
  del: plan.actions.filter((a) => a.type === "delete").length,
  same: plan.unchanged.length,
  conf: plan.conflicts.length,
  keep: plan.preserved.length,
});

/** True when applying would not change any file (idempotent re-runs write nothing). */
export const isNoop = (sync, previousManifest) => {
  if (!previousManifest) return false;
  if (sync.plan.actions.length || sync.plan.conflicts.length) return false;
  if (sync.agentsAfter !== sync.agentsBefore) return false;
  if (sync.claude.action !== "none") return false;
  if (Object.values(sync.config).some((c) => c && c.ok && c.changed)) return false;
  if (Object.keys(sync.unconfig).length) return false;
  if (previousManifest.version !== sync.version || previousManifest.lang !== sync.lang) return false;
  if ([...previousManifest.targets].sort().join() !== [...sync.targets].sort().join()) return false;
  const next = nextManifestFiles(sync.plan, previousManifest.files);
  const prev = previousManifest.files;
  return Object.keys(next).length === Object.keys(prev).length && Object.entries(next).every(([k, v]) => prev[k] === v);
};

/**
 * Apply a computed sync.
 * opts.migrateClaude: boolean decision for the CLAUDE.md migration.
 * Returns a report with backupDir, messages and the new manifest.
 */
export const applySync = (sync, { projectDir, previousManifest = null, migrateClaude = false, backup = true, runId = createRunId() }) => {
  const { plan, incoming } = sync;
  const messages = [];

  if (isNoop(sync, previousManifest)) return { backupDir: null, conflictCopies: [], messages, manifest: previousManifest, noop: true };

  // 1. Backup everything we may modify or delete.
  const touched = [
    ...plan.actions.filter((a) => a.type !== "add" || exists(resolveInside(projectDir, a.file))).map((a) => a.file),
    "AGENTS.md",
    ".redevkit/manifest.json",
  ];
  if (sync.claude.action === "migrate" && migrateClaude) touched.push("CLAUDE.md");
  if (sync.config.claude?.ok && sync.config.claude.changed) touched.push(CONFIG_FILES.claude);
  if (sync.config.codex?.ok && sync.config.codex.changed) touched.push(CONFIG_FILES.codex);
  if (sync.unconfig.claude) touched.push(CONFIG_FILES.claude);
  if (sync.unconfig.codex) touched.push(CONFIG_FILES.codex);
  const needsBackup = touched.some((rel) => exists(resolveInside(projectDir, rel))) && (previousManifest || sync.claude.action === "migrate" || sync.agentsBefore !== null);
  const backupDir = backup && needsBackup
    ? createBackup({ projectDir, files: touched, runId, reason: previousManifest ? "update" : "init", version: sync.version, manifestFiles: previousManifest ? Object.keys(previousManifest.files) : [] })
    : null;

  // 2. Managed files.
  const { conflictCopies } = applyPlan({ projectDir, plan, incoming, runId });

  // 3. AGENTS.md block (+ CLAUDE.md migration).
  let agentsText = sync.agentsAfter;
  let claudePointer = previousManifest?.context?.claudePointer ?? false;
  if (sync.claude.action === "migrate") {
    if (migrateClaude) {
      if (sync.claude.migrated) agentsText = appendMigratedNotes(agentsText, sync.claude.migrated, sync.lang, today());
      writeInside(projectDir, "CLAUDE.md", sync.claude.after);
      claudePointer = true;
      messages.push({ key: "claudeMigrated", vars: { v: backupDir ? path.relative(projectDir, backupDir) : "-" } });
    } else {
      messages.push({ key: "claudeMigrateSkipped" });
    }
  } else if (sync.claude.action === "create") {
    writeInside(projectDir, "CLAUDE.md", sync.claude.after);
    claudePointer = true;
  } else if (sync.targets.includes("claude")) {
    claudePointer = true;
  }
  if (agentsText !== sync.agentsBefore) writeInside(projectDir, "AGENTS.md", agentsText);

  // 4. Runtime config.
  const config = { ...(previousManifest?.config ?? {}) };
  if (sync.config.claude) {
    const c = sync.config.claude;
    if (!c.ok) messages.push({ key: "configInvalid", vars: { file: CONFIG_FILES.claude, err: c.error }, level: "warn" });
    else {
      if (c.changed) writeInside(projectDir, CONFIG_FILES.claude, c.text);
      config.claudeAllow = [...new Set([...(config.claudeAllow ?? []), ...c.added])];
      if (c.created) config.claudeSettingsCreated = true;
      if (c.added.length) messages.push({ key: "configAdded", vars: { file: CONFIG_FILES.claude, n: c.added.length } });
    }
  }
  if (sync.config.codex) {
    const c = sync.config.codex;
    if (!c.ok) messages.push({ key: "configInvalid", vars: { file: CONFIG_FILES.codex, err: c.error }, level: "warn" });
    else {
      if (c.changed) writeInside(projectDir, CONFIG_FILES.codex, c.text);
      const keys = new Map((config.codexKeys ?? []).map((k) => [`${k.table}.${k.key}`, k]));
      for (const k of c.added) keys.set(`${k.table}.${k.key}`, k);
      config.codexKeys = [...keys.values()];
      for (const k of c.kept) messages.push({ key: "configKept", vars: { file: CONFIG_FILES.codex, key: `${k.table}.${k.key}`, val: JSON.stringify(k.userValue) } });
      if (c.added.length) messages.push({ key: "configAdded", vars: { file: CONFIG_FILES.codex, n: c.added.length } });
    }
  }
  if (sync.unconfig.claude?.ok && sync.unconfig.claude.text !== undefined) {
    if (sync.unconfig.claude.text === null) removeInside(projectDir, CONFIG_FILES.claude);
    else writeInside(projectDir, CONFIG_FILES.claude, sync.unconfig.claude.text);
    delete config.claudeAllow;
    delete config.claudeSettingsCreated;
  }
  if (sync.unconfig.codex?.ok && sync.unconfig.codex.text !== undefined) {
    if (sync.unconfig.codex.text === null) removeInside(projectDir, CONFIG_FILES.codex);
    else writeInside(projectDir, CONFIG_FILES.codex, sync.unconfig.codex.text);
    delete config.codexKeys;
  }

  // 5. Manifest.
  const base = previousManifest ?? newManifest({ version: sync.version, targets: sync.targets, lang: sync.lang, runId });
  const manifest = {
    ...base,
    version: sync.version,
    targets: sync.targets,
    lang: sync.lang,
    updatedAt: new Date().toISOString(),
    lastRunId: runId,
    files: nextManifestFiles(plan, previousManifest?.files ?? {}),
    context: { agentsBlockHash: sha256(blockInner(agentsText) ?? ""), claudePointer },
    config,
  };
  writeManifest(projectDir, manifest);
  return { backupDir, conflictCopies, messages, manifest };
};

export { loadManifest };
