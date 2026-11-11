import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
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

test("first init --force backs up the user file it overwrites (no manifest, no AGENTS.md)", () => {
  const dir = tmpProject();
  try {
    const mine = ["---", "name: redevkit-plan", "description: my own skill", "---", "", "mine", ""].join("\n");
    write(dir, ".agents/skills/redevkit-plan/SKILL.md", mine);
    const r = cli(["init", "--yes", "--target", "codex", "--lang", "pt-BR", "--force"], dir);
    assert.equal(r.status, 0, r.stderr + r.stdout);
    assert.notEqual(read(dir, ".agents/skills/redevkit-plan/SKILL.md"), mine, "the forced file is overwritten");
    const root = path.join(dir, ".redevkit", "backups");
    assert.ok(fs.existsSync(root), "a backup directory exists");
    const saved = fs.readdirSync(root).some((id) => {
      const p = path.join(root, id, ".agents", "skills", "redevkit-plan", "SKILL.md");
      return fs.existsSync(p) && fs.readFileSync(p, "utf8") === mine;
    });
    assert.ok(saved, "the user's version is in the backup");
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
    // Files the rolled-back run did not touch stay: the claude install and the common files.
    const st = JSON.parse(cli(["status", "--json"], dir).stdout);
    assert.deepEqual(st.missing, [], "rollback must not delete managed files the run left untouched");
    assert.ok(has(dir, ".claude/skills/redevkit-new/SKILL.md"));
    assert.ok(has(dir, ".redevkit/templates/spec.md"));
    assert.equal(has(dir, ".codex/config.toml"), false, "the config file created by `target add` is removed again");
  } finally {
    rm(dir);
  }
});

test("rollback of an update restores only what the update touched, in the manifest language", () => {
  const dir = tmpProject();
  try {
    assert.equal(cli(["init", "--yes", "--target", "claude", "--lang", "en"], dir).status, 0);
    const skill = ".claude/skills/redevkit-status/SKILL.md";
    const original = read(dir, skill);
    // Simulate an older install of one file: the update rewrites only that file.
    write(dir, skill, "old version\n");
    const mPath = path.join(dir, ".redevkit", "manifest.json");
    const m = JSON.parse(fs.readFileSync(mPath, "utf8"));
    m.files[skill] = createHash("sha256").update("old version\n").digest("hex");
    fs.writeFileSync(mPath, JSON.stringify(m));
    const up = cli(["update"], dir);
    assert.equal(up.status, 0, up.stderr);
    assert.equal(read(dir, skill), original);
    const managed = Object.keys(JSON.parse(read(dir, ".redevkit/manifest.json")).files).length;
    const dry = cli(["rollback", "--dry-run"], dir);
    assert.equal(dry.status, 0, dry.stderr);
    assert.doesNotMatch(dry.stdout, /^\s+remove /m, "nothing to remove: the update added no file");
    const rb = cli(["rollback"], dir);
    assert.equal(rb.status, 0, rb.stderr);
    assert.match(rb.stdout, /Backup \S+ restored/, "messages follow the manifest language (en)");
    assert.equal(read(dir, skill), "old version\n");
    const st = JSON.parse(cli(["status", "--json"], dir).stdout);
    assert.deepEqual(st.missing, []);
    assert.equal(Object.keys(JSON.parse(read(dir, ".redevkit/manifest.json")).files).length, managed);
  } finally {
    rm(dir);
  }
});

test("first init backs up a user settings.json it rewrites; rollback undoes the whole init", () => {
  const dir = tmpProject();
  try {
    const mine = '{"model":"x"}\n';
    write(dir, ".claude/settings.json", mine);
    const r = cli(["init", "--yes", "--target", "claude", "--lang", "en"], dir);
    assert.equal(r.status, 0, r.stderr);
    assert.notEqual(read(dir, ".claude/settings.json"), mine, "managed allow entries were merged");
    const rb = cli(["rollback"], dir);
    assert.equal(rb.status, 0, rb.stderr + rb.stdout);
    assert.equal(read(dir, ".claude/settings.json"), mine);
    for (const rel of [".redevkit/manifest.json", "CLAUDE.md", "AGENTS.md", ".claude/skills"]) assert.equal(has(dir, rel), false, `${rel} created by init is removed`);
  } finally {
    rm(dir);
  }
});

test("usage errors exit with 2; --help and --version exit with 0", () => {
  const dir = tmpProject();
  try {
    for (const args of [["init", "--bogus"], ["nosuch"], ["target", "add"], ["init", "--target"], ["init", "a", "b"], []]) {
      const r = cli(args, dir);
      assert.equal(r.status, 2, `${args.join(" ") || "(no command)"}: ${r.stderr}`);
    }
    for (const args of [["--help"], ["init", "--help"], ["--version"]]) assert.equal(cli(args, dir).status, 0, args.join(" "));
    assert.deepEqual(fs.readdirSync(dir), [], "nothing written");
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

test("doctor: memory size limits (files 256 warn, changelog 512 warn, MEMORY.md 256 error, archive/ ignored)", () => {
  const dir = tmpProject();
  try {
    assert.equal(init(dir).status, 0);
    const fm = (type) => `---\ntype: ${type}\ncreated: 2026-11-08\nupdated: 2026-11-08\n---\n`;
    const body = (n) => Array.from({ length: n }, (_, i) => `- line ${i + 1}`).join("\n") + "\n";
    const core = { "constitution.md": "constitution", "project.md": "project", "system.md": "system", "tech.md": "tech", "active.md": "active", "user.md": "user" };
    for (const [f, type] of Object.entries(core)) write(dir, `.redevkit/memory/${f}`, fm(type) + (f === "system.md" ? "## Invariantes\n" : ""));
    const doctorMsgs = () => {
      const r = cli(["doctor", "--json"], dir);
      return { status: r.status, issues: JSON.parse(r.stdout).issues };
    };

    // At the limits: no size issue (frontmatter lines count too).
    write(dir, ".redevkit/memory/MEMORY.md", fm("index") + body(256 - 5));
    write(dir, ".redevkit/memory/changelog.md", fm("changelog") + body(512 - 5));
    write(dir, ".redevkit/memory/topics/a.md", fm("project") + body(256 - 5));
    write(dir, ".redevkit/memory/archive/changelog-2026-10.md", body(2000));
    let { issues } = doctorMsgs();
    assert.deepEqual(issues.filter((i) => /lines/.test(i.message)), [], "nothing over the limits yet");

    // One line over each limit.
    write(dir, ".redevkit/memory/MEMORY.md", fm("index") + body(256 - 4));
    write(dir, ".redevkit/memory/changelog.md", fm("changelog") + body(512 - 4));
    write(dir, ".redevkit/memory/topics/a.md", fm("project") + body(256 - 4));
    const r = doctorMsgs();
    issues = r.issues;
    const find = (file) => issues.find((i) => i.file === `.redevkit/memory/${file}` && /lines/.test(i.message));
    assert.equal(find("MEMORY.md")?.level, "error");
    assert.match(find("MEMORY.md").message, /257 lines \(max 256\)/);
    assert.equal(find("changelog.md")?.level, "warn");
    assert.match(find("changelog.md").message, /513 lines \(over 512\).*archive\/changelog-YYYY-MM\.md/);
    assert.equal(find("topics/a.md")?.level, "warn");
    assert.match(find("topics/a.md").message, /257 lines \(over 256\)/);
    assert.equal(find("archive/changelog-2026-10.md"), undefined, "archive/ is never size-checked");
    assert.equal(r.status, 1, "the MEMORY.md error makes the doctor fail");
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
