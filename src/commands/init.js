// redevkit init [dir]  (§10)
import fs from "node:fs";
import path from "node:path";
import { applySync, computeSync, detectProject } from "../core/install.js";
import { isYes, setLang, t } from "../core/i18n.js";
import { withWriteLock } from "../core/lock.js";
import { createRunId } from "../core/managed-tree.js";
import { loadManifest } from "../core/manifest.js";
import { ask, isInteractive } from "../core/prompt.js";
import { LANGS, packageVersion } from "../core/render.js";
import { printConfigPreview, printMessages, printMissing, printOutcome, printPlan } from "./sync-report.js";
import { assertNoDowngrade } from "./update.js";

export const parseTargets = (value) => {
  if (!value) return null;
  const v = String(value).toLowerCase();
  if (v === "both" || v === "all") return ["claude", "codex"];
  const list = v.split(",").map((s) => s.trim());
  if (list.every((x) => x === "claude" || x === "codex")) return [...new Set(list)].sort();
  return undefined;
};

export class CliError extends Error {
  constructor(message, code = 1) {
    super(message);
    this.exitCode = code;
  }
}

export const resolveProjectDir = (dir, opts = {}) => (opts.here || !dir ? process.cwd() : path.resolve(dir));

export const runInit = async (dir, opts, { log = console.log } = {}) => {
  const projectDir = resolveProjectDir(dir, opts);
  // B14: the manifest is read under the write lock. A project directory that does not exist yet is
  // locked right after it is created (see below).
  if (opts.dryRun || !fs.existsSync(projectDir)) return initProject(projectDir, opts, log, false);
  return withWriteLock(projectDir, "init", () => initProject(projectDir, opts, log, true), { log });
};

const initProject = async (projectDir, opts, log, locked) => {
  const { manifest: previous, error: manifestError } = fs.existsSync(projectDir) ? loadManifest(projectDir) : { manifest: null };
  if (opts.lang && LANGS.includes(opts.lang)) setLang(opts.lang);
  else if (previous?.lang) setLang(previous.lang);
  // A13: a manifest that exists but cannot be read is not a first install. Writing defaults over it
  // would orphan the installed files and could switch targets and language: stop, write nothing.
  if (manifestError) throw new CliError(t("manifestInvalidInit", { v: manifestError }), 1);
  if (previous) assertNoDowngrade(previous, opts); // A14

  const interactive = isInteractive();
  if (!interactive && !opts.yes) throw new CliError(t("noTtyNeedsYes"), 2);

  let targets = parseTargets(opts.target);
  if (targets === undefined) throw new CliError(t("invalidTarget", { v: opts.target }), 2);
  if (opts.lang && !LANGS.includes(opts.lang)) throw new CliError(t("invalidLang", { v: opts.lang }), 2);
  let lang = opts.lang ?? null;

  if (!targets) {
    if (previous) targets = previous.targets;
    else if (interactive && !opts.yes) {
      const answer = await ask(t("askTarget"));
      targets = parseTargets(answer || "both");
      if (!targets) throw new CliError(t("invalidTarget", { v: answer }), 2);
    } else targets = ["claude", "codex"];
  }
  if (!lang) {
    if (previous) lang = previous.lang;
    else if (interactive && !opts.yes) {
      const answer = await ask(t("askLang"));
      lang = answer || "pt-BR";
      if (!LANGS.includes(lang)) throw new CliError(t("invalidLang", { v: answer }), 2);
    } else lang = "pt-BR";
  }
  setLang(lang);

  if (!fs.existsSync(projectDir)) {
    if (opts.dryRun) log(`(dry-run) mkdir ${projectDir}`);
    else fs.mkdirSync(projectDir, { recursive: true });
  }

  if (!locked && !opts.dryRun) {
    return withWriteLock(
      projectDir,
      "init",
      () => {
        // Created just now: if another operation installed here in the meantime, stop (nothing written).
        const again = loadManifest(projectDir);
        if (again.manifest || again.error) throw new CliError(t("lockChanged"), 1);
        return installProject(projectDir, opts, log, { previous, targets, lang });
      },
      { log },
    );
  }
  return installProject(projectDir, opts, log, { previous, targets, lang });
};

/** Plan and apply, with targets and language resolved (runs under the write lock unless --dry-run). */
const installProject = async (projectDir, opts, log, { previous, targets, lang }) => {
  const { found, legacy } = fs.existsSync(projectDir) ? detectProject(projectDir) : { found: [], legacy: [] };
  if (found.length) log(t("detected", { v: found.join(", ") }));
  if (legacy.length) log(t("legacyMemory", { v: legacy.join(", ") }));

  const sync = computeSync({ projectDir, targets, lang, force: Boolean(opts.force), previousManifest: previous });
  printPlan(sync, { verbose: Boolean(opts.verbose), out: log });
  printConfigPreview(sync, { out: log });

  if (opts.dryRun) {
    if (sync.claude.action === "migrate") log(sync.claude.diff);
    printMissing(sync, { out: log });
    log(t("dryRun"));
    return { dryRun: true, sync };
  }

  let migrateClaude = false;
  if (sync.claude.action === "migrate") {
    if (opts.yes) migrateClaude = true;
    else {
      log(sync.claude.diff);
      migrateClaude = isYes(await ask(t("claudeMigrateAsk")));
    }
  }

  const runId = createRunId();
  const result = applySync(sync, { projectDir, previousManifest: previous, migrateClaude, backup: opts.backup !== false, runId });
  printMessages(result.messages, { out: log });
  if (result.backupDir) log(t("backupAt", { v: path.relative(projectDir, result.backupDir) || result.backupDir }));
  printOutcome(sync, { key: result.noop ? "upToDate" : previous ? "updated" : "done", vars: { version: packageVersion(), targets: targets.join("+"), lang }, out: log });
  if (targets.includes("claude")) log(t("nextStepClaude"));
  if (targets.includes("codex")) log(t("nextStepCodex"));
  if (targets.includes("claude")) log(t("claudeTrust"));
  if (targets.includes("codex")) log(t("codexTrust"));
  return { dryRun: false, sync, result, projectDir };
};
