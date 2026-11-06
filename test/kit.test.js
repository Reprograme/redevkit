// The real kit shipped in the package: valid source, valid renders, budget, block size.
import assert from "node:assert/strict";
import test from "node:test";
import { KIT_ROOT, loadKit, renderAll } from "../src/core/render.js";
import { asList } from "../src/core/frontmatter.js";
import { NAMES, validateKit } from "../src/core/validate.js";
import { checkPack, packFiles } from "./pack-check.mjs";

const kit = loadKit(KIT_ROOT);

test("kit inventory matches the plan (11 commands, 1 memory, 18 phases, 39 knowledge, 19 personas)", () => {
  const count = (k) => kit.skills.filter((s) => s.kind === k).length;
  assert.equal(count("command"), 11);
  assert.equal(count("memory"), 1);
  assert.equal(count("phase"), 18);
  assert.equal(count("knowledge"), 39);
  assert.equal(kit.personas.length, 19);
  assert.equal(NAMES.persona.length, 19);
});

test("kit validates: no errors in source or in any rendered target/language", () => {
  const { issues, budgets, blocks } = validateKit({ kit, kitRoot: KIT_ROOT });
  const errors = issues.filter((i) => i.level === "error");
  assert.deepEqual(errors, []);
  assert.ok(budgets.claude.total <= budgets.claude.limit, `claude catalog ${budgets.claude.total}`);
  assert.ok(budgets.codex.total <= budgets.codex.limit, `codex catalog ${budgets.codex.total}`);
  for (const [k, b] of Object.entries(blocks)) assert.ok(b.bytes <= 8192 && b.lines <= 150, `AGENTS block ${k}`);
});

test("catalog entries per target: Claude 88, Codex 69", () => {
  const { perTarget } = renderAll({ targets: ["claude", "codex"], lang: "en", kit });
  const skills = (map, re) => [...map.keys()].filter((k) => re.test(k)).length;
  assert.equal(skills(perTarget.claude, /^\.claude\/skills\/[^/]+\/SKILL\.md$/), 88);
  assert.equal(skills(perTarget.codex, /^\.agents\/skills\/[^/]+\/SKILL\.md$/), 69);
  assert.equal(skills(perTarget.codex, /^\.codex\/agents\/[^/]+\.toml$/), 19);
});

test("no persona preloads more than 3 skills; deploy is user-only on both targets (D28)", () => {
  for (const p of kit.personas) assert.ok(asList(p.data.skills).length <= 3, p.file);
  const { perTarget } = renderAll({ targets: ["claude", "codex"], lang: "en", kit });
  assert.match(perTarget.claude.get(".claude/skills/redevkit-deploy/SKILL.md"), /disable-model-invocation: true/);
  assert.match(perTarget.codex.get(".agents/skills/redevkit-deploy/agents/openai.yaml"), /allow_implicit_invocation: false/);
});

test("both template languages ship the same file set (D52)", () => {
  const { files: pt } = renderAll({ targets: ["claude"], lang: "pt-BR", kit });
  const { files: en } = renderAll({ targets: ["claude"], lang: "en", kit });
  const tpl = (m) => [...m.keys()].filter((k) => k.startsWith(".redevkit/templates/")).sort();
  assert.deepEqual(tpl(pt), tpl(en));
  assert.ok(tpl(pt).length >= 25);
});

test("npm pack contains only the allowlist and no bytecode (H4)", { timeout: 120000 }, () => {
  assert.deepEqual(checkPack(packFiles()), []);
});
