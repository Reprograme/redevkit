// Shared install/update engine used by init, update and target add/remove.
import path from "node:path";
import { appendMigratedNotes, blockInner, isPointer, migratableContent, simpleDiff, upsertAgentsBlock } from "./context-files.js";
import { assertRemovable, assertWritable, exists, readText, removeInside, resolveInside, sha256, writeInside } from "./fsutil.js";
import { applyPlan, CONFLICT_ROOT, createBackup, createPlan, createRunId, nextManifestFiles, RESTORED } from "./managed-tree.js";
import { loadManifest, MANIFEST_REL, manifestDataError, newManifest, SCHEMA_VERSION, writeManifest } from "./manifest.js";
import { KIT_ROOT, loadRuntimeEntries, packageVersion, renderAgentsBlock, renderAll, renderClaudePointer } from "./render.js";
import { mergeClaudeSettings, mergeCodexConfig, unmergeClaudeSettings, unmergeCodexConfig } from "./runtime-config.js";

export const CONTEXT_FILES = ["AGENTS.md", "CLAUDE.md"];
export const CONFIG_FILES = { claude: ".claude/settings.json", codex: ".codex/config.toml" };

const readRel = (projectDir, rel) => {
  const abs = resolveInside(projectDir, rel);
  return exists(abs) ? readText(abs) : null;
};

export const today = () => new Date().toISOString().slice(0, 10);

/**
 * Managed files the pipeline cannot run without: the `redevkit-*` skill directories (commands,
 * phases and the memory skill, with their references), the audits and the templates. Knowledge
 * skills and personas are optional: a user may delete one on purpose (catalog budget).
 */
export const isPipelineCore = (rel) =>
  /^\.(claude|agents)\/skills\/redevkit-[^/]+\//.test(rel) || rel.startsWith(".redevkit/audits/") || rel.startsWith(".redevkit/templates/");

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
 * opts: { projectDir, targets, lang, force, restore, kitRoot, version }
 * `restore` re-adds managed files that are missing locally; `force` implies it.
 */
export const computeSync = ({ projectDir, targets, lang, force = false, restore = false, kitRoot = KIT_ROOT, version = packageVersion(), previousManifest = null }) => {
  const { files: incoming } = renderAll({ targets, lang, version, kitRoot });
  const previous = previousManifest?.files ?? {};
  const plan = createPlan({ projectDir, incoming, previous, hasManifest: Boolean(previousManifest), force, restore: restore || force });

  // AGENTS.md block
  const block = renderAgentsBlock({ targets, lang, version, kitRoot });
  const agentsBefore = readRel(projectDir, "AGENTS.md");
  let agentsAfter = upsertAgentsBlock(agentsBefore, block, lang);
  // Same content with CRLF line endings (autocrlf checkout): leave the file as it is.
  if (agentsBefore !== null && agentsAfter === agentsBefore.replace(/\r\n/g, "\n")) agentsAfter = agentsBefore;
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

/**
 * True when applying would not change any file (idempotent re-runs write nothing). Only what this
 * call applies counts: a CLAUDE.md migration that is not going to run (update never migrates, A15)
 * is not a change.
 */
export const isNoop = (sync, previousManifest, { migrateClaude = false } = {}) => {
  if (!previousManifest) return false;
  if (sync.plan.actions.length || sync.plan.conflicts.length) return false;
  if (sync.agentsAfter !== sync.agentsBefore) return false;
  if (sync.claude.action === "create" || (sync.claude.action === "migrate" && migrateClaude)) return false;
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
 *
 * Validate before writing (B19): every content (AGENTS.md, CLAUDE.md, config merges), the next
 * manifest and every target path are prepared and checked first; only then the backup is taken and
 * the files are written. An error therefore never leaves a half-applied install.
 */
export const applySync = (sync, { projectDir, previousManifest = null, migrateClaude = false, backup = true, runId = createRunId() }) => {
  const { plan, incoming } = sync;
  const messages = [];

  // A manifest object that did not come through loadManifest is checked too.
  if (previousManifest) {
    const error = manifestDataError(previousManifest);
    if (error) throw new Error(`Invalid manifest: ${error}`);
  }
  if (isNoop(sync, previousManifest, { migrateClaude })) return { backupDir: null, conflictCopies: [], messages, manifest: previousManifest, noop: true };

  // 1. Prepare. `ops` are the writes and removals after the managed files, in order.
  const ops = [];
  const write = (rel, data) => ops.push({ type: "write", rel, data });
  const remove = (rel) => ops.push({ type: "remove", rel });

  // AGENTS.md block (+ CLAUDE.md migration).
  let agentsText = sync.agentsAfter;
  let claudePointer = previousManifest?.context?.claudePointer ?? false;
  let migratedMessage = null;
  if (sync.claude.action === "migrate") {
    if (migrateClaude) {
      if (sync.claude.migrated) agentsText = appendMigratedNotes(agentsText, sync.claude.migrated, sync.lang, today());
      write("CLAUDE.md", sync.claude.after);
      claudePointer = true;
      migratedMessage = { key: "claudeMigrated", vars: { v: "-" } };
      messages.push(migratedMessage);
    } else {
      messages.push({ key: "claudeMigrateSkipped" });
    }
  } else if (sync.claude.action === "create") {
    write("CLAUDE.md", sync.claude.after);
    claudePointer = true;
  } else if (sync.targets.includes("claude")) {
    claudePointer = true;
  }
  if (agentsText !== sync.agentsBefore) write("AGENTS.md", agentsText);

  // Runtime config.
  const config = { ...(previousManifest?.config ?? {}) };
  if (sync.config.claude) {
    const c = sync.config.claude;
    if (!c.ok) messages.push({ key: "configInvalid", vars: { file: CONFIG_FILES.claude, err: c.error }, level: "warn" });
    else {
      if (c.changed) write(CONFIG_FILES.claude, c.text);
      config.claudeAllow = [...new Set([...(config.claudeAllow ?? []), ...c.added])];
      if (c.created) config.claudeSettingsCreated = true;
      if (c.added.length) messages.push({ key: "configAdded", vars: { file: CONFIG_FILES.claude, n: c.added.length } });
    }
  }
  if (sync.config.codex) {
    const c = sync.config.codex;
    if (!c.ok) messages.push({ key: "configInvalid", vars: { file: CONFIG_FILES.codex, err: c.error }, level: "warn" });
    else {
      if (c.changed) write(CONFIG_FILES.codex, c.text);
      const keys = new Map((config.codexKeys ?? []).map((k) => [`${k.table}.${k.key}`, k]));
      for (const k of c.added) keys.set(`${k.table}.${k.key}`, k);
      config.codexKeys = [...keys.values()];
      for (const k of c.kept) messages.push({ key: "configKept", vars: { file: CONFIG_FILES.codex, key: `${k.table}.${k.key}`, val: JSON.stringify(k.userValue) } });
      for (const k of c.skipped ?? []) messages.push({ key: "configSkipped", vars: { file: CONFIG_FILES.codex, key: `${k.table}.${k.key}`, table: k.table, val: k.value }, level: "warn" });
      if (c.added.length) messages.push({ key: "configAdded", vars: { file: CONFIG_FILES.codex, n: c.added.length } });
    }
  }
  if (sync.unconfig.claude?.ok && sync.unconfig.claude.text !== undefined) {
    if (sync.unconfig.claude.text === null) remove(CONFIG_FILES.claude);
    else write(CONFIG_FILES.claude, sync.unconfig.claude.text);
    delete config.claudeAllow;
    delete config.claudeSettingsCreated;
  }
  if (sync.unconfig.codex?.ok) {
    // text is undefined when nothing of ours is in the file (or there is no file): leave it alone (A16).
    if (sync.unconfig.codex.text === null) remove(CONFIG_FILES.codex);
    else if (sync.unconfig.codex.text !== undefined) write(CONFIG_FILES.codex, sync.unconfig.codex.text);
    delete config.codexKeys;
  }

  // Next manifest.
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
  const manifestError = manifestDataError({ ...manifest, schemaVersion: SCHEMA_VERSION });
  if (manifestError) throw new Error(`Refusing to write an invalid manifest: ${manifestError}`);

  // Every path is checked before the first write (links, directories in the way).
  for (const a of plan.actions) {
    if (a.type === "delete") assertRemovable(projectDir, a.file);
    else assertWritable(projectDir, a.file);
  }
  for (const c of plan.conflicts) if (c.incomingHash && incoming.has(c.file)) assertWritable(projectDir, `${CONFLICT_ROOT}/${runId}/${c.file}`);
  for (const op of ops) {
    if (op.type === "write") assertWritable(projectDir, op.rel);
    else assertRemovable(projectDir, op.rel);
  }
  assertWritable(projectDir, MANIFEST_REL);

  // 2. Backup everything we may modify or delete.
  // A restored file is listed although it does not exist yet: it is recorded as absent, so a
  // rollback of this run removes it again (it was managed before the run, so nothing else would).
  const touched = [
    ...plan.actions.filter((a) => a.type !== "add" || a.reason === RESTORED || exists(resolveInside(projectDir, a.file))).map((a) => a.file),
    "AGENTS.md",
    MANIFEST_REL,
  ];
  if (sync.claude.action === "migrate" && migrateClaude) touched.push("CLAUDE.md");
  if (sync.claude.action === "create") touched.push("CLAUDE.md"); // recorded as absent: a rollback removes it
  if (sync.config.claude?.ok && sync.config.claude.changed) touched.push(CONFIG_FILES.claude);
  if (sync.config.codex?.ok && sync.config.codex.changed) touched.push(CONFIG_FILES.codex);
  if (sync.unconfig.claude) touched.push(CONFIG_FILES.claude);
  if (sync.unconfig.codex) touched.push(CONFIG_FILES.codex);
  // A forced overwrite of a user's file is always backed up, even on a first init (no manifest, no AGENTS.md).
  const forcedOverwrite = plan.actions.some((a) => String(a.reason ?? "").startsWith("forced"));
  // So is a user's own settings.json / config.toml that the config merge rewrites.
  const userConfigChanged = Object.values(sync.config).some((c) => c?.ok && c.changed && c.before !== null && c.before !== undefined);
  const needsBackup =
    touched.some((rel) => exists(resolveInside(projectDir, rel))) &&
    (previousManifest || sync.claude.action === "migrate" || sync.agentsBefore !== null || forcedOverwrite || userConfigChanged);
  const previousFiles = previousManifest ? Object.keys(previousManifest.files) : [];
  const backupDir = backup && needsBackup
    ? createBackup({
        projectDir,
        files: touched,
        runId,
        reason: previousManifest ? "update" : "init",
        version: sync.version,
        manifestFiles: previousFiles,
        recordAbsent: true,
        // A12: files that already existed with the managed content and become managed now. The run
        // did not create them, so a rollback must leave them in place.
        adopted: plan.unchanged.filter((f) => !previousManifest?.files?.[f]),
        // B02: the state this backup returns to and the state the run leaves.
        link: { runId, previousRunId: previousManifest ? previousManifest.lastRunId : null, resultRunId: runId },
        missingBefore: previousFiles.filter((f) => !exists(resolveInside(projectDir, f))),
      })
    : null;
  if (migratedMessage) migratedMessage.vars.v = backupDir ? path.relative(projectDir, backupDir) : "-";

  // 3. Write: managed files, then context and config files, then the manifest.
  const { conflictCopies } = applyPlan({ projectDir, plan, incoming, runId });
  for (const op of ops) {
    if (op.type === "write") writeInside(projectDir, op.rel, op.data);
    else removeInside(projectDir, op.rel);
  }
  writeManifest(projectDir, manifest);
  return { backupDir, conflictCopies, messages, manifest };
};

export { loadManifest };
