// Regression tests for the E2E runner (RELATORIO_ASTRA_VERIFICADO2.md B13, B15, B16).
// SAFETY: these tests never reach a real (paid) agent. This process's PATH holds only the test's
// own bin folder, every runStep call gets an explicit env with that same PATH, and before each call
// guard() checks that the runtime resolves to the fake inside that folder (it throws otherwise).
// The --check runs get a PATH where neither `claude` nor `codex` resolves, and never --resume.
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { which } from "../src/commands/doctor.js";
import { COORDINATOR, check, delegatedPersonas, overallVerdict, runStep, runtimeCommand, SCENARIOS, STEPS_CHECK, stepFailed, stepsCriterion } from "../e2e/run.mjs";
import { BIN, ROOT } from "./helpers.js";

const BASE = fs.realpathSync.native(fs.mkdtempSync(path.join(os.tmpdir(), "redevkit-e2e-runner-")));
const FAKE_BIN = path.join(BASE, "bin fake");
fs.mkdirSync(FAKE_BIN);

// The fake agent: the mode comes from FAKE_MODE in the env runStep passes on.
fs.writeFileSync(
  path.join(FAKE_BIN, "agent.js"),
  [
    'const { spawn } = require("node:child_process");',
    'const fs = require("node:fs");',
    'const path = require("node:path");',
    "const mode = process.env.FAKE_MODE;",
    "const hold = Number(process.env.FAKE_HOLD_MS || 20000);",
    "const pidFile = process.env.FAKE_PID_FILE;",
    "// A holder that inherits stdout/stderr and keeps them open; it records its pid for cleanup.",
    'const holder = () => spawn(process.execPath, ["-e", `require("fs").appendFileSync(${JSON.stringify(pidFile)}, process.pid + "\\\\n"); setTimeout(() => {}, ${hold})`], { stdio: ["ignore", "inherit", "inherit"], detached: true }).unref();',
    'if (mode === "ok") { console.log(JSON.stringify({ type: "fake", ok: true })); process.exit(0); }',
    'if (mode === "fail") process.exit(3);',
    "// B13 variant 1: the main process exits 0 at once; a detached grandchild holds stdout.",
    'if (mode === "orphan-exit") { holder(); console.log("main exiting"); setTimeout(() => process.exit(0), 100); }',
    "// B13 variant 2: the main process never exits; an orphaned holder (its parent already gone, so",
    "// out of the tree the timeout kills) keeps stdout open.",
    'if (mode === "hang") {',
    '  if (process.argv.includes("--intermediate")) { holder(); setTimeout(() => process.exit(0), 100); }',
    '  else { spawn(process.execPath, [__filename, "--intermediate"], { stdio: ["ignore", "inherit", "inherit"], env: process.env }); setTimeout(() => {}, 60000); }',
    "}",
    "",
  ].join("\n"),
);
if (process.platform === "win32") {
  fs.writeFileSync(path.join(FAKE_BIN, "codex.cmd"), `@"${process.execPath}" "%~dp0agent.js" %*\r\n`);
} else {
  // Absolute paths only: the test PATH holds just this folder, so not even `dirname` is found.
  fs.writeFileSync(path.join(FAKE_BIN, "codex"), `#!/bin/sh\nexec "${process.execPath}" "${path.join(FAKE_BIN, "agent.js")}" "$@"\n`, { mode: 0o755 });
}

/** An env whose PATH is only the fake bin folder (every PATH spelling removed first). */
const fakeEnv = (extra = {}) => {
  const env = {};
  for (const [k, v] of Object.entries(process.env)) if (k.toLowerCase() !== "path") env[k] = v;
  return { ...env, PATH: FAKE_BIN, ...extra };
};
// Belt and braces: this test process cannot find a real agent either.
for (const k of Object.keys(process.env)) if (k.toLowerCase() === "path" && k !== "PATH") delete process.env[k];
process.env.PATH = FAKE_BIN;

const inside = (file, dir) => {
  const f = fs.realpathSync.native(file).toLowerCase();
  const d = fs.realpathSync.native(dir).toLowerCase();
  return f.startsWith(d + path.sep);
};

/** SAFETY lock: the runtime runStep will start must be the fake one, or the test aborts. */
const guard = (runtime, env) => {
  const [exe] = runtimeCommand(runtime, BASE, "x", [], env);
  if (!exe || !inside(exe, FAKE_BIN)) throw new Error(`SAFETY ABORT: ${runtime} resolves to ${exe}, outside ${FAKE_BIN}`);
  assert.ok(!which("claude", env), "SAFETY: no claude on the test PATH");
  return exe;
};

const holderPids = (file) => (fs.existsSync(file) ? fs.readFileSync(file, "utf8").split(/\s+/).filter(Boolean) : []);

const guardedRun = async (mode, timeoutMs, drainMs, name) => {
  const work = path.join(BASE, `work ${name}`);
  fs.mkdirSync(work, { recursive: true });
  const pidFile = path.join(work, "holder.pids");
  const env = fakeEnv({ FAKE_MODE: mode, FAKE_PID_FILE: pidFile });
  guard("codex", env);
  const log = path.join(work, "step.jsonl");
  const t0 = Date.now();
  let pids = [];
  try {
    const r = await runStep("codex", work, { id: name, cmd: "redevkit-test", text: "x" }, log, timeoutMs, [], { env, drainMs });
    const elapsed = Date.now() - t0;
    pids = holderPids(pidFile);
    return { r, elapsed, pids, log: fs.readFileSync(log, "utf8") };
  } finally {
    for (const pid of pids.length ? pids : holderPids(pidFile)) {
      try {
        process.kill(Number(pid));
      } catch {
        // already gone
      }
    }
  }
};

/**
 * How long the holder keeps stdout open, and the bound a step must settle within: the timeout,
 * the drain cap and an allowance for killing the tree (taskkill on a loaded CI runner can take
 * seconds). The bound stays far below HOLD_MS, so passing proves the runner did not wait for it.
 */
const HOLD_MS = 20000;
const KILL_ALLOWANCE_MS = 4000;
const settleBound = (timeoutMs, drainMs) => timeoutMs + drainMs + KILL_ALLOWANCE_MS;

test.after(() => fs.rmSync(BASE, { recursive: true, force: true }));

test("safety: the test PATH resolves only the fake codex", () => {
  const exe = guard("codex", fakeEnv());
  assert.ok(inside(exe, FAKE_BIN), exe);
  assert.ok(inside(which("codex"), FAKE_BIN), "this process's own PATH is the fake bin too");
  assert.throws(() => guard("codex", { ...fakeEnv(), PATH: path.join(BASE, "nowhere") }), /not found/);
});

test("B13: a normal step still records its exit code (0 and non-zero)", async () => {
  const ok = await guardedRun("ok", 20000, 1000, "ok");
  assert.equal(ok.r.code, 0, JSON.stringify(ok.r));
  assert.equal(ok.r.timedOut, undefined);
  assert.equal(stepFailed(ok.r), false);
  assert.match(ok.log, /"type":"fake"/);
  const bad = await guardedRun("fail", 20000, 1000, "fail");
  assert.equal(bad.r.code, 3, JSON.stringify(bad.r));
  assert.equal(stepFailed(bad.r), true);
});

test("B13: the agent exits 0 but a detached grandchild holds stdout: the drain is capped", async () => {
  const timeoutMs = 1000;
  const drainMs = 1000;
  const { r, elapsed, log, pids } = await guardedRun("orphan-exit", timeoutMs, drainMs, "orphan-exit");
  assert.equal(pids.length, 1, "the holder started");
  assert.ok(elapsed < settleBound(timeoutMs, drainMs), `settled after ${elapsed} ms (the holder keeps stdout for ${HOLD_MS / 1000} s)`);
  assert.equal(r.code, 0, JSON.stringify(r));
  assert.equal(r.timedOut, undefined, "the agent exited in time");
  assert.equal(r.drainCut, true);
  assert.match(log, /main exiting/);
  assert.match(log, /# output drain cut after 1000ms/);
});

test("B13: the agent never exits: timeout kills the tree, the step fails and the drain is capped", async () => {
  const timeoutMs = 1000;
  const drainMs = 1000;
  const { r, elapsed, log, pids } = await guardedRun("hang", timeoutMs, drainMs, "hang");
  assert.equal(pids.length, 1, "the holder started");
  assert.ok(elapsed >= timeoutMs - 50, `settled after ${elapsed} ms`);
  assert.ok(elapsed < settleBound(timeoutMs, drainMs), `settled after ${elapsed} ms (agent sleeps 60 s, holder ${HOLD_MS / 1000} s)`);
  assert.equal(r.timedOut, true, JSON.stringify(r));
  assert.notEqual(r.code, 0);
  assert.equal(stepFailed(r), true);
  assert.match(log, /# timeout: no exit after 1000ms, process tree killed \(step failed\)/);
});

// ---------- B15 ----------
const A_OK = [
  { id: "new", code: 0 },
  { id: "plan", code: 0 },
  { id: "create", code: 0 },
];

test("B15: a required step with a non-zero exit, a timeout or no run fails the steps criterion", () => {
  const failed = stepsCriterion("A", [...A_OK, { id: "test", code: 1 }]);
  assert.equal(failed.ok, false);
  assert.match(failed.detail, /failed: test: exit=1/);
  assert.equal(stepsCriterion("A", [...A_OK, { id: "test", code: null, timedOut: true }]).ok, false);
  assert.equal(stepsCriterion("A", [...A_OK, { id: "test", code: 0, timedOut: true }]).ok, false, "a timeout fails even with code 0");
  assert.equal(stepsCriterion("A", [...A_OK, { id: "test", code: null, error: "codex not found" }]).ok, false);
  const missing = stepsCriterion("A", A_OK);
  assert.equal(missing.ok, false);
  assert.match(missing.detail, /not run: test/);
  const none = stepsCriterion("A", []);
  assert.equal(none.ok, null, "no steps.json: the outcome cannot be judged (SKIPPED), never PASS");
  assert.match(none.detail, /^SKIPPED/);
  assert.equal(stepsCriterion("A", [...A_OK, { id: "test", code: 0 }]).ok, true);
});

test("verdict: any FAIL wins; a SKIPPED criterion without failures is INCONCLUSIVE, never PASS", () => {
  assert.equal(overallVerdict([{ ok: true }, { ok: true }]), "PASS");
  assert.equal(overallVerdict([{ ok: true }, { ok: null }]), "INCONCLUSIVE");
  assert.equal(overallVerdict([{ ok: false }, { ok: null }]), "FAIL");
});

test("B15: a failed attempt is accepted only when a later attempt of the same command succeeded", () => {
  // A: --resume test after the failed test.
  const resumed = stepsCriterion("A", [...A_OK, { id: "test", code: 1 }, { id: "test", code: 0, resumed: true }]);
  assert.equal(resumed.ok, true, resumed.detail);
  assert.match(resumed.detail, /recovered: test: exit=1 → test \(resume\) ok/);
  // B: the scripted retest (redevkit-test) recovers a failed test; old steps.json has no cmd field.
  const b = (test, retest) => [
    { id: "new", code: 0 },
    { id: "enhance", code: 0 },
    { id: "inject-spec-bug", code: 0, harness: true },
    { id: "test", ...test },
    { id: "debug", code: 0 },
    { id: "retest", ...retest },
    { id: "verify", code: 0 },
  ];
  assert.equal(stepsCriterion("B", b({ code: 1 }, { code: 0 })).ok, true);
  assert.equal(stepsCriterion("B", b({ code: 0 }, { code: 1 })).ok, false, "an earlier success does not excuse a later failure");
  assert.equal(stepsCriterion("B", b({ code: 1 }, { code: 0, timedOut: true })).ok, false);
  // Another command does not recover it: a failed debug stays failed after a good retest.
  const debug = b({ code: 0 }, { code: 0 });
  debug[4] = { id: "debug", code: 1 };
  assert.equal(stepsCriterion("B", debug).ok, false);
});

/** Scenario A project whose files satisfy every file check (as in the verification's reproduction). */
const projectA = (dir, env) => {
  const init = spawnSync(process.execPath, [BIN, "init", "--yes", "--target", "codex", "--lang", "pt-BR"], { cwd: dir, env, encoding: "utf8" });
  assert.equal(init.status, 0, init.stderr + init.stdout);
  const mem = path.join(dir, ".redevkit", "memory");
  fs.mkdirSync(mem, { recursive: true });
  const core = { "MEMORY.md": "index", "constitution.md": "constitution", "project.md": "project", "system.md": "system", "tech.md": "tech", "active.md": "active", "changelog.md": "changelog", "user.md": "user" };
  for (const [f, type] of Object.entries(core)) {
    const extra = f === "constitution.md" ? "\n- **Test-First**: obrigatorio\n" : f === "system.md" ? "\n## Invariantes\n\n- nenhuma\n" : "";
    fs.writeFileSync(path.join(mem, f), `---\ntype: ${type}\ncreated: 2026-11-25\nupdated: 2026-11-25\n---\n\n# ${f}\n${extra}`);
  }
  const fd = path.join(dir, "specs", "001-nave");
  fs.mkdirSync(fd, { recursive: true });
  fs.writeFileSync(path.join(fd, "spec.md"), "# Spec\n\nJogo de nave.\n");
  fs.writeFileSync(path.join(fd, "plan.md"), "# Plano\n\nSkills: game-development, 2d-games, web-games.\n");
  fs.writeFileSync(path.join(fd, "tasks.md"), "# Tasks\n\n- [X] T001 [US1] Escrever teste do movimento — test/move.test.js — @game-developer\n- [X] T002 [US1] Implementar movimento — src/move.js — @game-developer\n");
  fs.writeFileSync(path.join(fd, "test-report.md"), "# Test report\n\n## Execução 2026-11-25 10:00 — PASS\n\n- **Escopo**: spec\n");
};

test("B15: --check gives FAIL when a step failed and PASS when a later attempt recovered it", () => {
  // SAFETY: a PATH with node only; neither runtime resolves, and --check without --resume never
  // starts an agent.
  const env = fakeEnv({ PATH: path.dirname(process.execPath) });
  for (const rt of ["claude", "codex"]) if (which(rt, env)) throw new Error(`SAFETY ABORT: ${rt} resolves to ${which(rt, env)}`);
  const proj = path.join(BASE, "check A", "projeto");
  const out = path.join(BASE, "check A", "out");
  fs.mkdirSync(proj, { recursive: true });
  fs.mkdirSync(out, { recursive: true });
  projectA(proj, env);
  const runCheck = (steps) => {
    fs.writeFileSync(path.join(out, "steps.json"), JSON.stringify({ workDir: proj, steps }, null, 2));
    const r = spawnSync(process.execPath, [path.join(ROOT, "e2e", "run.mjs"), "--scenario", "A", "--runtime", "codex", "--check", proj, "--out", out], { cwd: ROOT, env, encoding: "utf8" });
    const result = JSON.parse(fs.readFileSync(path.join(out, "result.json"), "utf8"));
    return { status: r.status, result, row: result.results.find((x) => x.name === STEPS_CHECK), md: fs.readFileSync(path.join(out, "result.md"), "utf8") };
  };
  const red = runCheck([...A_OK, { id: "test", code: 1 }]);
  assert.equal(red.row.ok, false, JSON.stringify(red.row));
  assert.equal(red.result.passed, false);
  assert.equal(red.status, 1);
  assert.match(red.md, /\*\*Verdict:\*\* FAIL/);
  assert.deepEqual(red.result.results.filter((x) => !x.ok).map((x) => x.name), [STEPS_CHECK], "only the steps criterion fails");

  const recovered = runCheck([...A_OK, { id: "test", code: 1 }, { id: "test", code: 0, resumed: true }]);
  assert.equal(recovered.row.ok, true, JSON.stringify(recovered.row));
  assert.equal(recovered.result.passed, true, JSON.stringify(recovered.result.results.filter((x) => !x.ok)));
  assert.equal(recovered.status, 0);
  assert.match(recovered.md, /\*\*Verdict:\*\* PASS/);
});

// ---------- B16 ----------
test("B16: the R delegation step asks for the specialists only; orchestrator is the main session", () => {
  const all = fs.readdirSync(path.join(ROOT, "kit", "personas")).filter((f) => f.endsWith(".md")).map((f) => f.replace(/\.md$/, ""));
  const specialists = delegatedPersonas();
  assert.equal(COORDINATOR, "orchestrator");
  assert.ok(all.includes(COORDINATOR));
  assert.ok(!specialists.includes(COORDINATOR));
  assert.deepEqual(specialists, all.filter((p) => p !== COORDINATOR).sort());
  assert.equal(specialists.length, 18);
  const prompt = SCENARIOS.R.steps[1].text;
  assert.match(prompt, /Para cada uma das 18 personas especialistas/);
  assert.doesNotMatch(prompt, /19 personas/);
  for (const p of specialists) assert.ok(prompt.includes(p), p);
  assert.match(prompt, /orchestrator coordena e nunca é delegado como subagente/);
});

/** An R work dir with valid (empty) routing, a personas.json and, for Claude, a delegation log. */
const routingRun = (name, { answers, subagents = [] }) => {
  const dir = path.join(BASE, `R ${name}`);
  const tmp = path.join(dir, ".redevkit", "tmp");
  fs.mkdirSync(tmp, { recursive: true });
  fs.writeFileSync(path.join(tmp, "routing.json"), "[]");
  fs.writeFileSync(path.join(tmp, "personas.json"), JSON.stringify(answers));
  const log = path.join(dir, "02-personas.jsonl");
  const content = subagents.map((t) => ({ type: "tool_use", name: "Agent", input: { subagent_type: t, prompt: "q" } }));
  fs.writeFileSync(log, `${JSON.stringify({ type: "assistant", message: { content } })}\n`);
  const steps = ["route", "personas"].map((id) => ({ id, code: 0, diff: { added: [], changed: [], removed: [] } }));
  return (runtime) => Object.fromEntries(check({ scenario: "R", workDir: dir, transcripts: [log], steps, runtime }).map((r) => [r.name, r]));
};

test("B16: the R checker requires the 18 specialists and that orchestrator is not delegated", () => {
  const specialists = delegatedPersonas();
  const answer = (persona, mode) => ({ persona, mode, answer: `Sou ${persona}; nunca faço o trabalho de outra persona.` });
  const answered = `all 18 specialist personas answered (every persona except ${COORDINATOR})`;
  const claudeDelegated = "Claude Code: each specialist delegated as a subagent of its type";
  const codexMode = "Codex: delegation mode recorded for every specialist (subagent or inline fallback)";
  const notDelegated = `${COORDINATOR} not delegated as a subagent (the main session coordinates)`;

  const good = routingRun("good", { answers: specialists.map((p) => answer(p, "subagent")), subagents: specialists })("claude");
  assert.equal(good[answered].ok, true, good[answered].detail);
  assert.equal(good[claudeDelegated].ok, true, good[claudeDelegated].detail);
  assert.equal(good[notDelegated].ok, true);
  assert.equal(good[STEPS_CHECK].ok, true, good[STEPS_CHECK].detail);

  const withCoordinator = routingRun("coordinator", {
    answers: [...specialists, COORDINATOR].map((p) => answer(p, "subagent")),
    subagents: [...specialists, COORDINATOR],
  })("claude");
  assert.equal(withCoordinator[claudeDelegated].ok, true);
  assert.equal(withCoordinator[notDelegated].ok, false, "delegating orchestrator breaks the route rule");

  const missing = routingRun("missing", { answers: specialists.slice(1).map((p) => answer(p, "subagent")), subagents: specialists.slice(1) })("claude");
  assert.equal(missing[answered].ok, false);
  assert.equal(missing[claudeDelegated].ok, false);
  assert.match(missing[claudeDelegated].detail, new RegExp(specialists[0]));

  const codex = routingRun("codex", { answers: specialists.map((p) => answer(p, "inline")) })("codex");
  assert.equal(codex[answered].ok, true);
  assert.equal(codex[codexMode].ok, true, codex[codexMode].detail);
  assert.equal(codex[notDelegated].ok, true);
  const codexCoordinator = routingRun("codex coordinator", { answers: [...specialists.map((p) => answer(p, "inline")), answer(COORDINATOR, "subagent")] })("codex");
  assert.equal(codexCoordinator[notDelegated].ok, false);
});
