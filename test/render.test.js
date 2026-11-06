import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { parse as tomlParse } from "smol-toml";
import { parseFrontmatter } from "../src/core/frontmatter.js";
import { loadKit, packageVersion, renderAgentsBlock, renderAll, renderTarget, PACKAGE_ROOT } from "../src/core/render.js";
import { validateRendered } from "../src/core/validate.js";
import { FIXTURE_KIT, ROOT } from "./helpers.js";

const SNAP_DIR = path.join(ROOT, "test", "__snapshots__");
const snapshot = (name, value) => {
  const file = path.join(SNAP_DIR, `${name}.snap`);
  const text = typeof value === "string" ? value : JSON.stringify(value, null, 2);
  if (process.env.UPDATE_SNAPSHOTS === "1" || !fs.existsSync(file)) {
    fs.mkdirSync(SNAP_DIR, { recursive: true });
    fs.writeFileSync(file, text);
  }
  assert.equal(text, fs.readFileSync(file, "utf8"), `snapshot ${name} changed (UPDATE_SNAPSHOTS=1 to accept)`);
};

const fixture = () => loadKit(FIXTURE_KIT);
const ctx = { lang: "en", version: "1.2.3" };
const dump = (map) => [...map.entries()].sort(([a], [b]) => (a < b ? -1 : 1)).map(([k, v]) => `=== ${k}\n${String(v)}`).join("\n");

test("render snapshots are stable per target", () => {
  const kit = fixture();
  snapshot("fixture-claude", dump(renderTarget(kit, "claude", ctx)));
  snapshot("fixture-codex", dump(renderTarget(kit, "codex", ctx)));
});

test("claude rendering: frontmatter allowlist, hidden phases, deploy, personas (D17, D24, D28)", () => {
  const files = renderTarget(fixture(), "claude", ctx);
  const cmd = parseFrontmatter(files.get(".claude/skills/redevkit-demo/SKILL.md"));
  assert.deepEqual(Object.keys(cmd.data), ["name", "description", "argument-hint"]);
  assert.match(cmd.body, /\*\*Input:\*\* \$ARGUMENTS/);
  assert.match(cmd.body, /Claude only\./);
  assert.doesNotMatch(cmd.body, /Codex only/);
  assert.match(cmd.body, /`\/redevkit-deploy` in en v1\.2\.3/);
  assert.match(cmd.body, /subagent_type: "helper"/);
  assert.match(cmd.body, /AskUserQuestion/);
  assert.equal(parseFrontmatter(files.get(".claude/skills/redevkit-step/SKILL.md")).data["user-invocable"], false);
  assert.equal(parseFrontmatter(files.get(".claude/skills/redevkit-deploy/SKILL.md")).data["disable-model-invocation"], true);
  assert.deepEqual(parseFrontmatter(files.get(".claude/skills/know/SKILL.md")).data.paths, ["**/*.ts", "**/*.tsx"]);
  const agent = parseFrontmatter(files.get(".claude/agents/helper.md"));
  assert.equal(agent.data.model, "inherit");
  assert.deepEqual(agent.data.skills, ["know"]);
  assert.match(agent.body, /`?\/redevkit-demo/);
  assert.ok(files.has(".claude/skills/helper/SKILL.md"), "thin persona skill");
  assert.equal(validateRendered(files, "claude").issues.filter((i) => i.level === "error").length, 0);
});

test("codex rendering: metadata, [internal], openai.yaml, TOML personas (D18, D24, D28)", () => {
  const files = renderTarget(fixture(), "codex", ctx);
  const cmd = parseFrontmatter(files.get(".agents/skills/redevkit-demo/SKILL.md"));
  assert.deepEqual(Object.keys(cmd.data), ["name", "description", "metadata"]);
  assert.equal(cmd.data.metadata["short-description"], "Demo");
  assert.match(cmd.body, /the request the user wrote alongside this skill invocation/);
  assert.match(cmd.body, /Codex only\./);
  assert.doesNotMatch(cmd.body, /Claude only/);
  assert.match(cmd.body, /`\$redevkit-deploy`/);
  assert.match(cmd.body, /spawn_agent/);
  assert.match(cmd.body, /request_user_input/);
  assert.match(parseFrontmatter(files.get(".agents/skills/redevkit-step/SKILL.md")).data.description, /^\[internal\] /);
  assert.equal(files.get(".agents/skills/redevkit-deploy/agents/openai.yaml"), "policy:\n  allow_implicit_invocation: false\n");
  const toml = tomlParse(files.get(".codex/agents/helper.toml"));
  assert.match(toml.developer_instructions, /''' triple quotes/);
  assert.ok(![...files.keys()].some((k) => k.startsWith(".agents/skills/helper")), "no persona skill in Codex");
  assert.equal(validateRendered(files, "codex").issues.filter((i) => i.level === "error").length, 0);
});

test("common files: only the chosen language, audits, .gitignore (D52)", () => {
  const { files } = renderAll({ targets: ["claude"], lang: "pt-BR", kitRoot: FIXTURE_KIT, kit: fixture(), version: "1.2.3" });
  assert.match(files.get(".redevkit/templates/spec.md"), /Especificação/);
  assert.ok(files.has(".redevkit/audits/demo_audit.py"));
  assert.ok(files.has(".redevkit/.gitignore"));
  assert.ok(![...files.keys()].some((k) => k.startsWith(".agents/")));
});

test("AGENTS.md block resolves includes, conditionals and multi-target paths", () => {
  const both = renderAgentsBlock({ targets: ["claude", "codex"], lang: "en", kitRoot: FIXTURE_KIT, version: "1.2.3" });
  assert.match(both, /Version 1\.2\.3 lang en/);
  assert.match(both, /@\.redevkit\/memory\/MEMORY\.md/);
  assert.match(both, /`\.claude\/skills\/redevkit-memanager\/SKILL\.md` or `\.agents\/skills\/redevkit-memanager\/SKILL\.md`/);
  const codexOnly = renderAgentsBlock({ targets: ["codex"], lang: "en", kitRoot: FIXTURE_KIT, version: "1.2.3" });
  assert.doesNotMatch(codexOnly, /@\.redevkit/);
});

test("validator flags leftovers, forbidden terms and broken links", () => {
  const files = new Map([
    [".claude/skills/a/SKILL.md", "---\nname: a\ndescription: x\nversion: 1\n---\n{{CMD:nope}} antigravity see [x](references/missing.md) and /memory/x\n"],
  ]);
  const msgs = validateRendered(files, "claude").issues.map((i) => i.message).join("\n");
  assert.match(msgs, /leftover placeholder/);
  assert.match(msgs, /forbidden term "antigravity"/);
  assert.match(msgs, /broken link/);
  assert.match(msgs, /bare \/memory\//);
  assert.match(msgs, /"version" not allowed/);
});

test("version comes from package.json only (M2)", () => {
  const pkg = JSON.parse(fs.readFileSync(path.join(PACKAGE_ROOT, "package.json"), "utf8"));
  assert.equal(packageVersion(), pkg.version);
  const block = renderAgentsBlock({ targets: ["claude"], lang: "en" });
  assert.match(block, new RegExp(`REDEVKIT ${pkg.version.replace(/\./g, "\\.")}`));
});
