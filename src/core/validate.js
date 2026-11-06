// Kit validation (source and rendered trees). Used by `redevkit doctor`, `validate-kit` and tests.
// Reimplements in JS what AG Kit's validate_kit.py did (P3: encoding errors reported, links that
// leave the directory checked, no hard-coded exceptions beyond the documented legacy-path ones).
import path from "node:path";
import { parse as tomlParse } from "smol-toml";
import { measureCatalog } from "./catalog-budget.js";
import { asList, parseFrontmatter } from "./frontmatter.js";
import { renderAgentsBlock, renderAll, TARGET_IDS } from "./render.js";

export const NAMES = {
  command: ["redevkit-new", "redevkit-brainstorm", "redevkit-plan", "redevkit-create", "redevkit-enhance", "redevkit-test", "redevkit-debug", "redevkit-verify", "redevkit-preview", "redevkit-deploy", "redevkit-status"],
  memory: ["redevkit-memanager"],
  phase: [
    "redevkit-constitution", "redevkit-specify", "redevkit-clarify", "redevkit-tasks", "redevkit-analyze", "redevkit-checklist", "redevkit-implement", "redevkit-converge",
    "redevkit-orchestrate", "redevkit-route", "redevkit-bug-assess", "redevkit-bug-fix", "redevkit-bug-test",
    "redevkit-assess-intake", "redevkit-assess-research", "redevkit-assess-define", "redevkit-assess-shape", "redevkit-assess-decide",
  ],
  persona: [
    "backend-specialist", "code-archaeologist", "database-architect", "debugger", "devops-engineer", "documentation-writer", "explorer-agent", "frontend-specialist",
    "game-developer", "mobile-developer", "orchestrator", "penetration-tester", "performance-optimizer", "product-owner", "project-planner", "qa-automation-engineer",
    "security-auditor", "seo-specialist", "test-engineer",
  ],
  knowledge: [
    "api-patterns", "app-builder", "architecture", "bash-linux", "batch-operations", "clean-code", "code-review-checklist", "code-review-graph", "context-compression",
    "database-design", "deployment-procedures", "design-spec", "documentation-templates", "frontend-architecture", "frontend-design", "game-development", "geo-fundamentals",
    "i18n-localization", "lint-and-validate", "mcp-builder", "mobile-design", "nextjs-react-expert", "nodejs-best-practices", "performance-profiling", "powershell-windows",
    "python-patterns", "red-team-tactics", "rust-pro", "seo-fundamentals", "server-management", "simplify-code", "skillify", "systematic-debugging", "tailwind-patterns",
    "tdd-workflow", "testing-patterns", "vulnerability-scanner", "web-design-guidelines", "webapp-testing",
  ],
};

export const MAX_DESCRIPTION = 160;
export const AGENTS_BLOCK_MAX_LINES = 150;
export const AGENTS_BLOCK_MAX_BYTES = 8 * 1024;

export const FORBIDDEN = [
  { id: "antigravity", re: /antigravity/i },
  { id: "gemini", re: /gemini/i },
  { id: "run_command", re: /run_command/ },
  { id: "ViewCodeItem", re: /ViewCodeItem/ },
  { id: "FindByName", re: /FindByName/ },
  { id: ".specify/", re: /\.specify\//, legacyOk: true },
  { id: "bare /memory/", re: /(?<!\.redevkit)\/memory\//, legacyOk: true },
  { id: "CODEBASE.md", re: /CODEBASE\.md/ },
];

/** Files allowed to mention legacy memory paths (they detect and import them). */
export const LEGACY_OK = [/(^|\/)redevkit-new\/SKILL\.md$/, /(^|\/)redevkit-memanager\/references\/legacy-import\.md$/];

// Kit placeholders start with an uppercase name or #/ (JSX `style={{ a: 1 }}` is not one).
const LEFTOVER = /\{\{\s*[A-Z#/][^}\n]*\}\}/g;
const LINK = /!?\[[^\]\n]*\]\(([^)\s]+)(?:\s+"[^"]*")?\)/g;

const stripCode = (text) => text.replace(/```[\s\S]*?```/g, "").replace(/`[^`\n]*`/g, "");

/** Relative link targets in a Markdown text (outside code). */
export const relativeLinks = (text) => {
  const out = [];
  for (const m of stripCode(text).matchAll(LINK)) {
    const target = m[1];
    if (/^([a-z][a-z0-9+.-]*:|#|\/)/i.test(target) || target.includes("{{")) continue;
    out.push(decodeURIComponent(target.split("#")[0]));
  }
  return out.filter(Boolean);
};

const issue = (level, file, message) => ({ level, file, message });

const checkText = (rel, text, issues) => {
  if (text.includes("�")) issues.push(issue("error", rel, "invalid UTF-8 (replacement character found)"));
  const legacy = LEGACY_OK.some((re) => re.test(rel));
  for (const f of FORBIDDEN) {
    if (f.legacyOk && legacy) continue;
    const m = f.re.exec(text);
    if (m) {
      const line = text.slice(0, m.index).split("\n").length;
      issues.push(issue("error", rel, `forbidden term "${f.id}" at line ${line}`));
    }
  }
};

/** Validate the kit source (names, frontmatter, placeholders, ARGS, persona skills). */
export const validateSource = (kit) => {
  const issues = [];
  const skillNames = new Set(kit.skills.map((s) => s.dir));
  const personaNames = new Set(kit.personas.map((p) => p.file.replace(/\.md$/, "")));
  const commandNames = new Set(kit.skills.filter((s) => s.kind === "command" || s.kind === "memory").map((s) => s.dir));

  for (const kind of ["command", "memory", "phase", "knowledge"]) {
    const have = new Set(kit.skills.filter((s) => s.kind === kind).map((s) => s.dir));
    for (const n of NAMES[kind]) if (!have.has(n)) issues.push(issue("error", `kit/${kind}`, `missing ${kind} skill "${n}"`));
    for (const n of have) if (!NAMES[kind].includes(n)) issues.push(issue("error", `kit/${kind}`, `unexpected ${kind} skill "${n}"`));
  }
  for (const n of NAMES.persona) if (!personaNames.has(n)) issues.push(issue("error", "kit/personas", `missing persona "${n}"`));
  for (const n of personaNames) if (!NAMES.persona.includes(n)) issues.push(issue("error", "kit/personas", `unexpected persona "${n}"`));

  const checkPlaceholders = (rel, text) => {
    for (const m of text.matchAll(/\{\{\s*([A-Z#/][^}\n]*?)\s*\}\}/g)) {
      const inner = m[1];
      if (/^[#/](claude|codex)$/.test(inner)) continue;
      const pm = /^([A-Z]+)(?::([a-z0-9-]+))?$/.exec(inner);
      if (!pm) {
        issues.push(issue("error", rel, `unknown placeholder {{${inner}}}`));
        continue;
      }
      const [, name, arg] = pm;
      const ok =
        (["ASK", "ARGS", "LANG", "VERSION"].includes(name) && !arg) ||
        (name === "CMD" && commandNames.has(arg)) ||
        ((name === "SKILL" || name === "SKILLDIR") && skillNames.has(arg)) ||
        ((name === "PERSONA" || name === "DELEGATE") && personaNames.has(arg));
      if (!ok) issues.push(issue("error", rel, `invalid placeholder {{${inner}}}`));
    }
    const opens = (text.match(/\{\{#(claude|codex)\}\}/g) ?? []).length;
    const closes = (text.match(/\{\{\/(claude|codex)\}\}/g) ?? []).length;
    if (opens !== closes) issues.push(issue("error", rel, "unbalanced {{#target}} blocks"));
  };

  for (const s of kit.skills) {
    const rel = `kit/${s.source.replace(/\\/g, "/")}`;
    for (const e of s.errors) issues.push(issue("error", rel, `frontmatter: ${e}`));
    if (s.data.name !== s.dir) issues.push(issue("error", rel, `name "${s.data.name}" must equal directory "${s.dir}"`));
    const d = String(s.data.description ?? "");
    if (!d) issues.push(issue("error", rel, "missing description"));
    if (d.length > MAX_DESCRIPTION) issues.push(issue("error", rel, `description has ${d.length} chars (max ${MAX_DESCRIPTION})`));
    if (/\n/.test(d)) issues.push(issue("error", rel, "description must be one line"));
    if (s.data.context === "fork") issues.push(issue("error", rel, "context: fork is not allowed"));
    if (s.kind === "command" && !s.data["short-description"]) issues.push(issue("warn", rel, "command without short-description"));
    const sd = s.data["short-description"];
    if (sd && String(sd).length > 60) issues.push(issue("warn", rel, "short-description over 60 chars"));
    const args = (s.body.match(/\{\{\s*ARGS\s*\}\}/g) ?? []).length + s.files.reduce((n, f) => n + (f.text.match(/\{\{\s*ARGS\s*\}\}/g) ?? []).length, 0);
    if ((s.kind === "command" || s.kind === "memory") && args !== 1) issues.push(issue("error", rel, `{{ARGS}} must appear exactly once (found ${args}) (T6)`));
    if (s.kind !== "command" && s.kind !== "memory" && args > 0) issues.push(issue("error", rel, "{{ARGS}} is only for commands and redevkit-memanager"));
    if (s.data.invocation && s.data.invocation !== "user-only") issues.push(issue("error", rel, `invalid invocation "${s.data.invocation}"`));
    checkPlaceholders(rel, s.body);
    for (const f of s.files) {
      const frel = `kit/${path.posix.join(path.posix.dirname(s.source.replace(/\\/g, "/")), f.rel)}`;
      if (!/^references\/[^/]+\.md$/.test(f.rel)) issues.push(issue("error", frel, "skill directories may only hold SKILL.md and references/*.md"));
      checkPlaceholders(frel, f.text);
    }
  }
  for (const p of kit.personas) {
    const rel = `kit/${p.source}`;
    for (const e of p.errors) issues.push(issue("error", rel, `frontmatter: ${e}`));
    const name = p.file.replace(/\.md$/, "");
    if (p.data.name !== name) issues.push(issue("error", rel, `name must equal file name "${name}"`));
    const d = String(p.data.description ?? "");
    if (!d) issues.push(issue("error", rel, "missing description"));
    if (d.length > MAX_DESCRIPTION) issues.push(issue("error", rel, `description has ${d.length} chars (max ${MAX_DESCRIPTION})`));
    const skills = asList(p.data.skills);
    if (skills.length > 3) issues.push(issue("error", rel, `persona preloads ${skills.length} skills (max 3)`));
    for (const sk of skills) if (!skillNames.has(sk)) issues.push(issue("error", rel, `unknown skill "${sk}" in skills:`));
    for (const sk of skills) {
      const target = kit.skills.find((s) => s.dir === sk);
      if (target?.data.invocation === "user-only") issues.push(issue("error", rel, `skill "${sk}" cannot be preloaded (user-only)`));
    }
    if (/\{\{\s*ARGS\s*\}\}/.test(p.body)) issues.push(issue("error", rel, "{{ARGS}} is not allowed in personas"));
    checkPlaceholders(rel, p.body);
  }
  return issues;
};

const CLAUDE_SKILL_KEYS = new Set(["name", "description", "argument-hint", "user-invocable", "disable-model-invocation", "paths"]);
const CODEX_SKILL_KEYS = new Set(["name", "description", "metadata"]);
const CLAUDE_AGENT_KEYS = new Set(["name", "description", "tools", "model", "skills"]);

/** Validate one rendered target (Map<rel, content>). */
export const validateRendered = (files, targetId) => {
  const issues = [];
  const keys = new Set(files.keys());
  for (const [rel, raw] of files) {
    if (!/\.(md|toml|yaml|json)$/.test(rel) && rel !== ".redevkit/.gitignore") continue;
    const text = String(raw);
    const left = text.match(LEFTOVER);
    if (left) issues.push(issue("error", rel, `leftover placeholder ${left[0]}`));
    checkText(rel, text, issues);
    if (rel.endsWith(".md")) {
      for (const link of relativeLinks(text)) {
        const resolved = path.posix.normalize(path.posix.join(path.posix.dirname(rel), link));
        if (resolved.startsWith("..")) issues.push(issue("error", rel, `link leaves the project: ${link}`));
        else if (!keys.has(resolved) && !keys.has(resolved.replace(/\/$/, "") + "/SKILL.md")) issues.push(issue("error", rel, `broken link: ${link}`));
      }
    }
    if (/^\.(claude|agents)\/skills\/[^/]+\/.+\/SKILL\.md$/.test(rel)) issues.push(issue("error", rel, "nested SKILL.md (RC3): sub-skills must be references/*.md"));
    if (/\/SKILL\.md$/.test(rel)) {
      const { data, errors, hasFrontmatter } = parseFrontmatter(text);
      if (!hasFrontmatter) issues.push(issue("error", rel, "missing frontmatter"));
      for (const e of errors) issues.push(issue("error", rel, `frontmatter: ${e}`));
      const allowed = targetId === "claude" ? CLAUDE_SKILL_KEYS : CODEX_SKILL_KEYS;
      for (const k of Object.keys(data)) if (!allowed.has(k)) issues.push(issue("error", rel, `frontmatter key "${k}" not allowed for ${targetId}`));
      if (!data.name || !data.description) issues.push(issue("error", rel, "name and description are required"));
      if (String(data.description ?? "").length > MAX_DESCRIPTION) issues.push(issue("error", rel, "description over 160 chars"));
    }
    if (targetId === "claude" && /^\.claude\/agents\/[^/]+\.md$/.test(rel)) {
      const { data } = parseFrontmatter(text);
      for (const k of Object.keys(data)) if (!CLAUDE_AGENT_KEYS.has(k)) issues.push(issue("error", rel, `agent key "${k}" not allowed`));
      if (asList(data.skills).length > 3) issues.push(issue("error", rel, "more than 3 preloaded skills"));
    }
    if (targetId === "codex" && /^\.codex\/agents\/[^/]+\.toml$/.test(rel)) {
      try {
        const parsed = tomlParse(text);
        for (const k of ["name", "description", "developer_instructions"]) if (typeof parsed[k] !== "string" || !parsed[k]) issues.push(issue("error", rel, `missing ${k}`));
      } catch (err) {
        issues.push(issue("error", rel, `invalid TOML: ${err.message}`));
      }
    }
  }
  const budget = measureCatalog(files, targetId);
  if (!budget.withinLimit) issues.push(issue("error", `catalog:${targetId}`, `catalog descriptions total ${budget.total} chars (limit ${budget.limit})`));
  else if (!budget.withinSoftLimit) issues.push(issue("warn", `catalog:${targetId}`, `catalog descriptions total ${budget.total} chars: above the ${budget.softLimit}-char fallback listing budget, so on small-context models the least-used descriptions may be dropped (names stay listed)`));
  return { issues, budget };
};

export const validateAgentsBlock = (block) => {
  const issues = [];
  const lines = block.split("\n").length;
  const bytes = Buffer.byteLength(block, "utf8");
  if (lines > AGENTS_BLOCK_MAX_LINES) issues.push(issue("error", "AGENTS.md block", `${lines} lines (max ${AGENTS_BLOCK_MAX_LINES})`));
  if (bytes > AGENTS_BLOCK_MAX_BYTES) issues.push(issue("error", "AGENTS.md block", `${bytes} bytes (max ${AGENTS_BLOCK_MAX_BYTES})`));
  const left = block.match(LEFTOVER);
  if (left) issues.push(issue("error", "AGENTS.md block", `leftover placeholder ${left[0]}`));
  checkText("AGENTS.md block", block, issues);
  return { issues, lines, bytes };
};

/** Full kit validation: source + both targets in both languages + audits text. */
export const validateKit = ({ kit, kitRoot, langs = ["pt-BR", "en"] }) => {
  const issues = [...validateSource(kit)];
  const budgets = {};
  const blocks = {};
  for (const lang of langs) {
    const { perTarget, files } = renderAll({ targets: TARGET_IDS, lang, kitRoot, kit });
    for (const t of TARGET_IDS) {
      const merged = new Map([...files].filter(([rel]) => rel.startsWith(".redevkit/")));
      for (const [k, v] of perTarget[t]) merged.set(k, v);
      const r = validateRendered(merged, t);
      for (const i of r.issues) if (!issues.some((x) => x.file === i.file && x.message === i.message)) issues.push(i);
      budgets[t] = r.budget;
    }
    for (const [rel, content] of files) {
      if (rel.startsWith(".redevkit/audits/") && rel.endsWith(".py")) checkText(rel, String(content), issues);
      if (rel.startsWith(".redevkit/templates/") && /\{\{\s*[A-Z#/]/.test(String(content))) issues.push(issue("error", rel, "templates must not contain {{...}}"));
    }
    for (const targets of [["claude"], ["codex"], ["claude", "codex"]]) {
      const block = renderAgentsBlock({ targets, lang, kitRoot });
      const r = validateAgentsBlock(block);
      blocks[`${targets.join("+")}`] = { lines: r.lines, bytes: r.bytes };
      for (const i of r.issues) if (!issues.some((x) => x.file === i.file && x.message === i.message)) issues.push(i);
    }
  }
  return { issues, budgets, blocks };
};
