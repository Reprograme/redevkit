// redevkit doctor [--json]  (§10, §9.9). Exit code != 0 when an error is found.
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { parse as tomlParse } from "smol-toml";
import { measureCatalog } from "../core/catalog-budget.js";
import { blockInner, findBlock } from "../core/context-files.js";
import { exists, listFiles, readText, resolveInside } from "../core/fsutil.js";
import { parseFrontmatter } from "../core/frontmatter.js";
import { getLang, setLang } from "../core/i18n.js";
import { CONFIG_FILES } from "../core/install.js";
import { loadManifest } from "../core/manifest.js";
import { loadRuntimeEntries } from "../core/render.js";
import { codexEntriesPresent } from "../core/runtime-config.js";
import { validateAgentsBlock, validateRendered } from "../core/validate.js";
import { managedDrift } from "./status.js";

const AGENTS_MAX = 32 * 1024;

/** Locate an executable on PATH without a shell (Y1). */
export const which = (cmd, env = process.env) => {
  const exts = process.platform === "win32" ? (env.PATHEXT ?? ".COM;.EXE;.BAT;.CMD").split(";").filter(Boolean) : [""];
  for (const dir of (env.PATH ?? env.Path ?? "").split(path.delimiter).filter(Boolean)) {
    for (const ext of process.platform === "win32" ? ["", ...exts] : [""]) {
      const p = path.join(dir, cmd + ext.toLowerCase());
      const P = path.join(dir, cmd + ext);
      for (const cand of [P, p]) {
        try {
          if (fs.statSync(cand).isFile() && (process.platform !== "win32" || ext)) return cand;
        } catch {
          // keep looking
        }
      }
    }
  }
  return null;
};

/** Run `<cmd> <args>` and return trimmed output, or null when it does not actually run (R2/R3). */
export const probe = (cmd, args = ["--version"], { timeout = 15000 } = {}) => {
  const exe = which(cmd);
  if (!exe) return null;
  let r;
  if (process.platform === "win32" && /\.(cmd|bat)$/i.test(exe)) {
    r = spawnSync(process.env.ComSpec ?? "cmd.exe", ["/d", "/s", "/c", `"${exe}" ${args.join(" ")}`], { encoding: "utf8", timeout, windowsVerbatimArguments: true });
  } else {
    r = spawnSync(exe, args, { encoding: "utf8", timeout });
  }
  if (r.error || r.status !== 0) return null;
  const out = `${r.stdout ?? ""}${r.stderr ?? ""}`.trim();
  return out ? out.split(/\r?\n/)[0] : null;
};

/** Python detection used by the audits: python, py -3 (Windows), python3; validated by executing. */
export const detectPython = () => {
  const candidates = [["python", []], ...(process.platform === "win32" ? [["py", ["-3"]]] : []), ["python3", []]];
  for (const [cmd, pre] of candidates) {
    const v = probe(cmd, [...pre, "--version"]);
    if (v && /^Python \d/.test(v)) return { command: [cmd, ...pre].join(" "), version: v };
  }
  return null;
};

const codexHome = () => process.env.CODEX_HOME || path.join(os.homedir(), ".codex");

/** Is the project (or an ancestor) trusted in ~/.codex/config.toml? */
export const codexTrust = (projectDir) => {
  const file = path.join(codexHome(), "config.toml");
  if (!exists(file)) return { known: false };
  let cfg;
  try {
    cfg = tomlParse(readText(file));
  } catch {
    return { known: false };
  }
  const projects = cfg.projects ?? {};
  const norm = (p) => path.resolve(p).replace(/[\\/]+$/, "").toLowerCase().replace(/\\/g, "/");
  let dir = path.resolve(projectDir);
  for (;;) {
    for (const [key, val] of Object.entries(projects)) {
      if (norm(key.replace(/^\\\\\?\\/, "")) === norm(dir)) return { known: true, trusted: val?.trust_level === "trusted", path: key };
    }
    const parent = path.dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
  return { known: true, trusted: false };
};

const SECRET_PATTERNS = [
  /-----BEGIN [A-Z ]*PRIVATE KEY-----/,
  /\bAKIA[0-9A-Z]{16}\b/,
  /\b(ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{20,}|xox[bp]-[A-Za-z0-9-]{10,})/,
  /\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}/,
  /:\/\/[^\s/:@]+:[^\s/@]+@/,
  /\b(password|passwd|secret|api[_-]?key|token)\s*[:=]\s*["']?[A-Za-z0-9_\-+/=]{8,}/i,
];

const CORE = { "MEMORY.md": "index", "constitution.md": "constitution", "project.md": "project", "system.md": "system", "tech.md": "tech", "active.md": "active", "changelog.md": "changelog", "user.md": "user" };
const TOPIC_TYPES = new Set(["user", "feedback", "project", "reference"]);
const DATE = /^\d{4}-\d{2}-\d{2}/;

/** Memory checks (§9.9). Returns issues. */
export const checkMemory = (projectDir, lang) => {
  const issues = [];
  const memDir = path.join(projectDir, ".redevkit", "memory");
  const add = (level, file, message) => issues.push({ level, file: `.redevkit/memory/${file}`, message });
  if (!exists(memDir)) {
    issues.push({ level: "info", file: ".redevkit/memory", message: "not initialized yet (run redevkit-new)" });
    return issues;
  }
  for (const f of Object.keys(CORE)) if (!exists(path.join(memDir, f))) add("error", f, "missing core memory file");
  for (const rel of listFiles(memDir)) {
    if (!rel.endsWith(".md")) continue;
    const text = readText(path.join(memDir, ...rel.split("/")));
    for (const re of SECRET_PATTERNS) if (re.test(text)) add("error", rel, `possible secret (${re.source.slice(0, 24)}…)`);
    if (rel.startsWith("archive/")) continue;
    const { data, hasFrontmatter, errors } = parseFrontmatter(text);
    if (!hasFrontmatter) {
      add("error", rel, "missing frontmatter (type, created, updated)");
      continue;
    }
    for (const e of errors) add("error", rel, `frontmatter: ${e}`);
    for (const k of ["type", "created", "updated"]) if (data[k] === undefined || data[k] === null || data[k] === "") add("error", rel, `frontmatter missing "${k}"`);
    for (const k of ["created", "updated"]) if (data[k] && !DATE.test(String(data[k]))) add("error", rel, `"${k}" is not an ISO date`);
    if (data.created && data.updated && DATE.test(String(data.created)) && DATE.test(String(data.updated)) && String(data.updated) < String(data.created)) add("warn", rel, "updated is before created");
    const expected = CORE[rel];
    if (expected && data.type !== expected) add("error", rel, `type must be "${expected}"`);
    if (rel.startsWith("topics/") && !TOPIC_TYPES.has(String(data.type))) add("error", rel, "topic type must be user, feedback, project or reference");
  }
  const indexPath = path.join(memDir, "MEMORY.md");
  if (exists(indexPath)) {
    const raw = readText(indexPath);
    const lines = raw.split(/\r?\n/);
    if (lines.length > 200) add("error", "MEMORY.md", `index has ${lines.length} lines (max 200)`);
    // Only real entries ("- [type] … → target"), never the format example inside HTML comments.
    for (const line of raw.replace(/<!--[\s\S]*?-->/g, "").split(/\r?\n/)) {
      if (!/^\s*-\s*\[[a-z]+\]/.test(line)) continue;
      const m = /→\s*`?([^\s`]+\.md)`?\s*$/.exec(line);
      if (!m) continue;
      const target = m[1].split("/");
      // Targets are relative to .redevkit/memory/; project-root paths (.redevkit/…, specs/…) also count.
      if (!exists(path.join(memDir, ...target)) && !exists(path.join(projectDir, ...target))) add("error", "MEMORY.md", `index link does not resolve: ${m[1]}`);
    }
  }
  const systemPath = path.join(memDir, "system.md");
  if (exists(systemPath)) {
    const heading = lang === "en" ? /^##\s+Invariants\s*$/m : /^##\s+Invariantes\s*$/m;
    if (!heading.test(readText(systemPath))) add("error", "system.md", `missing "## ${lang === "en" ? "Invariants" : "Invariantes"}" section`);
  }
  const activePath = path.join(memDir, "active.md");
  if (exists(activePath)) {
    const m = /^\s*-\s*(?:Feature|Feature ativa|Funcionalidade)\s*:\s*`?(specs\/\d{3}-[^\s`]+)`?/im.exec(readText(activePath));
    if (m && !exists(path.join(projectDir, ...m[1].replace(/\/$/, "").split("/")))) add("error", "active.md", `active feature path does not exist: ${m[1]}`);
  }
  return issues;
};

/** Duplicate NNN in specs/ (D53, risk 6). */
export const duplicateFeatureNumbers = (projectDir) => {
  const dir = path.join(projectDir, "specs");
  if (!exists(dir)) return [];
  const seen = new Map();
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const m = /^(\d{3})-/.exec(e.name);
    if (!e.isDirectory() || !m) continue;
    seen.set(m[1], [...(seen.get(m[1]) ?? []), e.name]);
  }
  return [...seen.entries()].filter(([, v]) => v.length > 1).map(([n, v]) => ({ number: n, dirs: v }));
};

export const runDoctor = async (opts, { log = console.log, projectDir = process.cwd() } = {}) => {
  const issues = [];
  const add = (level, file, message) => issues.push({ level, file, message });
  const tools = {
    node: process.version,
    git: probe("git"),
    python: detectPython(),
    claude: probe("claude"),
    codex: probe("codex"),
  };
  if (!tools.git) add("warn", "tools", "git not found");
  if (!tools.python) add("warn", "tools", "Python not found (audits will be SKIPPED; project commands are used instead)");

  const { manifest, error } = loadManifest(projectDir);
  if (error) add("error", ".redevkit/manifest.json", error);
  if (!manifest && !error) add("error", ".redevkit/manifest.json", "REDEVKIT is not installed here (run redevkit init)");
  let budgets = {};
  if (manifest) {
    setLang(manifest.lang);
    const drift = managedDrift(projectDir, manifest);
    for (const f of drift.missing) add("warn", f, "managed file missing (run redevkit update)");
    for (const f of drift.modified) add("info", f, "managed file modified locally (kept by update)");

    // Installed files per target: frontmatter, placeholders, links, catalog budget.
    for (const target of manifest.targets) {
      const files = new Map();
      for (const rel of Object.keys(manifest.files)) {
        const inTarget = target === "claude" ? /^\.claude\//.test(rel) : /^(\.agents|\.codex)\//.test(rel);
        if (!inTarget && !rel.startsWith(".redevkit/")) continue;
        const abs = resolveInside(projectDir, rel);
        if (exists(abs) && /\.(md|toml|yaml|json)$/.test(rel)) files.set(rel, readText(abs));
        else if (exists(abs)) files.set(rel, "");
      }
      const r = validateRendered(files, target);
      for (const i of r.issues) if (!/broken link/.test(i.message) || files.has(i.file)) issues.push(i);
      budgets[target] = measureCatalog(files, target);
    }

    // AGENTS.md
    const agentsAbs = path.join(projectDir, "AGENTS.md");
    if (!exists(agentsAbs)) add("error", "AGENTS.md", "missing");
    else {
      const text = readText(agentsAbs);
      const size = Buffer.byteLength(text, "utf8");
      if (size > AGENTS_MAX) add("error", "AGENTS.md", `${size} bytes: above the 32 KiB Codex default, it will be truncated`);
      try {
        if (!findBlock(text)) add("error", "AGENTS.md", "REDEVKIT block missing (run redevkit update)");
        else for (const i of validateAgentsBlock(blockInner(text)).issues) issues.push(i);
      } catch (err) {
        add("error", "AGENTS.md", err.message);
      }
    }
    if (manifest.targets.includes("claude")) {
      const claudeAbs = path.join(projectDir, "CLAUDE.md");
      if (!exists(claudeAbs)) add("error", "CLAUDE.md", "missing pointer to AGENTS.md");
      else if (!/^@AGENTS\.md\s*$/m.test(readText(claudeAbs))) add("error", "CLAUDE.md", "does not import @AGENTS.md");
      else if (readText(claudeAbs).split(/\r?\n/).filter((l) => l.trim()).length > 2) add("warn", "CLAUDE.md", "has content besides the pointer; move it to AGENTS.md");
    }

    // Managed config entries (D51).
    const entries = loadRuntimeEntries();
    if (manifest.targets.includes("claude")) {
      const abs = path.join(projectDir, ...CONFIG_FILES.claude.split("/"));
      if (!exists(abs)) add("warn", CONFIG_FILES.claude, "missing (managed permissions.allow entries absent)");
      else {
        try {
          const allow = JSON.parse(readText(abs))?.permissions?.allow ?? [];
          const missing = entries.claudeAllow.filter((e) => !allow.includes(e));
          if (missing.length) add("info", CONFIG_FILES.claude, `${missing.length} managed allow entr(ies) absent (removed by you or never added)`);
        } catch (err) {
          add("error", CONFIG_FILES.claude, `invalid JSON: ${err.message}`);
        }
      }
    }
    if (manifest.targets.includes("codex")) {
      const abs = path.join(projectDir, ...CONFIG_FILES.codex.split("/"));
      const present = codexEntriesPresent(exists(abs) ? readText(abs) : null, entries.codexEntries);
      for (const e of present) if (!e.present) add(e.invalid ? "error" : "warn", CONFIG_FILES.codex, `${e.table}.${e.key} ${e.invalid ? "file is invalid TOML" : "not set"}`);
      const trust = codexTrust(projectDir);
      if (!trust.known) add("info", "codex", "could not read ~/.codex/config.toml to check project trust");
      else if (!trust.trusted) add("warn", "codex", "project is not trusted in Codex: .codex/agents and .codex/config.toml are ignored (personas run inline)");
    }

    for (const i of checkMemory(projectDir, manifest.lang)) issues.push(i);
  }
  for (const d of duplicateFeatureNumbers(projectDir)) add("error", "specs/", `duplicate feature number ${d.number}: ${d.dirs.join(", ")} (renumber one)`);

  const errors = issues.filter((i) => i.level === "error");
  const report = { ok: errors.length === 0, tools, budgets, issues };
  if (opts.json) log(JSON.stringify(report, null, 2));
  else {
    const pt = getLang() === "pt-BR";
    log(`node ${tools.node} · git ${tools.git ? "ok" : "-"} · python ${tools.python ? tools.python.command : "-"} · claude ${tools.claude ? "ok" : "-"} · codex ${tools.codex ? "ok" : "-"}`);
    for (const [t, b] of Object.entries(budgets)) log(`${pt ? "catálogo" : "catalog"} ${t}: ${b.count} skills, ${b.total}/${b.limit} ${pt ? "caracteres" : "chars"}`);
    for (const i of issues) log(`${i.level.toUpperCase().padEnd(5)} ${i.file}: ${i.message}`);
    log(errors.length ? `${errors.length} ${pt ? "erro(s)" : "error(s)"}` : pt ? "Nenhum erro." : "No errors.");
  }
  return report;
};
