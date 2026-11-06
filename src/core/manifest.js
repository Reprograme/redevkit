// .redevkit/manifest.json: CLI state (not memory). Written atomically (Y18).
import path from "node:path";
import { atomicWrite, exists, isSafeRelative, readText } from "./fsutil.js";

export const SCHEMA_VERSION = 1;
export const MANIFEST_REL = ".redevkit/manifest.json";

export const manifestPath = (projectDir) => path.join(projectDir, ".redevkit", "manifest.json");

/** Returns { manifest } | { manifest: null } | { error }. */
export const loadManifest = (projectDir) => {
  const p = manifestPath(projectDir);
  if (!exists(p)) return { manifest: null };
  let data;
  try {
    data = JSON.parse(readText(p));
  } catch (err) {
    return { manifest: null, error: `manifest is not valid JSON: ${err.message}` };
  }
  if (data?.schemaVersion !== SCHEMA_VERSION || typeof data.files !== "object" || Array.isArray(data.files)) {
    return { manifest: null, error: "manifest has an unsupported schema" };
  }
  for (const [file, hash] of Object.entries(data.files)) {
    if (!isSafeRelative(file) || !/^[0-9a-f]{64}$/.test(hash)) return { manifest: null, error: `manifest has an unsafe entry: ${file}` };
  }
  data.targets = Array.isArray(data.targets) ? data.targets : [];
  data.context = data.context ?? {};
  data.config = data.config ?? {};
  return { manifest: data };
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
