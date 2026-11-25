// Regression tests for the CLI defects confirmed by the second audit (RELATORIO_ASTRA_VERIFICADO2.md):
// B01, B02, B10, B11, B14, B19 and N02. Every scenario runs in a temporary project and checks the
// manifest against the disk.
import assert from "node:assert/strict";
import { spawn, spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { applySync, computeSync } from "../src/core/install.js";
import { createBackup, createRunId } from "../src/core/managed-tree.js";
import { loadManifest } from "../src/core/manifest.js";
import { BIN, cli, has, read, rm, ROOT, tmpProject, treeState, write } from "./helpers.js";

const MANIFEST = ".redevkit/manifest.json";
const LOCK = ".redevkit/redevkit.lock";
const manifestOf = (dir) => JSON.parse(read(dir, MANIFEST));
const setManifest = (dir, m) => write(dir, MANIFEST, `${JSON.stringify(m, null, 2)}\n`);
const backupsOf = (dir) => (has(dir, ".redevkit/backups") ? fs.readdirSync(path.join(dir, ".redevkit", "backups")).sort() : []);
/** Managed files of the manifest that are missing on disk. */
const missingOf = (dir) => Object.keys(manifestOf(dir).files).filter((f) => !has(dir, f));
const initCodex = (dir) => {
  const r = cli(["init", "--target", "codex", "--lang", "en", "--yes"], dir);
  assert.equal(r.status, 0, r.stderr + r.stdout);
  return Object.keys(manifestOf(dir).files).sort();
};
/** Backup ids created by a command (the run's own backup, never the pre-rollback ones). */
const newBackup = (dir, before) => {
  const added = backupsOf(dir).filter((b) => !before.includes(b) && !b.startsWith("pre-rollback-"));
  assert.equal(added.length, 1, `one new backup: ${added}`);
  return added[0];
};
const cliAsync = (args, cwd, env = {}) =>
  new Promise((resolve) => {
    const child = spawn(process.execPath, [BIN, ...args], { cwd, env: { ...process.env, REDEVKIT_NO_TTY: "1", ...env } });
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (d) => (stdout += d));
    child.stderr.on("data", (d) => (stderr += d));
    child.on("close", (status) => resolve({ status, stdout, stderr }));
    child.stdin.end();
  });

test("B01: a manifest without valid targets is invalid; no write command proceeds and the project is unchanged", () => {
  const dir = tmpProject();
  try {
    initCodex(dir);
    const good = manifestOf(dir);
    const variants = [
      (m) => delete m.targets,
      (m) => (m.targets = []),
      (m) => (m.targets = ["claud"]),
      (m) => (m.targets = ["codex", "codex"]),
      (m) => (m.targets = "codex"),
    ];
    for (const mutate of variants) {
      const m = structuredClone(good);
      mutate(m);
      setManifest(dir, m);
      const before = treeState(dir);
      for (const args of [["update"], ["update", "--dry-run"], ["update", "--restore"], ["target", "add", "claude", "--yes"], ["target", "remove", "codex"], ["uninstall", "--yes"], ["init", "--yes"]]) {
        const r = cli(args, dir);
        assert.equal(r.status, 1, `${args.join(" ")} with targets=${JSON.stringify(m.targets)}: ${r.stdout}`);
        assert.match(r.stderr, /invalid "targets" field/, args.join(" "));
        assert.deepEqual(treeState(dir), before, `${args.join(" ")} writes nothing`);
      }
      const doc = cli(["doctor"], dir);
      assert.equal(doc.status, 1, "doctor reports the invalid manifest");
      assert.match(doc.stdout + doc.stderr, /targets/);
    }
    setManifest(dir, good);
    assert.deepEqual(missingOf(dir), [], "every managed file is still on disk");
    assert.equal(cli(["update"], dir).status, 0, "a valid manifest works again");
  } finally {
    rm(dir);
  }
});

test("B19: invalid nested config/context fields are reported by name before anything is written", () => {
  const dir = tmpProject();
  try {
    initCodex(dir);
    const good = manifestOf(dir);
    const cases = [
      ["config.codexKeys", (m) => (m.config.codexKeys = 123)],
      ["config.codexKeys", (m) => (m.config.codexKeys = [1])],
      ["config.codexKeys", (m) => (m.config.codexKeys = [{ table: "features" }])],
      ["config.claudeAllow", (m) => (m.config.claudeAllow = "Bash(ls)")],
      ["config.claudeSettingsCreated", (m) => (m.config.claudeSettingsCreated = "yes")],
      ["context.claudePointer", (m) => (m.context.claudePointer = "yes")],
      ["context.agentsBlockHash", (m) => (m.context.agentsBlockHash = 7)],
      ["lastRunId", (m) => (m.lastRunId = 1)],
    ];
    for (const [field, mutate] of cases) {
      const m = structuredClone(good);
      mutate(m);
      setManifest(dir, m);
      const before = treeState(dir);
      for (const args of [["update", "--restore"], ["target", "add", "claude", "--yes"], ["uninstall", "--yes"]]) {
        const r = cli(args, dir);
        assert.equal(r.status, 1, `${field} / ${args.join(" ")}`);
        assert.ok(r.stderr.includes(`"${field}"`), `${field} is named: ${r.stderr}`);
        assert.deepEqual(treeState(dir), before, `${field} / ${args.join(" ")}: nothing written`);
      }
    }
    // The variant of the audit: `target add claude --yes` with codexKeys 123 wrote 210 files before aborting.
    assert.equal(has(dir, ".claude"), false);
    assert.equal(has(dir, "CLAUDE.md"), false);
    setManifest(dir, good);
    assert.deepEqual(missingOf(dir), []);
  } finally {
    rm(dir);
  }
});

test("B19: applySync validates the whole run before the first write (manifest object passed directly)", () => {
  const dir = tmpProject();
  try {
    initCodex(dir);
    const { manifest } = loadManifest(dir);
    manifest.config.codexKeys = 123; // bypasses loadManifest, as a library caller could
    const sync = computeSync({ projectDir: dir, targets: ["claude", "codex"], lang: "en", previousManifest: manifest });
    assert.ok(sync.plan.actions.length > 100, "the plan would add the Claude files");
    const before = treeState(dir);
    assert.throws(() => applySync(sync, { projectDir: dir, previousManifest: manifest, migrateClaude: true }), /config\.codexKeys/);
    assert.deepEqual(treeState(dir), before, "no file, no backup, no partial install");
  } finally {
    rm(dir);
  }
});

test("B11: uninstall with a damaged AGENTS.md marker fails before any removal, also in --dry-run", () => {
  const dir = tmpProject();
  try {
    const files = initCodex(dir);
    write(dir, "AGENTS.md", read(dir, "AGENTS.md").replace("<!-- REDEVKIT:END -->", ""));
    const before = treeState(dir);
    const dry = cli(["uninstall", "--dry-run"], dir);
    assert.equal(dry.status, 1, dry.stdout);
    assert.match(dry.stderr, /malformed REDEVKIT block/);
    const real = cli(["uninstall", "--yes"], dir);
    assert.equal(real.status, 1, real.stdout);
    assert.match(real.stderr, /malformed REDEVKIT block/);
    assert.match(real.stderr, /Nothing was changed/);
    assert.deepEqual(treeState(dir), before, "no file removed, no backup, manifest and config kept");
    assert.equal(files.filter((f) => has(dir, f)).length, files.length, `all ${files.length} managed files are still there`);

    // Fixed marker: the uninstall goes through.
    write(dir, "AGENTS.md", `${read(dir, "AGENTS.md").trimEnd()}\n\n<!-- REDEVKIT:END -->\n`);
    const ok = cli(["uninstall", "--yes"], dir);
    assert.equal(ok.status, 0, ok.stderr);
    assert.equal(has(dir, MANIFEST), false);
  } finally {
    rm(dir);
  }
});

test("B10: rollback refuses an incomplete or incoherent backup before touching anything, also in --dry-run", () => {
  const dir = tmpProject();
  try {
    initCodex(dir);
    const before0 = backupsOf(dir);
    assert.equal(cli(["target", "add", "claude", "--yes"], dir).status, 0);
    const id = newBackup(dir, before0);
    const bdir = path.join(dir, ".redevkit", "backups", id);
    fs.rmSync(path.join(bdir, "AGENTS.md"));
    const before = treeState(dir);
    for (const args of [["rollback", "--dry-run"], ["rollback"], ["rollback", "--backup", id]]) {
      const r = cli(args, dir);
      assert.equal(r.status, 1, `${args.join(" ")}: ${r.stdout}`);
      assert.match(r.stderr, new RegExp(`${id} is incomplete: AGENTS\\.md is missing`));
      assert.doesNotMatch(r.stdout, /restore AGENTS\.md/);
      assert.deepEqual(treeState(dir), before, `${args.join(" ")} changes nothing`);
    }

    // Incoherent metadata: the saved manifest no longer matches the state the backup records.
    fs.writeFileSync(path.join(bdir, "AGENTS.md"), "restored\n");
    const meta = JSON.parse(fs.readFileSync(path.join(bdir, "_backup.json"), "utf8"));
    fs.writeFileSync(path.join(bdir, "_backup.json"), JSON.stringify({ ...meta, files: "AGENTS.md" }));
    const r = cli(["rollback"], dir);
    assert.equal(r.status, 1);
    assert.match(r.stderr, /incoherent/);
    fs.writeFileSync(path.join(bdir, "_backup.json"), JSON.stringify({ ...meta, managedFiles: meta.managedFiles.slice(1) }));
    const r2 = cli(["rollback", "--dry-run"], dir);
    assert.equal(r2.status, 1);
    assert.match(r2.stderr, /managedFiles/);
    fs.writeFileSync(path.join(bdir, "_backup.json"), "{");
    const r3 = cli(["rollback", "--backup", id], dir);
    assert.equal(r3.status, 1);
    assert.match(r3.stderr, /_backup\.json is missing or unreadable/);
    assert.deepEqual(missingOf(dir), []);
  } finally {
    rm(dir);
  }
});

test("B02: rollback to an older backup restores the chain newest first and leaves Codex whole and no Claude", () => {
  const dir = tmpProject();
  try {
    const codexFiles = initCodex(dir);
    const configToml = read(dir, ".codex/config.toml");
    const agents = read(dir, "AGENTS.md");
    let seen = backupsOf(dir);
    assert.equal(cli(["target", "add", "claude", "--yes"], dir).status, 0);
    const addId = newBackup(dir, seen);
    seen = backupsOf(dir);
    const rem = cli(["target", "remove", "codex"], dir);
    assert.equal(rem.status, 0, rem.stderr);
    const removeId = newBackup(dir, seen);
    assert.equal(has(dir, ".codex/config.toml"), false);

    const dry = cli(["rollback", "--backup", addId, "--dry-run"], dir);
    assert.equal(dry.status, 0, dry.stderr);
    assert.ok(dry.stdout.includes(`${removeId} -> ${addId}`), dry.stdout);

    const rb = cli(["rollback", "--backup", addId], dir);
    assert.equal(rb.status, 0, rb.stderr + rb.stdout);
    const m = manifestOf(dir);
    assert.deepEqual(m.targets, ["codex"]);
    assert.deepEqual(Object.keys(m.files).sort(), codexFiles);
    assert.deepEqual(missingOf(dir), [], `all ${codexFiles.length} Codex files are present`);
    assert.ok(codexFiles.length > 200);
    assert.equal(has(dir, ".claude"), false, "no Claude files left");
    assert.equal(has(dir, "CLAUDE.md"), false);
    assert.equal(read(dir, ".codex/config.toml"), configToml);
    assert.equal(read(dir, "AGENTS.md"), agents);
    const st = JSON.parse(cli(["status", "--json"], dir).stdout);
    assert.deepEqual(st.missing, []);
    assert.equal(cli(["doctor"], dir).status, 0);
  } finally {
    rm(dir);
  }
});

test("rollback --backup takes an unambiguous id prefix and refuses an ambiguous one without writing", () => {
  const dir = tmpProject();
  try {
    initCodex(dir);
    let seen = backupsOf(dir);
    assert.equal(cli(["target", "add", "claude", "--yes"], dir).status, 0);
    const addId = newBackup(dir, seen);
    seen = backupsOf(dir);
    assert.equal(cli(["target", "remove", "codex"], dir).status, 0);
    const removeId = newBackup(dir, seen);

    const before = treeState(dir);
    const common = addId.slice(0, 9); // "YYYYMMDD-": shared by both backups
    assert.ok(removeId.startsWith(common));
    const amb = cli(["rollback", "--backup", common], dir);
    assert.equal(amb.status, 1);
    assert.match(amb.stderr + amb.stdout, new RegExp(`${addId}.*${removeId}|${removeId}.*${addId}`));
    assert.deepEqual(treeState(dir), before, "an ambiguous id changes nothing");

    const short = addId.slice(0, -2);
    assert.ok(!removeId.startsWith(short));
    const dry = cli(["rollback", "--backup", short, "--dry-run"], dir);
    assert.equal(dry.status, 0, dry.stderr);
    assert.ok(dry.stdout.includes(`${removeId} -> ${addId}`), dry.stdout);
  } finally {
    rm(dir);
  }
});

test("B02: a broken chain (a run with --no-backup) is refused without writing; the last run's backup is restored directly", () => {
  const dir = tmpProject();
  try {
    initCodex(dir);
    let seen = backupsOf(dir);
    assert.equal(cli(["target", "add", "claude", "--yes"], dir).status, 0);
    const addId = newBackup(dir, seen);
    // An update without backup: simulate an older install of one file, then update --no-backup.
    const skill = ".claude/skills/redevkit-status/SKILL.md";
    write(dir, skill, "old version\n");
    const m = manifestOf(dir);
    m.files[skill] = createHash("sha256").update("old version\n").digest("hex");
    setManifest(dir, m);
    seen = backupsOf(dir);
    assert.equal(cli(["update", "--no-backup"], dir).status, 0);
    assert.deepEqual(backupsOf(dir), seen, "no backup was taken");
    const before = treeState(dir);
    for (const args of [["rollback", "--backup", addId], ["rollback", "--backup", addId, "--dry-run"]]) {
      const r = cli(args, dir);
      assert.equal(r.status, 1, r.stdout);
      assert.match(r.stderr, /chain of backups down to it is broken/);
      assert.deepEqual(treeState(dir), before);
    }
    const def = cli(["rollback"], dir);
    assert.equal(def.status, 1);
    assert.match(def.stderr, /No backup undoes the last operation/);
    assert.deepEqual(treeState(dir), before);

    // Direct case: the backup of the last operation is restored as before.
    seen = backupsOf(dir);
    assert.equal(cli(["target", "remove", "claude"], dir).status, 0);
    const rb = cli(["rollback"], dir);
    assert.equal(rb.status, 0, rb.stderr);
    assert.deepEqual(manifestOf(dir).targets, ["claude", "codex"]);
    assert.deepEqual(missingOf(dir), []);
    // Rolling back again undoes the run before (the --no-backup update): refused, nothing written.
    const again = cli(["rollback"], dir);
    assert.equal(again.status, 1);
    assert.match(again.stderr, /redevkit rollback --backup pre-rollback-/, "points to undoing the rollback");
  } finally {
    rm(dir);
  }
});

test("B02: after a restore every file of the restored manifest must exist (post-check)", () => {
  const dir = tmpProject();
  try {
    initCodex(dir);
    const seen = backupsOf(dir);
    assert.equal(cli(["target", "add", "claude", "--yes"], dir).status, 0);
    const id = newBackup(dir, seen);
    // A backup whose saved manifest lists a file nobody can restore (coherent metadata, wrong content).
    const bdir = path.join(dir, ".redevkit", "backups", id);
    const saved = JSON.parse(fs.readFileSync(path.join(bdir, ".redevkit", "manifest.json"), "utf8"));
    saved.files["ghost/never-installed.md"] = "a".repeat(64);
    fs.writeFileSync(path.join(bdir, ".redevkit", "manifest.json"), JSON.stringify(saved));
    const meta = JSON.parse(fs.readFileSync(path.join(bdir, "_backup.json"), "utf8"));
    meta.managedFiles.push("ghost/never-installed.md");
    fs.writeFileSync(path.join(bdir, "_backup.json"), JSON.stringify(meta));
    const r = cli(["rollback"], dir);
    assert.equal(r.status, 1, r.stdout);
    assert.match(r.stderr, /1 file\(s\) of the restored manifest do not exist on disk \(e\.g\. ghost\/never-installed\.md\)/);
    assert.match(r.stderr, /redevkit update --restore/);
    assert.match(r.stderr, /redevkit rollback --backup pre-rollback-/);
  } finally {
    rm(dir);
  }
});

test("B14: two simultaneous target removals end as the serial run (one succeeds, one refuses)", async () => {
  for (let round = 0; round < 2; round += 1) {
    const dir = tmpProject();
    try {
      assert.equal(cli(["init", "--target", "both", "--lang", "en", "--yes"], dir).status, 0);
      const [a, b] = await Promise.all([cliAsync(["target", "remove", "claude"], dir), cliAsync(["target", "remove", "codex"], dir)]);
      const statuses = [a.status, b.status].sort();
      assert.deepEqual(statuses, [0, 2], `round ${round}: ${a.stdout}${a.stderr} | ${b.stdout}${b.stderr}`);
      assert.match(a.status === 2 ? a.stderr : b.stderr, /Cannot remove the last target/);
      const m = manifestOf(dir);
      assert.equal(m.targets.length, 1);
      assert.deepEqual(missingOf(dir), [], `round ${round}: the remaining target is whole`);
      assert.equal(has(dir, LOCK), false, "the lock is released");
      assert.equal(new Set(backupsOf(dir)).size, backupsOf(dir).length);
    } finally {
      rm(dir);
    }
  }
});

test("B14: a live lock makes a second command wait and then fail with nothing changed; an orphan lock is taken over", () => {
  const dir = tmpProject();
  try {
    initCodex(dir);
    // Held by a live process (this test runner).
    write(dir, LOCK, JSON.stringify({ pid: process.pid, host: os.hostname(), command: "update", startedAt: new Date().toISOString() }));
    const before = treeState(dir);
    const t0 = Date.now();
    const r = cli(["target", "add", "claude", "--yes"], dir, { REDEVKIT_LOCK_WAIT_MS: "600" });
    assert.equal(r.status, 1, r.stdout);
    assert.ok(Date.now() - t0 >= 500, "it waited before giving up");
    assert.match(r.stderr, /Another REDEVKIT operation is running in this project \(pid \d+, update/);
    assert.match(r.stderr, /redevkit\.lock/);
    assert.deepEqual(treeState(dir), before, "nothing changed and the other process's lock is kept");
    assert.equal(cli(["update", "--dry-run"], dir).status, 0, "read-only runs do not need the lock");

    // Orphan: the owner process no longer exists.
    const dead = spawnSync(process.execPath, ["-e", ""]).pid;
    write(dir, LOCK, JSON.stringify({ pid: dead, host: os.hostname(), command: "update", startedAt: new Date().toISOString() }));
    const ok = cli(["target", "add", "claude", "--yes"], dir, { REDEVKIT_LOCK_WAIT_MS: "600" });
    assert.equal(ok.status, 0, ok.stderr);
    assert.equal(has(dir, LOCK), false);

    // Orphan by age: a lock nobody refreshed for longer than the limit.
    write(dir, LOCK, JSON.stringify({ pid: process.pid, host: "another-host", command: "update", startedAt: "2000-01-01T00:00:00.000Z" }));
    const old = new Date(Date.now() - 60 * 60 * 1000);
    fs.utimesSync(path.join(dir, ...LOCK.split("/")), old, old);
    const ok2 = cli(["target", "remove", "claude"], dir, { REDEVKIT_LOCK_WAIT_MS: "600" });
    assert.equal(ok2.status, 0, ok2.stderr);
    assert.equal(has(dir, LOCK), false);
    assert.deepEqual(missingOf(dir), []);
  } finally {
    rm(dir);
  }
});

test("B14: a refused first init leaves no .redevkit directory behind", () => {
  const dir = tmpProject();
  try {
    const r = cli(["init"], dir); // no TTY and no --yes: refused
    assert.equal(r.status, 2);
    assert.deepEqual(fs.readdirSync(dir), []);
  } finally {
    rm(dir);
  }
});

test("N02: run ids are unique within one millisecond and across processes, and sort chronologically", () => {
  const now = new Date();
  const ids = Array.from({ length: 2000 }, () => createRunId(now));
  assert.equal(new Set(ids).size, ids.length);
  assert.deepEqual([...ids].sort(), ids, "same millisecond: the order of the calls is kept");
  const later = createRunId(new Date(now.getTime() + 1));
  assert.ok(later > ids[ids.length - 1]);

  // Two processes generating ids at the same moment never collide.
  const gen = `import { createRunId } from ${JSON.stringify(new URL("../src/core/managed-tree.js", import.meta.url).href)};
const d = new Date(Date.UTC(2026, 10, 25, 7, 51, 48, 680));
process.stdout.write(Array.from({ length: 500 }, () => createRunId(d)).join("\\n"));`;
  const runs = [0, 1].map(() => spawnSync(process.execPath, ["--input-type=module", "-e", gen], { encoding: "utf8", cwd: ROOT }));
  const all = runs.flatMap((r) => r.stdout.split("\n"));
  assert.equal(all.length, 1000);
  assert.equal(new Set(all).size, 1000);

  // A backup directory is created exclusively: an id in use is an error, never a merge.
  const dir = tmpProject();
  try {
    write(dir, "a.md", "one");
    createBackup({ projectDir: dir, files: ["a.md"], runId: "same-id" });
    write(dir, "a.md", "two");
    assert.throws(() => createBackup({ projectDir: dir, files: ["a.md"], runId: "same-id" }), /already in use/);
    assert.equal(read(dir, ".redevkit/backups/same-id/a.md"), "one");
  } finally {
    rm(dir);
  }
});
