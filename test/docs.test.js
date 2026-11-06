// Documentation consistency (PLANO §13.4 rows D2–D8, §14 F9).
// - docs/metodo.md may only use spec-driven method terms that exist in kit/templates/.
// - Every relative Markdown link in README.md and docs/*.md resolves to an existing file.
// - Command names and CLI options cited in the docs exist in the kit and in the CLI.
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { buildProgram } from "../src/cli.js";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const read = (rel) => fs.readFileSync(path.join(ROOT, rel), "utf8");

const listFiles = (dir) => {
  const out = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const abs = path.join(dir, entry.name);
    if (entry.isDirectory()) out.push(...listFiles(abs));
    else if (entry.isFile()) out.push(abs);
  }
  return out;
};

const DOCS = ["README.md", ...fs.readdirSync(path.join(ROOT, "docs")).filter((f) => f.endsWith(".md")).map((f) => `docs/${f}`)];

// Terms the old Spec Kit method doc used without any support in its templates (D3, D4, D6).
const METHOD_TERMS = [
  "Phase -1",
  "Fase -1",
  "Article",
  "Artigo",
  "Simplicity Gate",
  "Integration-First",
  "implementation-details",
  "File Creation Order",
];

const templateText = listFiles(path.join(ROOT, "kit", "templates"))
  .filter((f) => f.endsWith(".md"))
  .map((f) => fs.readFileSync(f, "utf8"))
  .join("\n")
  .toLowerCase();

/** Remove fenced code blocks and inline code spans, keeping line count. */
const stripCode = (text) =>
  text
    .replace(/^(```|~~~)[^\n]*\n[\s\S]*?^\1[^\n]*$/gm, (m) => m.replace(/[^\n]/g, ""))
    .replace(/`[^`\n]*`/g, "");

test("docs/metodo.md uses only method terms that exist in kit/templates", () => {
  const metodo = read("docs/metodo.md").toLowerCase();
  for (const term of METHOD_TERMS) {
    const t = term.toLowerCase();
    if (metodo.includes(t)) {
      assert.ok(templateText.includes(t), `docs/metodo.md mentions "${term}", which no file under kit/templates/ contains`);
    }
  }
});

test("docs/metodo.md covers the gates, the TDD line and the task grammar", () => {
  const metodo = read("docs/metodo.md");
  for (const g of ["G1", "G2", "G3", "G4", "G5", "G6", "G7"]) assert.ok(metodo.includes(g), `gate ${g} missing`);
  for (const line of ["**TDD**: required", "**TDD**: waived"]) {
    assert.ok(metodo.includes(line), `"${line}" missing from docs/metodo.md`);
    assert.ok(templateText.includes(line.toLowerCase()), `"${line}" missing from kit/templates`);
  }
  assert.ok(metodo.includes("- [ ] T012 [P] [US1] descrição — caminho — @persona — VERIFY: critério"), "task line grammar missing");
});

test("every relative Markdown link in README.md and docs/*.md resolves", () => {
  const broken = [];
  for (const rel of DOCS) {
    const text = stripCode(read(rel));
    const targets = [
      ...[...text.matchAll(/!?\[[^\]]*\]\(\s*<?([^)\s>]+)>?(?:\s+"[^"]*")?\s*\)/g)].map((m) => m[1]),
      ...[...text.matchAll(/^\s{0,3}\[[^\]]+\]:\s*<?(\S+?)>?(?:\s|$)/gm)].map((m) => m[1]),
    ];
    for (const target of targets) {
      if (/^[a-z][a-z0-9+.-]*:/i.test(target) || target.startsWith("#")) continue; // URL, mailto, same-file anchor
      const file = decodeURIComponent(target.split("#")[0].split("?")[0]);
      const abs = path.resolve(ROOT, path.dirname(rel), file);
      if (!fs.existsSync(abs)) broken.push(`${rel} -> ${target}`);
    }
  }
  assert.deepEqual(broken, [], `broken links:\n${broken.join("\n")}`);
});

test("redevkit-* names cited in the docs exist in the kit", () => {
  const known = new Set(
    ["commands", "phases", "memory"].flatMap((d) =>
      fs
        .readdirSync(path.join(ROOT, "kit", d), { withFileTypes: true })
        .filter((e) => e.isDirectory())
        .map((e) => e.name),
    ),
  );
  const unknown = [];
  for (const rel of DOCS) {
    for (const m of read(rel).matchAll(/redevkit-[a-z][a-z-]*[a-z]/g)) {
      if (!known.has(m[0])) unknown.push(`${rel}: ${m[0]}`);
    }
  }
  assert.deepEqual(unknown, [], `unknown skill names:\n${unknown.join("\n")}`);
});

test("CLI commands and options in README.md exist in the CLI", () => {
  const program = buildProgram();
  const options = new Set();
  const commands = new Set();
  const walk = (cmd) => {
    for (const o of cmd.options) if (o.long) options.add(o.long);
    for (const sub of cmd.commands) {
      commands.add(sub.name());
      walk(sub);
    }
  };
  walk(program);
  // Command-skill flags come from the argument-hint of each command.
  for (const dir of fs.readdirSync(path.join(ROOT, "kit", "commands"))) {
    const skill = read(`kit/commands/${dir}/SKILL.md`);
    const hint = /^argument-hint:\s*(.*)$/m.exec(skill)?.[1] ?? "";
    for (const m of hint.matchAll(/--[a-z][a-z-]*/g)) options.add(m[0]);
  }
  const readme = read("README.md");
  const unknownOptions = [...new Set([...readme.matchAll(/(?<![\w-])--[a-z][a-z-]*/g)].map((m) => m[0]))].filter((o) => !options.has(o));
  assert.deepEqual(unknownOptions, [], `README.md cites options the CLI and the commands do not have: ${unknownOptions.join(", ")}`);
  const unknownCommands = [...readme.matchAll(/`redevkit ([a-z-]+)/g)].map((m) => m[1]).filter((c) => !commands.has(c));
  assert.deepEqual(unknownCommands, [], `README.md cites CLI commands that do not exist: ${unknownCommands.join(", ")}`);
});
