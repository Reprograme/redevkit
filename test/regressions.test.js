// Regression tests for the CLI defects found by the 1.2.0 audit (RELATORIO_ASTRA_VERIFICADO.md,
// A12–A21). A22 is covered in docs.test.js, next to the check it fixes.
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { parse as tomlParse } from "smol-toml";
import { checkMemory, detectPython, duplicateFeatureNumbers, pythonCompatible, which } from "../src/commands/doctor.js";
import { loadManifest } from "../src/core/manifest.js";
import { loadRuntimeEntries, packageVersion } from "../src/core/render.js";
import { mergeCodexConfig, unmergeCodexConfig } from "../src/core/runtime-config.js";
import { runStep } from "../e2e/run.mjs";
import { BIN, cli, has, read, rm, ROOT, tmpProject, treeState, write } from "./helpers.js";

const MANIFEST = ".redevkit/manifest.json";
const manifestOf = (dir) => JSON.parse(read(dir, MANIFEST));
const backupsOf = (dir) => (has(dir, ".redevkit/backups") ? fs.readdirSync(path.join(dir, ".redevkit", "backups")) : []);
const codexEntries = loadRuntimeEntries().codexEntries;

test("A12: rollback of the first init keeps a pre-existing file the init adopted unchanged", () => {
  const dir = tmpProject();
  try {
    const audit = fs.readFileSync(path.join(ROOT, "kit", "audits", "code_state.py"));
    write(dir, "AGENTS.md", "# Team notes\n");
    fs.mkdirSync(path.join(dir, ".redevkit", "audits"), { recursive: true });
    fs.writeFileSync(path.join(dir, ".redevkit", "audits", "code_state.py"), audit);
    const r = cli(["init", "--here", "--target", "codex", "--lang", "en", "--yes"], dir);
    assert.equal(r.status, 0, r.stderr + r.stdout);
    assert.match(r.stdout, /[1-9]\d* unchanged/);
    const [backup] = backupsOf(dir);
    const meta = JSON.parse(read(dir, `.redevkit/backups/${backup}/_backup.json`));
    assert.ok(meta.adopted.includes(".redevkit/audits/code_state.py"), "the adopted file is recorded in the backup");

    const dry = cli(["rollback", "--dry-run"], dir);
    assert.equal(dry.status, 0, dry.stderr);
    assert.match(dry.stdout, /restore AGENTS\.md/);
    assert.doesNotMatch(dry.stdout, /remove\s+\.redevkit\/audits\/code_state\.py/);
    assert.match(dry.stdout, /remove\s+\.redevkit\/audits\/checklist\.py/, "files the init created are still removed");

    const real = cli(["rollback"], dir);
    assert.equal(real.status, 0, real.stderr);
    assert.ok(has(dir, ".redevkit/audits/code_state.py"), "the user's file survives the rollback");
    assert.deepEqual(fs.readFileSync(path.join(dir, ".redevkit", "audits", "code_state.py")), audit);
    assert.ok(!has(dir, ".redevkit/audits/checklist.py"), "dry run and real rollback agree");
    assert.equal(read(dir, "AGENTS.md"), "# Team notes\n");
  } finally {
    rm(dir);
  }
});

test("A13: init over an existing but invalid manifest writes nothing and points to recovery", () => {
  const dir = tmpProject();
  try {
    write(dir, "AGENTS.md", "# Team notes\n");
    assert.equal(cli(["init", "--target", "codex", "--lang", "en", "--yes"], dir).status, 0);
    write(dir, MANIFEST, '{"schemaVersion": 1, "files": {');
    const before = treeState(dir);
    const r = cli(["init", "--here", "--yes"], dir);
    assert.equal(r.status, 1, r.stdout);
    assert.match(r.stderr, /redevkit rollback/);
    assert.match(r.stderr, /not valid JSON/);
    assert.deepEqual(treeState(dir), before, "nothing is written: no defaults, no new targets, no language switch");
    assert.ok(!has(dir, ".claude") && !has(dir, "CLAUDE.md"));

    // The suggested recovery works with the broken manifest and says what it cannot know.
    const rb = cli(["rollback"], dir);
    assert.equal(rb.status, 0, rb.stderr);
    assert.match(rb.stdout, /Manifesto atual inválido|manifest is invalid/i);
  } finally {
    rm(dir);
  }
});

test("A14: update, init and target refuse to downgrade a newer installation unless --allow-downgrade", () => {
  const dir = tmpProject();
  try {
    assert.equal(cli(["init", "--target", "codex", "--lang", "en", "--yes"], dir).status, 0);
    const m = manifestOf(dir);
    m.version = "9.9.9";
    write(dir, MANIFEST, `${JSON.stringify(m, null, 2)}\n`);
    const before = treeState(dir);
    for (const args of [["update"], ["update", "--dry-run"], ["init", "--yes"], ["target", "add", "claude"]]) {
      const r = cli(args, dir);
      assert.equal(r.status, 1, `${args.join(" ")}: ${r.stdout}`);
      assert.match(r.stderr, /9\.9\.9.*newer than this CLI/);
      assert.match(r.stderr, /--allow-downgrade/);
    }
    assert.deepEqual(treeState(dir), before, "a refused downgrade writes nothing");
    const ok = cli(["update", "--allow-downgrade"], dir);
    assert.equal(ok.status, 0, ok.stderr);
    assert.equal(manifestOf(dir).version, packageVersion());
  } finally {
    rm(dir);
  }
});

test("A14: the downgrade refusal is in the installation language (pt-BR)", () => {
  const dir = tmpProject();
  try {
    assert.equal(cli(["init", "--target", "codex", "--lang", "pt-BR", "--yes"], dir).status, 0);
    const m = manifestOf(dir);
    m.version = "9.9.9";
    write(dir, MANIFEST, `${JSON.stringify(m, null, 2)}\n`);
    const r = cli(["update"], dir);
    assert.equal(r.status, 1);
    assert.match(r.stderr, /mais nova que esta CLI/);
  } finally {
    rm(dir);
  }
});

test("A15: update with an unmigrated CLAUDE.md is a no-op: no backup, same lastRunId", () => {
  const dir = tmpProject();
  try {
    assert.equal(cli(["init", "--target", "both", "--lang", "en", "--yes"], dir).status, 0);
    write(dir, "CLAUDE.md", "# My own rules\n\nUse tabs.\n");
    const runId = manifestOf(dir).lastRunId;
    const backups = backupsOf(dir).length;
    for (let i = 0; i < 2; i += 1) {
      const r = cli(["update"], dir);
      assert.equal(r.status, 0, r.stderr);
      assert.match(r.stdout, /Nothing to do/);
    }
    assert.equal(backupsOf(dir).length, backups, "no useless backup");
    assert.equal(manifestOf(dir).lastRunId, runId);
    assert.equal(read(dir, "CLAUDE.md"), "# My own rules\n\nUse tabs.\n", "update never migrates");
  } finally {
    rm(dir);
  }
});

test("A16: uninstall of a Claude-only install never deletes the user's .codex/config.toml", () => {
  for (const content of ["", "\n\n  \n"]) {
    const dir = tmpProject();
    try {
      assert.equal(cli(["init", "--target", "claude", "--lang", "en", "--yes"], dir).status, 0);
      write(dir, ".codex/config.toml", content);
      const r = cli(["uninstall", "--yes"], dir);
      assert.equal(r.status, 0, r.stderr);
      assert.ok(has(dir, ".codex/config.toml"), `kept: ${JSON.stringify(content)}`);
      assert.equal(read(dir, ".codex/config.toml"), content);
    } finally {
      rm(dir);
    }
  }
  // Nothing of ours in the file: unmerge leaves it alone instead of returning "delete".
  assert.equal(unmergeCodexConfig("").text, undefined);
  assert.equal(unmergeCodexConfig("\n\n").text, undefined);
});

test("A17: an inline [features] table gets the key inside it; unmerge restores the original", () => {
  for (const user of ["features = { custom = true }\n", "features = {custom=true}\n", 'model = "x"\nfeatures = {}\n[profiles.a]\nm = 1\n']) {
    const merged = mergeCodexConfig(user, codexEntries);
    assert.equal(merged.ok, true, merged.error);
    assert.deepEqual(merged.skipped, []);
    assert.deepEqual(merged.added.map((k) => `${k.table}.${k.key}`).sort(), ["features.default_mode_request_user_input", "skills.max_context_tokens"]);
    const parsed = tomlParse(merged.text);
    assert.equal(parsed.features.default_mode_request_user_input, true);
    assert.equal(parsed.skills.max_context_tokens, 10000);
    if (user.includes("custom")) assert.equal(parsed.features.custom, true);
    if (user.includes("profiles")) assert.equal(parsed.profiles.a.m, 1);
    const again = mergeCodexConfig(merged.text, codexEntries);
    assert.equal(again.changed, false, "idempotent");
    assert.deepEqual(again.kept, [], "our inline key is recognized as ours");
    assert.equal(unmergeCodexConfig(merged.text).text, user);
  }
});

test("A17: an entry that cannot be added safely is skipped alone, with one clear warning", () => {
  const merged = mergeCodexConfig("features = 5\n", codexEntries);
  assert.equal(merged.ok, true);
  assert.deepEqual(merged.skipped.map((k) => `${k.table}.${k.key}`), ["features.default_mode_request_user_input"]);
  assert.deepEqual(merged.added.map((k) => `${k.table}.${k.key}`), ["skills.max_context_tokens"]);
  assert.equal(tomlParse(merged.text).skills.max_context_tokens, 10000);

  const dir = tmpProject();
  try {
    write(dir, ".codex/config.toml", "features = 5\n");
    const r = cli(["init", "--target", "codex", "--lang", "en", "--yes"], dir);
    assert.equal(r.status, 0, r.stderr);
    const warnings = r.stdout.split(/\r?\n/).filter((l) => l.includes("features.default_mode_request_user_input"));
    assert.equal(warnings.length, 1, r.stdout);
    assert.match(warnings[0], /was not added/);
    assert.doesNotMatch(r.stdout, /invalid TOML/);
    assert.equal(tomlParse(read(dir, ".codex/config.toml")).skills.max_context_tokens, 10000);
    assert.ok(manifestOf(dir).config.codexKeys.some((k) => k.table === "skills"));

    // The inline case end to end: both keys land and the doctor sees them.
    write(dir, ".codex/config.toml", "features = { custom = true }\n");
    assert.equal(cli(["update"], dir).status, 0);
    const doc = JSON.parse(cli(["doctor", "--json"], dir).stdout);
    assert.deepEqual(doc.issues.filter((i) => i.file === ".codex/config.toml" && /not set/.test(i.message)), []);
  } finally {
    rm(dir);
  }
});

test("A18: feature numbers past 999 count for duplicates and for the active feature path", () => {
  const dir = tmpProject();
  try {
    for (const d of ["998-a", "999-b", "1000-c", "1000-d"]) fs.mkdirSync(path.join(dir, "specs", d), { recursive: true });
    assert.deepEqual(duplicateFeatureNumbers(dir), [{ number: "1000", dirs: ["1000-c", "1000-d"] }]);
    write(dir, ".redevkit/memory/active.md", "---\ntype: active\ncreated: 2026-01-01\nupdated: 2026-01-01\n---\n\n- Feature: `specs/1000-ghost`\n");
    const issues = checkMemory(dir, "en").filter((i) => /active feature path/.test(i.message));
    assert.equal(issues.length, 1);
    assert.match(issues[0].message, /specs\/1000-ghost/);
  } finally {
    rm(dir);
  }
});

test("A19: a manifest with files: null (or other bad types) is reported as invalid, never thrown", () => {
  const dir = tmpProject();
  try {
    for (const bad of [{ files: null }, { files: [] }, { files: {}, targets: "codex" }, { files: {}, config: 3 }]) {
      write(dir, MANIFEST, JSON.stringify({ schemaVersion: 1, version: "1.2.0", lang: "en", targets: ["codex"], ...bad }));
      const { manifest, error } = loadManifest(dir);
      assert.equal(manifest, null);
      assert.ok(error, JSON.stringify(bad));
    }
    write(dir, MANIFEST, JSON.stringify({ schemaVersion: 1, version: "1.2.0", lang: "en", targets: ["codex"], files: null }));
    const doc = cli(["doctor", "--json"], dir);
    assert.equal(doc.status, 1);
    const report = JSON.parse(doc.stdout);
    assert.ok(report.issues.some((i) => i.file === MANIFEST && /unsupported schema/.test(i.message)));
    for (const args of [["status"], ["update"], ["uninstall", "--yes"]]) {
      const r = cli(args, dir);
      assert.equal(r.status, 1, args.join(" "));
      assert.match(r.stderr, /Manifesto inválido|Invalid manifest/);
    }
  } finally {
    rm(dir);
  }
});

test("A20: Python older than 3.9 is skipped for the next candidate and flagged by the doctor", () => {
  assert.equal(pythonCompatible("Python 3.9.0"), true);
  assert.equal(pythonCompatible("Python 3.14.4"), true);
  assert.equal(pythonCompatible("Python 3.8.10"), false);
  assert.equal(pythonCompatible("Python 2.7.18"), false);
  const versions = { python: "Python 3.8.10", py: "Python 3.14.4", python3: "Python 3.12.1" };
  const fake = (cmd) => versions[cmd] ?? null;
  const found = detectPython({ probeFn: fake });
  assert.notEqual(found.python, null);
  assert.notEqual(found.python.command, "python");
  assert.deepEqual(found.incompatible.map((p) => p.command), ["python"]);
  const none = detectPython({ probeFn: (cmd) => (cmd === "python" ? "Python 2.7.18" : cmd === "python3" ? "Python 3.8.10" : null) });
  assert.equal(none.python, null);
  assert.ok(none.incompatible.length >= 1);

  // End to end: only an old python on PATH.
  const dir = tmpProject();
  const bin = path.join(path.dirname(dir), "fake bin");
  try {
    fs.mkdirSync(bin);
    if (process.platform === "win32") fs.writeFileSync(path.join(bin, "python.cmd"), "@echo off\r\necho Python 3.8.10\r\n");
    else fs.writeFileSync(path.join(bin, "python"), "#!/bin/sh\necho Python 3.8.10\n", { mode: 0o755 });
    // Only the fake bin on PATH (one PATH key: Windows env names are case-insensitive).
    const env = { ...Object.fromEntries(Object.entries(process.env).filter(([k]) => k.toUpperCase() !== "PATH")), PATH: bin, REDEVKIT_NO_TTY: "1" };
    const r = spawnSync(process.execPath, [BIN, "doctor", "--json"], { cwd: dir, encoding: "utf8", env });
    const report = JSON.parse(r.stdout);
    assert.equal(report.tools.python, null);
    assert.ok(report.issues.some((i) => i.file === "tools" && /incompatible Python.*3\.8\.10.*3\.9\+/.test(i.message)), JSON.stringify(report.issues));
  } finally {
    rm(dir);
  }
});

test("A21: the E2E runs a .cmd agent shim with the prompt intact and records spawn failures", { skip: process.platform !== "win32" && "cmd shims are Windows-only" }, async () => {
  const dir = tmpProject("e2e work");
  const bin = path.join(path.dirname(dir), "bin com espaço");
  const savedPath = process.env.PATH;
  try {
    fs.mkdirSync(bin);
    fs.writeFileSync(
      path.join(bin, "echo.js"),
      [
        'let input = "";',
        'process.stdin.setEncoding("utf8");',
        'const done = () => process.stdout.write(JSON.stringify({ argv: process.argv.slice(2), stdin: input }) + "\\n");',
        'if (process.argv.includes("-")) { process.stdin.on("data", (d) => (input += d)); process.stdin.on("end", done); } else done();',
        "",
      ].join("\n"),
    );
    fs.writeFileSync(path.join(bin, "codex.cmd"), `@"${process.execPath}" "%~dp0echo.js" %*\r\n`);
    process.env.PATH = `${bin}${path.delimiter}${savedPath}`;
    // Safety: never reach a real (paid) agent from a test.
    assert.equal(String(which("codex")).toLowerCase(), path.join(bin, "codex.cmd").toLowerCase(), "the fake codex.cmd must come first on PATH");
    const logOf = (file) => JSON.parse(fs.readFileSync(file, "utf8").split(/\r?\n/).filter((l) => l.startsWith("{")).pop());

    const text = 'diga "olá & tchau" | 50% de %PATH% ^ (fim) <ok>';
    const one = await runStep("codex", dir, { id: "one", cmd: "redevkit-new", text }, path.join(dir, "one.jsonl"), 60000);
    assert.equal(one.code, 0, JSON.stringify(one));
    const got = logOf(path.join(dir, "one.jsonl"));
    assert.equal(got.argv.at(-1), `$redevkit-new ${text}`, "the prompt is one literal argument");
    assert.deepEqual(got.argv.slice(0, 2), ["exec", "--sandbox"]);

    const multi = "linha 1\nlinha 2 com \"aspas\"";
    const two = await runStep("codex", dir, { id: "two", cmd: "redevkit-plan", text: multi }, path.join(dir, "two.jsonl"), 60000);
    assert.equal(two.code, 0, JSON.stringify(two));
    const got2 = logOf(path.join(dir, "two.jsonl"));
    assert.equal(got2.argv.at(-1), "-", "a multi-line prompt goes on stdin");
    assert.equal(got2.stdin, `$redevkit-plan ${multi}`);

    // A runtime that cannot be started is a failed step, not a crash of the runner.
    process.env.PATH = path.dirname(dir);
    assert.equal(which("codex"), null);
    const three = await runStep("codex", dir, { id: "three", cmd: "redevkit-new", text: "x" }, path.join(dir, "three.jsonl"), 60000);
    assert.equal(three.code, null);
    assert.match(three.error, /codex not found/);
    assert.match(fs.readFileSync(path.join(dir, "three.jsonl"), "utf8"), /# spawn error: codex not found/);
  } finally {
    process.env.PATH = savedPath;
    rm(dir);
  }
});
