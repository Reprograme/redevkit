// redevkit status [--quiet]  and  redevkit version [--check]  (§10, C1)
import { hashFileIfExists, resolveInside } from "../core/fsutil.js";
import { getLang } from "../core/i18n.js";
import { packageVersion } from "../core/render.js";
import { compare, isValid } from "../core/semver.js";
import { requireManifest } from "./update.js";

const L = (pt, en) => (getLang() === "pt-BR" ? pt : en);

export const managedDrift = (projectDir, manifest) => {
  const modified = [];
  const missing = [];
  for (const [rel, hash] of Object.entries(manifest.files)) {
    const cur = hashFileIfExists(resolveInside(projectDir, rel));
    if (cur === undefined) missing.push(rel);
    else if (cur !== hash) modified.push(rel);
  }
  return { modified, missing };
};

export const versionRelation = (installed, current) => {
  if (!isValid(installed) || !isValid(current)) return "unknown";
  const c = compare(installed, current);
  return c === 0 ? "same" : c < 0 ? "older" : "newer";
};

export const runStatus = async (opts, { log = console.log, projectDir = process.cwd() } = {}) => {
  const manifest = requireManifest(projectDir);
  const cliVersion = packageVersion();
  const relation = versionRelation(manifest.version, cliVersion);
  const drift = managedDrift(projectDir, manifest);
  const report = { installed: manifest.version, cli: cliVersion, relation, targets: manifest.targets, lang: manifest.lang, ...drift };
  if (opts.json) {
    log(JSON.stringify(report, null, 2));
    return report;
  }
  if (opts.quiet) {
    log(`${manifest.version} ${relation} ${drift.modified.length}M ${drift.missing.length}D`);
    return report;
  }
  log(`REDEVKIT ${L("instalado", "installed")}: ${manifest.version} · CLI: ${cliVersion}`);
  if (relation === "older") log(L(`Há uma versão mais nova nesta CLI (${cliVersion}). Rode: redevkit update`, `This CLI has a newer version (${cliVersion}). Run: redevkit update`));
  if (relation === "newer") log(L("A instalação é mais nova que esta CLI; atualize a CLI antes de rodar update.", "The installation is newer than this CLI; upgrade the CLI before running update."));
  if (relation === "unknown") log(L("Versão não comparável (semver inválido).", "Versions not comparable (invalid semver)."));
  log(`${L("Alvos", "Targets")}: ${manifest.targets.join(", ")} · ${L("Idioma", "Language")}: ${manifest.lang}`);
  log(`${L("Arquivos gerenciados", "Managed files")}: ${Object.keys(manifest.files).length} · ${L("alterados", "modified")}: ${drift.modified.length} · ${L("ausentes", "missing")}: ${drift.missing.length}`);
  for (const f of drift.modified) log(`  M ${f}`);
  for (const f of drift.missing) log(`  D ${f}`);
  log(L(
    "Versão publicada no npm não consultada (o status funciona offline). Para checar: redevkit version --check",
    "Published npm version not checked (status works offline). To check: redevkit version --check",
  ));
  return report;
};

export const fetchLatest = async ({ timeoutMs = 4000, fetchImpl = globalThis.fetch } = {}) => {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const res = await fetchImpl("https://registry.npmjs.org/redevkit/latest", { signal: ctrl.signal, headers: { accept: "application/json" } });
    if (res.status === 404) return { ok: false, reason: "not-published" };
    if (!res.ok) return { ok: false, reason: `http-${res.status}` };
    const data = await res.json();
    return { ok: true, version: data.version };
  } catch (err) {
    return { ok: false, reason: err.name === "AbortError" ? "timeout" : "offline" };
  } finally {
    clearTimeout(timer);
  }
};

export const runVersion = async (opts, { log = console.log, fetchImpl } = {}) => {
  const v = packageVersion();
  log(v);
  if (!opts.check) return { version: v };
  const latest = await fetchLatest({ fetchImpl });
  if (!latest.ok) {
    const msg = {
      offline: L("Não foi possível consultar o npm (sem rede). A versão mais recente é desconhecida.", "Could not reach npm (offline). The latest version is unknown."),
      timeout: L("O npm não respondeu a tempo. A versão mais recente é desconhecida.", "npm did not answer in time. The latest version is unknown."),
      "not-published": L("O pacote ainda não está publicado no npm.", "The package is not published on npm yet."),
    }[latest.reason] ?? L(`Falha ao consultar o npm (${latest.reason}).`, `npm query failed (${latest.reason}).`);
    log(msg);
    return { version: v, latest: null, reason: latest.reason };
  }
  const rel = versionRelation(v, latest.version);
  log(rel === "older" ? L(`Nova versão disponível: ${latest.version}`, `New version available: ${latest.version}`) : L("Você está na versão mais recente.", "You are on the latest version."));
  return { version: v, latest: latest.version, relation: rel };
};
