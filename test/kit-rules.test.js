// Regression guards for the loop and verification rules of the kit (A01–A05, O05, B05–B07, B17, B21, N03, N04).
// Each test reads the kit sources and fails when a rule that closes a defective path is removed.
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { KIT_ROOT, loadKit, renderAll } from "../src/core/render.js";

const raw = (rel) => fs.readFileSync(path.join(KIT_ROOT, rel), "utf8");
// Collapse line wraps so that a rule reads as one sentence wherever the file breaks it.
const flat = (text) => text.replace(/\s+/g, " ");
const read = (rel) => flat(raw(rel));
// Text between a heading (or marker) and the next marker, flattened.
const section = (rel, start, end) => {
  const text = raw(rel);
  const i = text.indexOf(start);
  assert.ok(i >= 0, `${rel}: "${start}" not found`);
  const j = end ? text.indexOf(end, i + start.length) : text.length;
  assert.ok(j > i, `${rel}: "${end}" not found after "${start}"`);
  return flat(text.slice(i, j));
};

const VERIFY = "commands/redevkit-verify/SKILL.md";
const EXECUTION = "commands/redevkit-verify/references/execution.md";
const TEST = "commands/redevkit-test/SKILL.md";
const LOOPS = "commands/redevkit-test/references/loops.md";
const DEBUG = "commands/redevkit-debug/SKILL.md";
const CREATE = "commands/redevkit-create/SKILL.md";
const CONVERGE = "phases/redevkit-converge/SKILL.md";
const ROUTE = "phases/redevkit-route/SKILL.md";
const ORCHESTRATOR = "personas/orchestrator.md";
const LANGS = ["en", "pt-BR"];

const verifyStep1 = () => section(VERIFY, "### 1. Whole suite", "### 2. Converge");
const reuseRows = () =>
  raw(VERIFY)
    .split("\n")
    .filter((l) => /^\| `(PASS|FAIL)`/.test(l));

test("A02: verify never reuses a FAIL with the environment class", () => {
  const rows = reuseRows();
  const fail = rows.filter((l) => l.startsWith("| `FAIL`"));
  assert.equal(fail.length, 1, "exactly one FAIL reuse row");
  assert.match(fail[0], /Scope `global`/);
  assert.match(fail[0], /no `environment` class/);
  assert.match(verifyStep1(), /A `FAIL` with the `environment` class is never reused/);
  assert.match(read(VERIFY), /its step 1 never reuses an `environment` `FAIL`: the suite runs again/);
  assert.match(read(LOOPS), /An `environment` `FAIL` is never reused, so the next verify runs the suite again/);
});

test("A04: verify reuses directly only a global verdict; spec (full suite) only without failures outside the spec", () => {
  const rows = reuseRows();
  assert.ok(!rows.some((l) => /^\| `PASS` \|/.test(l)), "no unconditional PASS reuse row");
  const pass = rows.filter((l) => l.startsWith("| `PASS`"));
  assert.equal(pass.length, 2);
  assert.ok(pass.some((l) => /^\| `PASS` with Scope `global` \| yes \| Reuse it/.test(l)));
  const full = pass.find((l) => l.includes("`spec (full suite)`"));
  assert.ok(full, "spec (full suite) PASS row");
  assert.match(full, /\*\*Outside the spec\*\* lists no failure/);
  assert.match(verifyStep1(), /Only a `global` verdict is reused as it stands/);
  assert.match(verifyStep1(), /when its \*\*Outside the spec\*\* lists a failure the test procedure runs and classifies them by the global rules/);
});

test("A04: test verdict accepts failures outside the spec in scope spec (full suite), and only there", () => {
  const verdict = section(TEST, "Verdict: **PASS**", "A scenario that cannot be automated");
  assert.doesNotMatch(verdict, /PASS\*\* only when every command exited 0 \(in scope `global`, or failed only by/);
  assert.match(verdict, /no test of this run's scope failed/);
  assert.match(verdict, /`baseline` failures \(scope `global`\) or tests listed under \*\*Outside the spec\*\* \(scope `spec \(full suite\)`/);
  const evidence = section(TEST, "## Evidence rule", "## Handoff");
  assert.match(evidence, /a test of this run's scope \(not `baseline`, not listed under \*\*Outside the spec\*\*\) failed/);
  assert.match(section(TEST, "**Outside the spec.**", "### 5."), /it never reuses a run whose \*\*Outside the spec\*\* lists a failure/);
});

test("A04: both test-report templates state the same PASS rule and reuse rule", () => {
  const en = read("templates/en/reports/test-report.md");
  assert.doesNotMatch(en, /PASS only when every command exited 0 \(scope global: or failed only by baseline failures\)/);
  assert.match(en, /PASS only when no test of this run's scope failed/);
  assert.match(en, /tests listed under Outside the spec \(scope spec \(full suite\)\)/);
  assert.match(en, /a spec \(full suite\) run only when it is PASS and its Outside the spec list has no failure/);
  const pt = read("templates/pt-BR/reports/test-report.md");
  assert.doesNotMatch(pt, /PASS somente quando todos os comandos saíram com 0 \(escopo global: ou falharam só por falhas de baseline\)/);
  assert.match(pt, /PASS somente quando nenhum teste do escopo desta execução falhou/);
  assert.match(pt, /testes listados em Fora da spec \(escopo spec \(full suite\)\)/);
  assert.match(pt, /só uma execução PASS cuja lista Fora da spec não tem falha/);
});

test("A01: a wrong test of a global failure goes back to the verify and counts as a debug round", () => {
  const wrong = section(DEBUG, "- **The test is wrong**", "- **The behavior was never built**");
  assert.match(wrong, /`global` → `\{\{CMD:redevkit-verify\}\}`, whose step 1 runs the whole suite again \(never the stale `FAIL`\)/);
  assert.match(wrong, /`spec` → `\{\{CMD:redevkit-test\}\}`/);
  assert.match(wrong, /counts as a debug round of that loop \(Test cycle or Correction cycle/);
  const handoff = section(DEBUG, "## Handoff");
  assert.doesNotMatch(handoff, /`\{\{CMD:redevkit-test\}\}` for a wrong test/);
  assert.match(handoff, /for a wrong test, the command of the Failing scope as below \(`spec` → `\{\{CMD:redevkit-test\}\}`, `global` → `\{\{CMD:redevkit-verify\}\}`/);
  const memory = section(DEBUG, "## Memory phase 3", "## Evidence rule");
  assert.match(memory, /\+1 debug round of the loop of the Failing scope on every handoff this run makes inside it, to the test, verify or create command, whatever it changed/);
  assert.match(memory, /Correction cycle for `global`/);
});

test("1.3.1 F1: debug → create (behavior never built) counts a debug round, so verify → debug → create → test → verify is bounded", () => {
  const never = section(DEBUG, "- **The behavior was never built**", "- **The suite cannot run**");
  assert.match(never, /hand off to `\{\{CMD:redevkit-create\}\}`\. With Failing scope `spec` or `global` this handoff counts as a debug round of that loop too/);
  const testCycle = section(LOOPS, "### Test cycle", "### Correction cycle");
  assert.match(testCycle, /adds 1 on every handoff it makes in this loop \(Failing scope `spec`\), whatever the run changed/);
  assert.match(testCycle, /to `redevkit-create` for behavior never built \(so test → debug → create → test is bounded too\)/);
  const correction = section(LOOPS, "### Correction cycle", "### Unverified");
  assert.match(correction, /adds 1 on every handoff it makes in this loop \(Failing scope `global`\), whatever the run changed/);
  assert.match(correction, /so verify → debug → create → test → verify is bounded too\. A test `PASS` never resets this counter/);
});

test("1.3.1 A3: enhance never adopts the G2 approval of its change plan, even in --auto", () => {
  const ENHANCE = "commands/redevkit-enhance/SKILL.md";
  const step4 = section(ENHANCE, "### 4. Approve the change plan", "### 5. Implement");
  assert.doesNotMatch(step4, /the approval is adopted/);
  assert.match(step4, /so it is never adopted as an assumption: the run stops here even in `--auto`/);
  assert.match(step4, /In a non-interactive run without that approval, write the delta and the tasks, keep `- Plan approved: no`, implement nothing/);
  assert.match(read(ENHANCE), /`--auto`: after the approval, continue with `\{\{CMD:redevkit-test\}\}` `--auto`/);
  assert.match(read("context/AGENTS.block.md"), /It always stops at the gates: G1 constitution creation or amendment, G2 plan approval/);
});

test("A01: loops count the wrong-test handback and the verify never reuses a FAIL after a debug handback", () => {
  const correction = section(LOOPS, "### Correction cycle", "### Unverified");
  assert.match(correction, /a wrong test of a `global` failure always goes back to `redevkit-verify`, never to `redevkit-test`/);
  assert.match(correction, /A verify that follows a debug handback never reuses the old `FAIL` test run/);
  assert.match(correction, /its verdict is `failed` while debug rounds is 3 or more/);
  const fail = reuseRows().find((l) => l.startsWith("| `FAIL`"));
  assert.match(fail, /no debug handback since/);
  assert.match(verifyStep1(), /the Correction cycle debug rounds in `active\.md` differ from the \*\*Correction cycle\*\* the latest `verification\.md` run recorded/);
  assert.match(read(VERIFY), /also when it judges the test wrong, and that handback counts as a debug round/);
  // The disputed test is judged again by the test procedure, which asks the user on disagreement.
  assert.match(read(TEST), /in scope `global` it comes back through the verify command\) and you still judge it a `product-defect`, the spec is unclear: it stays `test-defect` and you ask the user/);
  // The verify records the counters it compares against.
  for (const lang of LANGS) {
    assert.match(raw(`templates/${lang}/reports/verification.md`), /debug rounds \[N\]\/3/);
  }
});

test("A03: a gap covered only by an Unverified feature's own task is carried into the active feature", () => {
  const step3 = section(CONVERGE, "3. **Assess the code.**", "4. **Assign severity.**");
  assert.match(step3, /only an open or blocked task of the \*\*receiving\*\* file covers a gap/);
  assert.match(step3, /A gap covered only by a task of the analyzed feature's own `tasks\.md` is a new finding: append one task that carries it/);
  assert.match(step3, /it is never carried twice/);
  assert.match(section(CONVERGE, "## Input", "## Prerequisites"), /the active feature's when `\{\{CMD:redevkit-verify\}\}` converges an Unverified feature/);
  const step2 = section(VERIFY, "### 2. Converge", "### 3. Execute");
  assert.match(step2, /a gap already covered by an open or blocked task of the \*\*active\*\* feature's `tasks\.md` is cited, not appended/);
  assert.match(step2, /A task that covers a gap only in an Unverified feature's own `tasks\.md` is carried into the active one/);
  assert.match(read(LOOPS), /An open or blocked task in the listed feature's own `tasks\.md` does not cover the gap: it is carried into the active feature's `tasks\.md` once/);
  assert.match(read(CREATE), /A Convergence task that carries another feature's task \("carries <feature> T0NN"\) also marks that original `\[X\]`/);
});

test("A05: the verify keeps the app it started running through the audits and stops it afterwards", () => {
  const step3 = section(VERIFY, "### 3. Execute", "### 4. Audit");
  assert.doesNotMatch(step3, /then stop it/);
  assert.match(step3, /keep it running: step 4 audits it by its URL/);
  const step4 = section(VERIFY, "### 4. Audit", "### 5. Report");
  assert.match(step4, /with `--url` of the app step 3 started/);
  assert.match(step4, /`--no-runtime` only when the type has no runtime or the app did not start/);
  assert.match(step4, /When the audits end, stop the app step 3 started and confirm its port is free; stop it also when the run leaves steps 3–4 early/);
  const exec = section(EXECUTION, "### 3. Execute", "### Checklist by Project Type");
  assert.doesNotMatch(exec, /then stop it/);
  assert.match(exec, /keep it running until the audits of step 4 end: they take its URL/);
  const audits = section(EXECUTION, "## Audits (step 4)", "## Fix policy");
  assert.match(audits, /with the app running \(the one step 3 started\) \| `verify_all\.py` with the app URL/);
  assert.match(audits, /7\. When the orchestrator run ends \(pass, fail, timeout or error\), stop the application step 3 started/);
  assert.match(audits, /an application the verify started never outlives the run/);
  assert.match(read("templates/en/reports/verification.md"), /\| App stop \(after the audits\) \|/);
  assert.match(read("templates/pt-BR/reports/verification.md"), /\| Parada da aplicação \(depois das auditorias\) \|/);
});

test("O05: the orchestrator role is played by the main session, never delegated as a subagent", () => {
  const rule3 = section(ROUTE, "3. **Detect domains**", "4. **Smallest coherent set.**");
  assert.match(rule3, /Coordination is never delegated/);
  assert.match(rule3, /the main session \(the conversation that owns the command\) follows `\{\{SKILL:redevkit-orchestrate\}\}` in that role/);
  assert.match(rule3, /not started as a subagent/);
  assert.match(read(ROUTE), /\| Multi-domain \|[^\n]*the main session coordinates per rule 3; never a subagent, never a task owner/);
  const where = section(ORCHESTRATOR, "## Where you run", "## Personas you coordinate");
  assert.match(where, /No command delegates to you as a subagent/);
  assert.match(where, /If you are running as a subagent and cannot delegate, never try to delegate/);
  assert.match(where, /return the delegation plan \(task → persona → brief\) to your caller, or execute the tasks inline/);
  assert.match(where, /`\{\{SKILL:redevkit-orchestrate\}\}` step 1/);
  // No command or phase delegates to the orchestrator persona.
  const kit = loadKit(KIT_ROOT);
  const texts = [
    ...kit.skills.flatMap((s) => [[s.source, s.body], ...s.files.map((f) => [`${s.source} › ${f.rel}`, f.text])]),
    ...kit.personas.map((p) => [p.source, p.body]),
  ];
  for (const [source, text] of texts) assert.doesNotMatch(text, /\{\{\s*DELEGATE:orchestrator\s*\}\}/, source);
});

test("the new rules survive rendering on both targets and languages", () => {
  for (const lang of LANGS) {
    const { perTarget } = renderAll({ targets: ["claude", "codex"], lang });
    const claude = flat(perTarget.claude.get(".claude/skills/redevkit-verify/SKILL.md"));
    const codex = flat(perTarget.codex.get(".agents/skills/redevkit-verify/SKILL.md"));
    for (const out of [claude, codex]) {
      assert.match(out, /A `FAIL` with the `environment` class is never reused/);
      assert.match(out, /Only a `global` verdict is reused as it stands/);
      assert.match(out, /stop the app step 3 started and confirm its port is free/);
      assert.doesNotMatch(out, /\{\{/);
    }
  }
});

// Second audit (B05, B06, B07, B17, B21, N03, N04).
const STATUS = "commands/redevkit-status/SKILL.md";
const DEPLOY = "commands/redevkit-deploy/SKILL.md";
const CODE_STATE = "commands/redevkit-test/references/code-state.md";
// Rows of the status handoff table, in order (the first row that matches wins).
const statusHandoffRow = (pattern) => {
  const text = raw(STATUS);
  const rows = text.slice(text.indexOf("## Handoff")).split("\n").filter((l) => l.startsWith("| "));
  const i = rows.findIndex((l) => pattern.test(l));
  assert.ok(i >= 0, `status handoff row ${pattern} not found`);
  return { i, row: rows[i] };
};
const tableRow = (rel, cell) => {
  const row = raw(rel).split("\n").find((l) => l.startsWith(cell));
  assert.ok(row, `${rel}: row ${cell} not found`);
  return row;
};

test("B05: the verify never reuses a test-defect FAIL and the answer is recorded so it is never asked again", () => {
  const fail = reuseRows().find((l) => l.startsWith("| `FAIL`"));
  assert.match(fail, /no `test-defect` class/);
  assert.match(verifyStep1(), /A `FAIL` with the `test-defect` class is never reused either: the test correction and the question for the user are resolved only by the test procedure, which runs again/);
  assert.match(read(LOOPS), /neither is a `test-defect` `FAIL`, whose test correction or question for the user only the test procedure resolves/);
  // The answer persists in the spec, so the rerun follows it instead of asking again.
  const limits = section(TEST, "Limits: one extra run", "**Outside the spec.**");
  assert.match(limits, /never send it to the debug command again before the user answers/);
  assert.match(limits, /Record each answer to a `test-defect` question .* in `spec\.md` › `## Clarifications` \/ `## Esclarecimentos`/);
  assert.match(limits, /every later run follows it and never asks it again/);
  assert.match(limits, /code that contradicts it is a `product-defect` that goes to the debug command with the answer as evidence/);
  // Verify handoff: answer, then the verify again, also for a test outside the spec test set.
  const handoff = section(VERIFY, "## Handoff");
  assert.match(handoff, /`test-defect` left → no command: the question for the user is pending .* once answered, run `\{\{CMD:redevkit-verify\}\}` again: its step 1 never reuses a `test-defect` `FAIL`/);
  assert.match(handoff, /also when the defective test is outside the active feature's spec test set: never `\{\{CMD:redevkit-test\}\}` for it/);
  // Status: a pending test-defect wins over the "verify failed" row and names the rerun command.
  const td = statusHandoffRow(/`FAIL` with `test-defect` left \(also after a `failed` verify\)/);
  const vf = statusHandoffRow(/Latest verify is `failed` and the code did not change after it/);
  assert.ok(td.i < vf.i, "the test-defect row must precede the verify-failed row");
  assert.match(td.row, /`\{\{CMD:redevkit-verify\}\}` when the run's Scope is `global`.*otherwise `\{\{CMD:redevkit-test\}\}`/);
});

test("B06: a test FAIL after the reference verify blocks the deploy, even on the same code", () => {
  const ref = section(CODE_STATE, "## Deploy reference run");
  assert.match(ref, /3\. No later red test: every run that the active feature's `test-report\.md` has after the test run the reference names in its Test evidence .* must be `PASS`/);
  assert.match(ref, /A `FAIL` run there → `BLOCKED`, even on the same code/);
  assert.match(read(DEPLOY), /no run of the active feature's `test-report\.md` after the test run it used may be `FAIL` \(a later red test invalidates it, even on the same code\)/);
  // The test command marks the verify in memory; the verify rewrites the line without it.
  const memory = section(TEST, "## Memory phase 3", "## Evidence rule");
  assert.match(memory, /On `FAIL`, when `- Verify:` of the active feature is `converged\+verified`, append `· invalidated by test FAIL YYYY-MM-DD HH:MM`/);
  assert.match(section(VERIFY, "## Memory phase 3", "## Evidence rule"), /rewritten without the `invalidated by test FAIL` marker/);
  // A PASS followed by a FAIL is never reused, so the new verify really runs the suite.
  assert.match(verifyStep1(), /A `PASS` followed in `test-report\.md` by a `FAIL` run is never reused: the suite runs again/);
  assert.match(statusHandoffRow(/`converged\+verified` on the current code/).row, /not `invalidated`/);
  for (const lang of LANGS) {
    assert.match(raw(`templates/${lang}/memory/active.md`), /- Verify: .*\[· invalidated by test FAIL/);
  }
  assert.match(read("templates/en/reports/deploy.md"), /\| Test runs after the reference \|.*\| OK \/ BLOCKED \|/);
  assert.match(read("templates/en/reports/deploy.md"), /when a test run after the one it used is FAIL \(even on the same code\)/);
  assert.match(read("templates/pt-BR/reports/deploy.md"), /\| Execuções de teste depois da referência \|.*\| OK \/ BLOCKED \|/);
  assert.match(read("templates/pt-BR/reports/deploy.md"), /quando uma execução de teste posterior à que ela usou é FAIL \(mesmo sobre o mesmo código\)/);
});

test("B07: a green spec (full suite) run with nothing failing outside the spec ends the baseline", () => {
  const row = flat(tableRow(TEST, "| `baseline` |"));
  assert.match(row, /and none with Scope `spec \(full suite\)` that is `PASS` with no failure under \*\*Outside the spec\*\*: the whole suite ran and passed, also when the verify reused that run/);
  assert.match(verifyStep1(), /a reused `spec \(full suite\)` `PASS` with no failure under \*\*Outside the spec\*\* is a fully green whole-suite run for the `baseline` class/);
  assert.match(read("templates/en/reports/test-report.md"), /or a PASS with scope spec \(full suite\) and no failure under Outside the spec, also when redevkit-verify reused it/);
  assert.match(read("templates/pt-BR/reports/test-report.md"), /ou um PASS de escopo spec \(full suite\) sem falha em Fora da spec, também quando o redevkit-verify o reaproveitou/);
});

test("B17: --rollback targets the latest report that changed the environment, never an aborted one", () => {
  const mode = section(DEPLOY, "### Rollback mode", "## Gates that apply");
  assert.doesNotMatch(mode, /read the latest report for the environment, show its rollback plan/);
  assert.match(mode, /whose outcome shows that the environment was changed and still is: `succeeded`, or `failed` when its execution log shows that the publication step completed/);
  assert.match(mode, /Skip `aborted` reports and `failed` reports that stopped before any step changed the environment/);
  assert.match(mode, /Show the chosen report and its rollback plan, confirm \(G6, and G4 for data\)/);
  assert.match(mode, /names the report it rolled back/);
  assert.match(read(DEPLOY), /`--rollback` executes the rollback plan of the latest deploy report for that environment that changed it/);
  assert.match(read("templates/en/reports/deploy.md"), /- \*\*Rollback of\*\*:/);
  assert.match(read("templates/pt-BR/reports/deploy.md"), /- \*\*Rollback de\*\*:/);
});

test("B21: an automatable scenario still MISSING is a test-defect owned by the test procedure", () => {
  const row = flat(tableRow(TEST, "| `test-defect` |"));
  assert.match(row, /Also a missing test: a scenario that can be automated and is still `MISSING` after step 2/);
  assert.match(row, /A missing test gets one more attempt to generate it \(step 2\); still `MISSING` → ask the user/);
  assert.match(section(TEST, "Verdict: **PASS**", "A scenario that cannot be automated"), /an automatable scenario left `MISSING` \(class `test-defect`: the test is missing, step 4\)/);
  assert.match(section(TEST, "## Handoff"), /`test-defect` left → no command: the question for the user is pending \(a spec decision, or how to test a scenario still `MISSING`\)/);
  assert.match(section(VERIFY, "## Handoff"), /pending \(a spec decision, or how to test a scenario still `MISSING`\)/);
  assert.match(read("templates/en/reports/test-report.md"), /test-defect \(missing test: still MISSING after generation\)/);
  assert.match(read("templates/en/reports/test-report.md"), /Scenarios still without a test\*\* \(automatable: class test-defect/);
  assert.match(read("templates/pt-BR/reports/test-report.md"), /test-defect \(teste ausente: continua MISSING depois da geração\)/);
  assert.match(read("templates/pt-BR/reports/test-report.md"), /Cenários ainda sem teste\*\* \(automatizáveis: classe test-defect/);
  // No new failure class: the classification table keeps the same five.
  const classes = raw(TEST).split("\n").filter((l) => /^\| `[a-z-]+` \|/.test(l)).map((l) => l.split("`")[1]);
  assert.deepEqual(classes, ["environment", "baseline", "test-defect", "not-implemented", "product-defect"]);
});

test("N03: the verify fix policy routes the same classes to the same commands, in the same order, as the verify SKILL", () => {
  const policy = section(EXECUTION, "## Fix policy", "## Verdict");
  assert.doesNotMatch(policy, /failed by `not-implemented` goes to the create command, everything else to the debug command/);
  assert.match(policy, /by `environment` → no command, fixed outside the code, then the verify again/);
  assert.match(policy, /by `test-defect` → no command, the question for the user is pending, then the verify again/);
  assert.match(policy, /by `not-implemented` → the create command/);
  assert.match(policy, /everything else \(a `product-defect`, build, start, flow or blocking audit\) → the debug command/);
  const ordered = (text, marks) => {
    const pos = marks.map((s) => text.indexOf(s));
    assert.ok(pos.every((p) => p >= 0), `missing entry: ${marks[pos.indexOf(-1)]}`);
    assert.deepEqual([...pos].sort((a, b) => a - b), pos);
  };
  ordered(section(VERIFY, "## Handoff"), [
    "class is `environment` → no command",
    "`test-defect` left → no command",
    "`not-implemented` → `{{CMD:redevkit-create}}`",
    "anything else (a `product-defect`",
  ]);
  ordered(policy, ["by `environment` →", "by `test-defect` →", "by `not-implemented` →", "everything else"]);
});

test("N04: both verification templates offer the test-defect next step", () => {
  assert.match(raw("templates/en/reports/verification.md"), /\*\*Next step\*\*: .*answer the question the test run names, then run redevkit-verify again \(failed: test-defect\)/);
  assert.match(raw("templates/pt-BR/reports/verification.md"), /\*\*Próximo passo\*\*: .*responder a pergunta que a execução de testes nomeia e rodar o redevkit-verify de novo \(failed: test-defect\)/);
  assert.match(raw("templates/en/reports/test-report.md"), /test-defect → answer the question it names/);
  assert.match(raw("templates/pt-BR/reports/test-report.md"), /test-defect → responder a pergunta que ela nomeia/);
});

test("E2E r11 (F-codex): every run, the verify's included, keeps the Tree fingerprint row of the template", () => {
  const verify = read("commands/redevkit-verify/SKILL.md");
  assert.match(verify, /full run section of the template: its Code state table keeps the `Tree fingerprint` row, never a prose summary/);
  const testSkill = read("commands/redevkit-test/SKILL.md");
  assert.match(testSkill, /Code state table \(the template's rows, `Tree fingerprint` included; never a prose line/);
  for (const lang of ["en", "pt-BR"]) assert.match(raw(`templates/${lang}/reports/test-report.md`), /\| Tree fingerprint \|/);
});

test("E2E r11 (F-codex rerun): the AGENTS.md block forbids piping text with accents into another program", () => {
  assert.match(read("context/AGENTS.block.md"), /never pipe text with accents into another program \(`@'…'@ \| python -`, `echo … \|`\): the shell re-encodes it and accents become `\?`/);
});

test("the second-audit rules survive rendering on both targets and languages", () => {
  for (const lang of LANGS) {
    const { perTarget } = renderAll({ targets: ["claude", "codex"], lang });
    for (const [target, root] of [["claude", ".claude/skills"], ["codex", ".agents/skills"]]) {
      const get = (p) => {
        const text = perTarget[target].get(`${root}/${p}`);
        assert.ok(text, `${target}: ${root}/${p} not rendered`);
        return flat(text);
      };
      assert.match(get("redevkit-verify/SKILL.md"), /A `FAIL` with the `test-defect` class is never reused either/);
      assert.match(get("redevkit-test/SKILL.md"), /Also a missing test: a scenario that can be automated/);
      assert.match(get("redevkit-test/references/code-state.md"), /No later red test/);
      assert.match(get("redevkit-deploy/SKILL.md"), /Skip `aborted` reports/);
      for (const p of ["redevkit-verify/SKILL.md", "redevkit-test/SKILL.md", "redevkit-status/SKILL.md", "redevkit-deploy/SKILL.md"]) {
        assert.doesNotMatch(get(p), /\{\{/, `${target} ${lang} ${p}`);
      }
    }
  }
});
