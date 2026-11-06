// Renders the single-source kit (kit/) into per-target project files (§4.3).
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { parseFrontmatter } from "./frontmatter.js";
import { listFiles, readText } from "./fsutil.js";
import * as claude from "./targets/claude.js";
import * as codex from "./targets/codex.js";

export const PACKAGE_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
export const KIT_ROOT = path.join(PACKAGE_ROOT, "kit");
export const TARGETS = { claude, codex };
export const TARGET_IDS = ["claude", "codex"];
export const LANGS = ["pt-BR", "en"];

export const packageVersion = () => JSON.parse(fs.readFileSync(path.join(PACKAGE_ROOT, "package.json"), "utf8")).version;

const SKILL_GROUPS = [
  ["commands", "command"],
  ["phases", "phase"],
  ["memory", "memory"],
  ["skills", "knowledge"],
];

/** Load every source unit from kit/. */
export const loadKit = (kitRoot = KIT_ROOT) => {
  const skills = [];
  for (const [dir, kind] of SKILL_GROUPS) {
    const base = path.join(kitRoot, dir);
    if (!fs.existsSync(base)) continue;
    for (const entry of fs.readdirSync(base, { withFileTypes: true })) {
      if (!entry.isDirectory()) continue;
      const skillDir = path.join(base, entry.name);
      const skillFile = path.join(skillDir, "SKILL.md");
      if (!fs.existsSync(skillFile)) continue;
      const { data, body, errors } = parseFrontmatter(readText(skillFile));
      const files = listFiles(skillDir)
        .filter((rel) => rel !== "SKILL.md")
        .map((rel) => ({ rel, text: readText(path.join(skillDir, rel)) }));
      skills.push({ kind, dir: entry.name, source: path.join(dir, entry.name, "SKILL.md"), data, body, errors, files });
    }
  }
  const personas = [];
  const personaDir = path.join(kitRoot, "personas");
  if (fs.existsSync(personaDir)) {
    for (const file of fs.readdirSync(personaDir).filter((f) => f.endsWith(".md")).sort()) {
      const { data, body, errors } = parseFrontmatter(readText(path.join(personaDir, file)));
      personas.push({ kind: "persona", file, source: `personas/${file}`, data, body, errors });
    }
  }
  return { kitRoot, skills, personas };
};

const PLACEHOLDER = /\{\{\s*([A-Z]+)(?::([a-z0-9-]+))?\s*\}\}/g;

/** Keep or drop {{#claude}}…{{/claude}} and {{#codex}}…{{/codex}} blocks. */
export const applyConditionals = (text, keep) => {
  const lineBlock = /^[ \t]*\{\{#(claude|codex)\}\}[ \t]*\n([\s\S]*?)^[ \t]*\{\{\/\1\}\}[ \t]*(\n|$)/gm;
  let out = text.replace(lineBlock, (_, t, inner) => (keep.has(t) ? inner : ""));
  const inline = /\{\{#(claude|codex)\}\}([\s\S]*?)\{\{\/\1\}\}/g;
  out = out.replace(inline, (_, t, inner) => (keep.has(t) ? inner : ""));
  return out;
};

/**
 * Replace placeholders for one target. Unknown placeholders are left in place so the
 * validator reports them (§4.3: "o validador falha quando sobra algum {{...}}").
 */
export const applyPlaceholders = (text, target, ctx) => {
  const keep = new Set([target.id]);
  const conditioned = applyConditionals(text, keep);
  return conditioned.replace(PLACEHOLDER, (match, name, arg) => {
    if (name === "LANG") return ctx.lang;
    if (name === "VERSION") return ctx.version;
    const fn = target.placeholders[name];
    if (!fn) return match;
    if (["CMD", "SKILL", "SKILLDIR", "PERSONA", "DELEGATE"].includes(name) && !arg) return match;
    return fn(arg);
  });
};

/** Render only LANG/VERSION (target-neutral files). */
export const applyCommon = (text, ctx) =>
  text.replace(/\{\{\s*LANG\s*\}\}/g, ctx.lang).replace(/\{\{\s*VERSION\s*\}\}/g, ctx.version);

/** Files for one target: Map<projectRelativePath, string>. */
export const renderTarget = (kit, targetId, ctx) => {
  const target = TARGETS[targetId];
  if (!target) throw new Error(`Unknown target: ${targetId}`);
  const out = new Map();
  for (const skill of kit.skills) {
    const data = { ...skill.data, name: skill.data.name ?? skill.dir };
    const fm = target.skillFrontmatter(skill.kind, data);
    const body = applyPlaceholders(skill.body, target, ctx);
    out.set(target.paths.skillFile(skill.dir), `${fm}\n${body.replace(/^\n*/, "\n")}`);
    for (const f of skill.files) {
      out.set(`${target.paths.skillDir(skill.dir)}/${f.rel}`, applyPlaceholders(f.text, target, ctx));
    }
    for (const [rel, content] of target.extraFiles(skill.kind, data)) out.set(rel, content);
  }
  for (const persona of kit.personas) {
    const name = persona.data.name ?? persona.file.replace(/\.md$/, "");
    const data = { ...persona.data, name };
    const body = applyPlaceholders(persona.body, target, ctx);
    out.set(target.paths.persona(name), target.personaFile(data, body));
    if (target.personaSkill) out.set(target.paths.skillFile(name), target.personaSkill(data));
  }
  return out;
};

/** Target-independent files: templates (chosen language only, D52), audits, .redevkit/.gitignore. */
export const renderCommon = (kitRoot, ctx) => {
  const out = new Map();
  const tplRoot = path.join(kitRoot, "templates", ctx.lang);
  for (const rel of listFiles(tplRoot)) {
    out.set(`.redevkit/templates/${rel}`, applyCommon(readText(path.join(tplRoot, rel)), ctx));
  }
  const auditRoot = path.join(kitRoot, "audits");
  for (const rel of listFiles(auditRoot)) {
    if (rel.endsWith(".pyc")) continue;
    out.set(`.redevkit/audits/${rel}`, fs.readFileSync(path.join(auditRoot, rel)));
  }
  out.set(".redevkit/.gitignore", "backups/\ntmp/\nconflicts/\n");
  return out;
};

/** Everything the CLI manages as files for a set of targets. */
export const renderAll = ({ targets, lang, version = packageVersion(), kitRoot = KIT_ROOT, kit = loadKit(kitRoot) }) => {
  const ctx = { lang, version };
  const files = new Map(renderCommon(kitRoot, ctx));
  const perTarget = {};
  for (const t of TARGET_IDS) {
    if (!targets.includes(t)) continue;
    perTarget[t] = renderTarget(kit, t, ctx);
    for (const [k, v] of perTarget[t]) files.set(k, v);
  }
  return { files, perTarget, kit, ctx };
};

/** The AGENTS.md managed block for the installed targets. */
export const renderAgentsBlock = ({ targets, lang, version = packageVersion(), kitRoot = KIT_ROOT }) => {
  const src = readText(path.join(kitRoot, "context", "AGENTS.block.md"));
  const withIncludes = src.replace(/<!--\s*include:\s*([^\s]+)\s*-->/g, (_, rel) => {
    const inc = path.resolve(kitRoot, "context", rel);
    if (!inc.startsWith(path.resolve(kitRoot))) throw new Error(`include escapes kit: ${rel}`);
    return readText(inc).trim();
  });
  const keep = new Set(targets);
  const ordered = TARGET_IDS.filter((t) => keep.has(t)).map((t) => TARGETS[t]);
  // Shared file: path-like placeholders list every installed target ("`a` or `b`" inside backticks).
  const multi = (name, arg) => ordered.map((t) => t.placeholders[name](arg)).join("` or `");
  const resolved = applyConditionals(withIncludes, keep).replace(/\{\{\s*(CMD|SKILL|SKILLDIR|PERSONA):([a-z0-9-]+)\s*\}\}/g, (_, n, a) => multi(n, a));
  return applyCommon(resolved, { lang, version }).trim() + "\n";
};

/** CLAUDE.md pointer content in the manifest language (§4.4). */
export const renderClaudePointer = ({ lang, kitRoot = KIT_ROOT }) => {
  const file = path.join(kitRoot, "context", `CLAUDE.${lang}.md`);
  return readText(file).replace(/\r\n?/g, "\n").trim() + "\n";
};

/** Managed runtime entries (D51). */
export const loadRuntimeEntries = (kitRoot = KIT_ROOT) => {
  const allow = JSON.parse(readText(path.join(kitRoot, "runtime", "claude-allow.json")));
  const tomlText = readText(path.join(kitRoot, "runtime", "codex-config.toml"));
  const codexEntries = [];
  let table = null;
  for (const raw of tomlText.replace(/\r\n?/g, "\n").split("\n")) {
    const line = raw.replace(/#.*$/, "").trim();
    if (!line) continue;
    const t = /^\[([A-Za-z0-9_.-]+)\]$/.exec(line);
    if (t) {
      table = t[1];
      continue;
    }
    const kv = /^([A-Za-z0-9_-]+)\s*=\s*(.+)$/.exec(line);
    if (kv && table) codexEntries.push({ table, key: kv[1], value: kv[2].trim() });
  }
  return { claudeAllow: allow.allow ?? allow, codexEntries };
};
