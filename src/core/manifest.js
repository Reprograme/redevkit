// .redevkit/manifest.json: CLI state (not memory). Written atomically (Y18).
import path from "node:path";
import { atomicWrite, exists, isSafeRelative, readText } from "./fsutil.js";

export const SCHEMA_VERSION = 1;
export const MANIFEST_REL = ".redevkit/manifest.json";
export const KNOWN_TARGETS = ["claude", "codex"];

export const manifestPath = (projectDir) => path.join(projectDir, ".redevkit", "manifest.json");

const isPlainObject = (v) => typeof v === "object" && v !== null && !Array.isArray(v);
const isStringList = (v) => Array.isArray(v) && v.every((x) => typeof x === "string");
const isOptional = (v, check) => v === undefined || check(v);
const isCodexKey = (k) => isPlainObject(k) && typeof k.table === "string" && k.table !== "" && typeof k.key === "string" && k.key !== "";

/**
 * Name of the first field the commands read that has the wrong shape, or null.
 * - `targets` must be a non-empty list of known targets without duplicates (B01): an empty or
 *   unknown list would make update plan the removal of every agent file.
 * - The nested fields of `context` and `config` are checked too (B19): a hand-edited
 *   `config.codexKeys: 123` must stop every command before it writes, not halfway through an install.
 */
export const manifestFieldError = (data) => {
  if (!isOptional(data.version, (v) => typeof v === "string")) return "version";
  if (!isOptional(data.lang, (v) => typeof v === "string")) return "lang";
  if (!isOptional(data.lastRunId, (v) => typeof v === "string")) return "lastRunId";
  const tg = data.targets;
  if (!Array.isArray(tg) || tg.length === 0 || !tg.every((x) => KNOWN_TARGETS.includes(x)) || new Set(tg).size !== tg.length) return "targets";
  if (data.context !== undefined && data.context !== null) {
    const c = data.context;
    if (!isPlainObject(c)) return "context";
    if (!isOptional(c.agentsBlockHash, (v) => typeof v === "string")) return "context.agentsBlockHash";
    if (!isOptional(c.claudePointer, (v) => typeof v === "boolean")) return "context.claudePointer";
  }
  if (data.config !== undefined && data.config !== null) {
    const c = data.config;
    if (!isPlainObject(c)) return "config";
    if (!isOptional(c.claudeAllow, isStringList)) return "config.claudeAllow";
    if (!isOptional(c.claudeSettingsCreated, (v) => typeof v === "boolean")) return "config.claudeSettingsCreated";
    if (!isOptional(c.codexKeys, (v) => Array.isArray(v) && v.every(isCodexKey))) return "config.codexKeys";
  }
  return null;
};

const FIELD_HINT = {
  targets: " (expected a non-empty list of claude and/or codex, without duplicates)",
  "config.codexKeys": " (expected a list of { table, key })",
  "config.claudeAllow": " (expected a list of strings)",
};

/** Error text for manifest data, or null when every field the commands read is valid. */
export const manifestDataError = (data) => {
  if (!isPlainObject(data) || data.schemaVersion !== SCHEMA_VERSION || !isPlainObject(data.files)) return "manifest has an unsupported schema";
  // Every field the commands read is type-checked here, so a hand-edited manifest becomes an
  // "invalid manifest" error instead of a TypeError thrown later (A19: `files: null`).
  const badField = manifestFieldError(data);
  if (badField) return `manifest has an invalid "${badField}" field${FIELD_HINT[badField] ?? ""}`;
  for (const [file, hash] of Object.entries(data.files)) {
    if (!isSafeRelative(file) || typeof hash !== "string" || !/^[0-9a-f]{64}$/.test(hash)) return `manifest has an unsafe entry: ${file}`;
  }
  return null;
};

/** Returns { manifest } | { manifest: null } (absent) | { manifest: null, error } (present but invalid). */
export const loadManifest = (projectDir) => {
  const p = manifestPath(projectDir);
  if (!exists(p)) return { manifest: null };
  let data;
  try {
    data = JSON.parse(readText(p));
  } catch (err) {
    return { manifest: null, error: `manifest is not valid JSON: ${err.message}` };
  }
  const error = manifestDataError(data);
  if (error) return { manifest: null, error };
  data.context = data.context ?? {};
  data.config = data.config ?? {};
  return { manifest: data };
};

/**
 * Id of the run that produced the current state (the manifest's lastRunId), read leniently: rollback
 * needs it even when the manifest is invalid. { known: true, runId: null } when there is no manifest
 * (never installed, or uninstalled); { known: false } when it cannot be read.
 */
export const readStateId = (projectDir) => {
  const p = manifestPath(projectDir);
  if (!exists(p)) return { known: true, runId: null };
  try {
    const data = JSON.parse(readText(p));
    if (isPlainObject(data) && typeof data.lastRunId === "string") return { known: true, runId: data.lastRunId };
  } catch {
    // unreadable: unknown state
  }
  return { known: false };
};

export const writeManifest = (projectDir, manifest) => {
  const sortedFiles = Object.fromEntries(Object.entries(manifest.files).sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0)));
  const out = { ...manifest, schemaVersion: SCHEMA_VERSION, files: sortedFiles };
  atomicWrite(manifestPath(projectDir), `${JSON.stringify(out, null, 2)}\n`);
  return out;
};

export const newManifest = ({ version, targets, lang, runId }) => {
  const now = new Date().toISOString();
  return {
    schemaVersion: SCHEMA_VERSION,
    tool: "redevkit",
    version,
    targets,
    lang,
    installedAt: now,
    updatedAt: now,
    lastRunId: runId,
    files: {},
    context: {},
    config: {},
  };
};
