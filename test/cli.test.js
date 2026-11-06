import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { pathToFileURL } from "node:url";
import { BIN, cli, has, read, rm, tmpProject, treeState, write } from "./helpers.js";

const init = (dir, extra = []) => cli(["init", "--yes", "--target", "both", "--lang", "pt-BR", ...extra], dir);

test("init without TTY and without --yes fails and writes nothing (C4)", () => {
  const dir = tmpProject();
  try {
    const r = cli(["init"], dir);
    assert.equal(r.status, 2, r.stderr);
    assert.match(r.stderr, /--yes/);
    assert.deepEqual(fs.readdirSync(dir), []);
  } finally {
    rm(dir);
  }
});

test("init in a path with spaces and accents; a second init changes nothing", () => {
  const dir = tmpProject("meu projeto ção");
  try {
    const r1 = init(dir);
    assert.equal(r1.status, 0, r1.stderr + r1.stdout);
    for (const rel of ["AGENTS.md", "CLAUDE.md", ".redevkit/manifest.json", ".redevkit/.gitignore", ".claude/settings.json", ".codex/config.toml", ".claude/skills/redevkit-new/SKILL.md", ".agents/skills/redevkit-new/SKILL.md", ".agents/skills/redevkit-deploy/agents/openai.yaml"]) {
      assert.ok(has(dir, rel), rel);
    }
    assert.match(read(dir, "CLAUDE.md"), /^@AGENTS\.md/);
    const before = treeState(dir);
    const r2 = init(dir);
    assert.equal(r2.status, 0, r2.stderr);
    assert.deepEqual(treeState(dir), before, "second init must not change any file");
  } finally {
    rm(dir);
  }
});

test("init migrates an existing CLAUDE.md with backup (D40) and keeps AGENTS.md content", () => {
  const dir = tmpProject();
  try {
    write(dir, "CLAUDE.md", "# Old rules\n\nUse tabs.\n@docs/extra.md\n");
    write(dir, "AGENTS.md", "# Team notes\n\nBe kind.\n");
    const r = init(dir);
    assert.equal(r.status, 0, r.stderr);
    const agents = read(dir, "AGENTS.md");
    assert.match(agents, /<!-- REDEVKIT:BEGIN/);
    assert.match(agents, /Be kind\./);
    assert.match(agents, /migrado de CLAUDE\.md em \d{4}-\d{2}-\d{2}\)\n\n# Old rules\n\nUse tabs\.\n@docs\/extra\.md/);
    assert.match(read(dir, "CLAUDE.md"), /^@AGENTS\.md\n\nAs instruções/);
    const backups = fs.readdirSync(path.join(dir, ".redevkit", "backups"));
    assert.equal(backups.length, 1);
    assert.match(read(dir, `.redevkit/backups/${backups[0]}/CLAUDE.md`), /Use tabs/);
  } finally {
    rm(dir);
  }
});

test("init --dry-run writes nothing", () => {
  const dir = tmpProject();
  try {
    write(dir, "CLAUDE.md", "x\n");
    const r = init(dir, ["--dry-run"]);
    assert.equal(r.status, 0, r.stderr);
    assert.deepEqual(fs.readdirSync(dir), ["CLAUDE.md"]);
  } finally {
    rm(dir);
  }
});

test("invalid settings.json aborts that step without overwriting", () => {
  const dir = tmpProject();
  try {
    write(dir, ".claude/settings.json", "{ not json");
    const r = init(dir);
    assert.equal(r.status, 0, r.stderr);
    assert.equal(read(dir, ".claude/settings.json"), "{ not json");
    assert.match(r.stdout, /settings\.json/);
  } finally {
    rm(dir);
  }
});

test("update preserves local edits as conflicts and never touches memory/specs/DESIGN.md", () => {
  const dir = tmpProject();
  try {
    assert.equal(init(dir).status, 0);
    write(dir, ".redevkit/memory/MEMORY.md", "mine\n");
    write(dir, "specs/001-x/spec.md", "spec\n");
    write(dir, "DESIGN.md", "design\n");
    const skill = ".claude/skills/redevkit-status/SKILL.md";
    write(dir, skill, "edited by user\n");
    const manifestPath = path.join(dir, ".redevkit", "manifest.json");
    const m = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
    m.files[skill] = "0".repeat(64); // simulate an upstream change since install
    fs.writeFileSync(manifestPath, JSON.stringify(m));
    const r = cli(["update", "--conflict-report", "report.json"], dir);
    assert.equal(r.status, 0, r.stderr);
    assert.equal(read(dir, skill), "edited by user\n");
    const report = JSON.parse(read(dir, "report.json"));
    assert.ok(report.conflicts.some((c) => c.file === skill));
    assert.equal(read(dir, ".redevkit/memory/MEMORY.md"), "mine\n");
    assert.equal(read(dir, "specs/001-x/spec.md"), "spec\n");
    assert.equal(read(dir, "DESIGN.md"), "design\n");
  } finally {
    rm(dir);
  }
});

test("target remove/add codex and rollback", () => {
  const dir = tmpProject();
  try {
    assert.equal(init(dir).status, 0);
    const r1 = cli(["target", "remove", "codex"], dir);
    assert.equal(r1.status, 0, r1.stderr);
    assert.equal(has(dir, ".agents/skills"), false);
    assert.equal(has(dir, ".codex/agents"), false);
    assert.equal(has(dir, ".codex/config.toml"), false, "config created by us is removed");
    assert.ok(has(dir, "AGENTS.md"));
    assert.deepEqual(JSON.parse(read(dir, ".redevkit/manifest.json")).targets, ["claude"]);
    assert.equal(cli(["target", "remove", "claude"], dir).status, 2, "cannot remove the last target");
    const r2 = cli(["target", "add", "codex"], dir);
    assert.equal(r2.status, 0, r2.stderr);
    assert.ok(has(dir, ".agents/skills/redevkit-new/SKILL.md"));
    const rb = cli(["rollback"], dir);
    assert.equal(rb.status, 0, rb.stderr);
    assert.deepEqual(JSON.parse(read(dir, ".redevkit/manifest.json")).targets, ["claude"]);
    assert.equal(has(dir, ".agents/skills/redevkit-new/SKILL.md"), false);
  } finally {
    rm(dir);
  }
});

test("uninstall keeps memory, specs, DESIGN.md, notes and the CLAUDE.md pointer", () => {
  const dir = tmpProject();
  try {
    write(dir, ".claude/settings.json", JSON.stringify({ permissions: { allow: ["Read"] } }));
    write(dir, ".codex/config.toml", 'model = "x"\n');
    assert.equal(init(dir).status, 0);
    write(dir, ".redevkit/memory/MEMORY.md", "mine\n");
    write(dir, "specs/001-x/spec.md", "spec\n");
    write(dir, "DESIGN.md", "design\n");
    fs.appendFileSync(path.join(dir, "AGENTS.md"), "\nMy note.\n");
    assert.equal(cli(["uninstall"], dir).status, 2, "no TTY requires --yes");
    const r = cli(["uninstall", "--yes"], dir);
    assert.equal(r.status, 0, r.stderr);
    assert.equal(has(dir, ".claude/skills"), false);
    assert.equal(has(dir, ".agents"), false);
    assert.equal(has(dir, ".redevkit/manifest.json"), false);
    assert.equal(read(dir, ".redevkit/memory/MEMORY.md"), "mine\n");
    assert.equal(read(dir, "specs/001-x/spec.md"), "spec\n");
    assert.equal(read(dir, "DESIGN.md"), "design\n");
    assert.doesNotMatch(read(dir, "AGENTS.md"), /REDEVKIT:BEGIN/);
    assert.match(read(dir, "AGENTS.md"), /My note\./);
    assert.match(read(dir, "CLAUDE.md"), /@AGENTS\.md/);
    assert.deepEqual(JSON.parse(read(dir, ".claude/settings.json")), { permissions: { allow: ["Read"] } });
    assert.equal(read(dir, ".codex/config.toml"), 'model = "x"\n');
  } finally {
    rm(dir);
  }
});

test("status compares versions with semver and reports drift", () => {
  const dir = tmpProject();
  try {
    assert.equal(init(dir).status, 0);
    const m = JSON.parse(read(dir, ".redevkit/manifest.json"));
    m.version = "0.9.0";
    write(dir, ".redevkit/manifest.json", JSON.stringify(m));
    fs.rmSync(path.join(dir, ".claude", "skills", "redevkit-status", "SKILL.md"));
    const r = cli(["status", "--json"], dir);
    const s = JSON.parse(r.stdout);
    assert.equal(s.relation, "older");
    assert.ok(s.missing.includes(".claude/skills/redevkit-status/SKILL.md"));
  } finally {
    rm(dir);
  }
});

test("doctor: detects duplicate NNN, missing memory files and secrets; exit code != 0 on errors", () => {
  const dir = tmpProject();
  try {
    assert.equal(init(dir).status, 0);
    write(dir, "specs/001-a/spec.md", "x");
    write(dir, "specs/001-b/spec.md", "x");
    write(dir, ".redevkit/bugs/b1/test.md", "x");
    write(
      dir,
      ".redevkit/memory/MEMORY.md",
      "---\ntype: index\ncreated: 2026-11-06\nupdated: 2026-11-06\n---\n# M\n<!-- Entry: - [type] summary → arquivo.md -->\n- [project] bug → .redevkit/bugs/b1/test.md\n- [project] x → missing.md\n",
    );
    write(dir, ".redevkit/memory/user.md", "---\ntype: user\ncreated: 2026-11-06\nupdated: 2026-11-06\n---\napi_key = abcdefgh12345678\n");
    const r = cli(["doctor", "--json"], dir);
    assert.equal(r.status, 1);
    const report = JSON.parse(r.stdout);
    const msgs = report.issues.map((i) => `${i.file}: ${i.message}`).join("\n");
    assert.match(msgs, /duplicate feature number 001/);
    assert.match(msgs, /missing core memory file/);
    assert.match(msgs, /index link does not resolve: missing\.md/);
    assert.doesNotMatch(msgs, /arquivo\.md|bugs\/b1/, "comments and project-root targets are fine");
    assert.match(msgs, /possible secret/);
    assert.ok(report.budgets.claude.total > 0);
  } finally {
    rm(dir);
  }
});

test("bin guard works through a path with spaces (H1) and when imported", async () => {
  const base = fs.mkdtempSync(path.join(os.tmpdir(), "redevkit bin "));
  try {
    const r = spawnSync(process.execPath, [BIN, "--version"], { cwd: base, encoding: "utf8" });
    assert.equal(r.stdout.trim(), JSON.parse(fs.readFileSync(path.join(path.dirname(BIN), "..", "package.json"), "utf8")).version);
    const mod = await import(pathToFileURL(BIN).href);
    assert.equal(typeof mod.main, "function");
  } finally {
    fs.rmSync(base, { recursive: true, force: true });
  }
});

test("junk files do not break commands (Y12)", () => {
  const dir = tmpProject();
  try {
    write(dir, "desktop.ini", "[.ShellClassInfo]\n");
    write(dir, ".claude/skills/Thumbs.db", "x");
    assert.equal(init(dir).status, 0);
    assert.equal(cli(["status"], dir).status, 0);
    assert.equal(cli(["uninstall", "--yes"], dir).status, 0);
    assert.ok(has(dir, "desktop.ini"));
  } finally {
    rm(dir);
  }
});
