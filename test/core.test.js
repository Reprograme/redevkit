import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { parse as tomlParse } from "smol-toml";
import { appendMigratedNotes, isPointer, migratableContent, removeAgentsBlock, upsertAgentsBlock, BEGIN, END } from "../src/core/context-files.js";
import { asList, parseFrontmatter, stringifyFrontmatter } from "../src/core/frontmatter.js";
import { atomicWrite, cleanupPendingTemps, crossesLink, isSafeRelative, pendingTempCount, removeInside, writeInside } from "../src/core/fsutil.js";
import { applyPlan, createBackup, createPlan, listBackups, nextManifestFiles, restoreBackup } from "../src/core/managed-tree.js";
import { loadManifest, newManifest, writeManifest } from "../src/core/manifest.js";
import { mergeClaudeSettings, mergeCodexConfig, unmergeClaudeSettings, unmergeCodexConfig } from "../src/core/runtime-config.js";
import { compare } from "../src/core/semver.js";
import { personaFile } from "../src/core/targets/codex.js";
import { has, read, rm, tmpProject, write } from "./helpers.js";

test("frontmatter: CRLF, BOM, quotes, lists, nested maps (H5)", () => {
  const src = '\uFEFF---\r\nname: x\r\ndescription: "A: b # c"\r\nlist: [a, "b c"]\r\nblock:\r\n  - one\r\n  - two\r\nmetadata:\r\n  short-description: Hi\r\nflag: false # comment\r\n---\r\nBody\r\n';
  const { data, body, errors } = parseFrontmatter(src);
  assert.deepEqual(errors, []);
  assert.equal(data.name, "x");
  assert.equal(data.description, "A: b # c");
  assert.deepEqual(data.list, ["a", "b c"]);
  assert.deepEqual(data.block, ["one", "two"]);
  assert.deepEqual(data.metadata, { "short-description": "Hi" });
  assert.equal(data.flag, false);
  assert.equal(body.trim(), "Body");
  assert.deepEqual(asList("a, b"), ["a", "b"]);
});

test("frontmatter: stringify quotes only when needed and round-trips", () => {
  const text = stringifyFrontmatter([["name", "a"], ["description", "[internal] x: y"], ["flag", false], ["paths", ["**/*.ts"]], ["metadata", { "short-description": "S" }]]);
  const { data } = parseFrontmatter(`${text}\n`);
  assert.equal(data.description, "[internal] x: y");
  assert.equal(data.flag, false);
  assert.deepEqual(data.paths, ["**/*.ts"]);
  assert.equal(data.metadata["short-description"], "S");
  assert.match(text, /^name: a$/m);
});

test("frontmatter: reports duplicate keys and unterminated blocks", () => {
  assert.ok(parseFrontmatter("---\na: 1\na: 2\n---\n").errors.length > 0);
  assert.ok(parseFrontmatter("---\na: 1\n").errors.length > 0);
});

test("safe relative paths reject traversal and absolute paths", () => {
  for (const bad of ["../x", "/etc/passwd", "C:/x", "a//b", "a/./b", ""]) assert.equal(isSafeRelative(bad), false, bad);
  assert.equal(isSafeRelative(".claude/skills/a/SKILL.md"), true);
});

test("atomic write leaves no temp files and SIGINT cleanup removes in-flight temps (C2)", () => {
  const dir = tmpProject();
  try {
    const target = path.join(dir, "sub", "file.txt");
    atomicWrite(target, "hello");
    assert.equal(fs.readFileSync(target, "utf8"), "hello");
    assert.deepEqual(fs.readdirSync(path.dirname(target)), ["file.txt"]);
    assert.equal(pendingTempCount(), 0);
    cleanupPendingTemps();
  } finally {
    rm(dir);
  }
});

test("symlinks are never written or deleted through (C3, Y3, Y9)", (t) => {
  const dir = tmpProject();
  const outside = tmpProject("fora");
  try {
    fs.writeFileSync(path.join(outside, "victim.txt"), "keep");
    try {
      fs.symlinkSync(outside, path.join(dir, "link"), "junction");
    } catch (err) {
      t.skip(`cannot create links here (${err.code})`);
      return;
    }
    assert.equal(crossesLink(dir, path.join(dir, "link", "victim.txt")), true);
    assert.throws(() => writeInside(dir, "link/victim.txt", "x"), /symbolic link/);
    assert.throws(() => removeInside(dir, "link/victim.txt"), /symbolic link/);
    assert.equal(fs.readFileSync(path.join(outside, "victim.txt"), "utf8"), "keep");
  } finally {
    rm(dir);
    rm(outside);
  }
});

test("manifest is written atomically and validated on load", () => {
  const dir = tmpProject();
  try {
    const m = newManifest({ version: "1.0.0", targets: ["claude"], lang: "en", runId: "r" });
    m.files = { "b.md": "a".repeat(64), "a.md": "b".repeat(64) };
    writeManifest(dir, m);
    const { manifest } = loadManifest(dir);
    assert.deepEqual(Object.keys(manifest.files), ["a.md", "b.md"]);
    write(dir, ".redevkit/manifest.json", JSON.stringify({ ...m, files: { "../x": "a".repeat(64) } }));
    assert.match(loadManifest(dir).error, /unsafe/);
    write(dir, ".redevkit/manifest.json", "{not json");
    assert.match(loadManifest(dir).error, /not valid JSON/);
  } finally {
    rm(dir);
  }
});

test("managed tree: three-way decision table", () => {
  const dir = tmpProject();
  try {
    const h = (s) => createPlan({ projectDir: dir, incoming: new Map([["x", s]]), previous: {} }).incomingHashes.x;
    write(dir, "same.md", "v1");
    write(dir, "localonly.md", "mine");
    write(dir, "both.md", "mine");
    write(dir, "gone.md", "v1");
    write(dir, "userfile.md", "user");
    const previous = { "same.md": h("v1"), "localonly.md": h("v1"), "both.md": h("v1"), "gone.md": h("v1"), "deleted.md": h("v1") };
    const incoming = new Map([
      ["same.md", "v2"],
      ["localonly.md", "v1"],
      ["both.md", "v2"],
      ["deleted.md", "v1"],
      ["new.md", "n"],
      ["userfile.md", "upstream"],
    ]);
    const plan = createPlan({ projectDir: dir, incoming, previous, hasManifest: true });
    const byFile = (list) => list.map((x) => x.file ?? x).sort();
    assert.deepEqual(byFile(plan.actions.filter((a) => a.type === "update")), ["same.md"]);
    assert.deepEqual(byFile(plan.actions.filter((a) => a.type === "add")), ["new.md"]);
    assert.deepEqual(byFile(plan.actions.filter((a) => a.type === "delete")), ["gone.md"]);
    assert.deepEqual(byFile(plan.conflicts), ["both.md", "userfile.md"]);
    assert.deepEqual(byFile(plan.preserved), ["deleted.md", "localonly.md"]);
    applyPlan({ projectDir: dir, plan, incoming, runId: "run1" });
    assert.equal(read(dir, "same.md"), "v2");
    assert.equal(read(dir, "both.md"), "mine");
    assert.equal(read(dir, ".redevkit/conflicts/run1/both.md"), "v2");
    assert.equal(has(dir, "gone.md"), false);
    const files = nextManifestFiles(plan, previous);
    assert.equal(files["both.md"], previous["both.md"], "conflict keeps the old baseline");
    assert.equal(files["userfile.md"], undefined, "user-owned file stays unmanaged");
    const forced = createPlan({ projectDir: dir, incoming, previous, hasManifest: true, force: true });
    assert.ok(forced.actions.some((a) => a.file === "both.md" && a.type === "update"));
  } finally {
    rm(dir);
  }
});

test("backup and restore round-trip, with a safety backup", () => {
  const dir = tmpProject();
  try {
    write(dir, "a.md", "old");
    createBackup({ projectDir: dir, files: ["a.md", "missing.md"], runId: "b1" });
    write(dir, "a.md", "new");
    write(dir, "added.md", "added later");
    const r = restoreBackup({ projectDir: dir, backupId: "b1", currentManaged: ["a.md", "added.md"], runId: "r1" });
    assert.equal(read(dir, "a.md"), "old");
    assert.equal(has(dir, "added.md"), false);
    assert.ok(r.safetyBackupDir);
    assert.equal(read(dir, ".redevkit/backups/pre-rollback-r1/a.md"), "new");
    assert.equal(listBackups(dir).length, 2);
  } finally {
    rm(dir);
  }
});

test("AGENTS.md block: insert, update and remove are idempotent", () => {
  const created = upsertAgentsBlock(null, "Block v1", "pt-BR");
  assert.ok(created.startsWith(BEGIN));
  assert.match(created, /## Notas do projeto/);
  assert.equal(upsertAgentsBlock(created, "Block v1", "pt-BR"), created);
  const user = "# Mine\n\nKeep me.\n";
  const inserted = upsertAgentsBlock(user, "Block v1", "en");
  assert.ok(inserted.includes("Keep me."));
  const updated = upsertAgentsBlock(inserted, "Block v2", "en");
  assert.ok(updated.includes("Block v2") && !updated.includes("Block v1"));
  assert.equal(updated.split(END).length, 2);
  const removed = removeAgentsBlock(updated);
  assert.equal(removed.trim(), user.trim());
  assert.throws(() => upsertAgentsBlock(`${END}\n${BEGIN}`, "x", "en"), /malformed/);
});

test("CLAUDE.md migration helpers", () => {
  const pointers = ["@AGENTS.md\n\nLeia o AGENTS.md.\n", "@AGENTS.md\n\nRead AGENTS.md.\n"];
  assert.equal(isPointer("@AGENTS.md\r\n\r\nLeia o AGENTS.md.", pointers), true);
  assert.equal(isPointer("# Rules\nUse tabs", pointers), false);
  assert.equal(migratableContent("@AGENTS.md\n# Rules\n@docs/x.md\n"), "# Rules\n@docs/x.md");
  const out = appendMigratedNotes("block\n", "# Rules", "pt-BR", "2026-11-06");
  assert.match(out, /## Notas do projeto \(migrado de CLAUDE.md em 2026-11-06\)\n\n# Rules/);
});

test("settings.json merge: absent, existing, invalid, user entries (D51)", () => {
  const entries = ["Bash(git status *)", "Bash(npm test *)"];
  const created = mergeClaudeSettings(null, entries);
  assert.equal(created.ok && created.created, true);
  assert.deepEqual(JSON.parse(created.text).permissions.allow, entries);
  const existing = JSON.stringify({ model: "x", permissions: { allow: ["Bash(npm test *)", "Read"], deny: ["Bash(rm *)"] } });
  const merged = mergeClaudeSettings(existing, entries);
  const data = JSON.parse(merged.text);
  assert.deepEqual(merged.added, ["Bash(git status *)"]);
  assert.equal(data.model, "x");
  assert.deepEqual(data.permissions.deny, ["Bash(rm *)"]);
  assert.equal(mergeClaudeSettings("{ invalid", entries).ok, false);
  assert.equal(mergeClaudeSettings('{"permissions": []}', entries).ok, false);
  const un = unmergeClaudeSettings(merged.text, merged.added);
  assert.deepEqual(JSON.parse(un.text).permissions.allow, ["Bash(npm test *)", "Read"]);
  assert.equal(unmergeClaudeSettings(created.text, entries, { deleteIfEmpty: true }).text, null);
});

test("config.toml merge: absent, existing with comments, user value, invalid (D51)", () => {
  const entries = [
    { table: "features", key: "default_mode_request_user_input", value: "true" },
    { table: "skills", key: "max_context_tokens", value: "10000" },
  ];
  const fresh = mergeCodexConfig(null, entries);
  assert.equal(fresh.ok, true);
  assert.deepEqual(JSON.parse(JSON.stringify(tomlParse(fresh.text))), { features: { default_mode_request_user_input: true }, skills: { max_context_tokens: 10000 } });
  const user = '# my config\nmodel = "gpt"\n\n[features]\n# keep this comment\nweb_search = true\n\n[skills]\nmax_context_tokens = 4000\n';
  const merged = mergeCodexConfig(user, entries);
  assert.equal(merged.ok, true);
  assert.match(merged.text, /# keep this comment/);
  assert.equal(tomlParse(merged.text).skills.max_context_tokens, 4000, "user value wins");
  assert.equal(merged.kept[0].key, "max_context_tokens");
  assert.equal(tomlParse(merged.text).features.default_mode_request_user_input, true);
  assert.equal(mergeCodexConfig(merged.text, entries).changed, false, "idempotent");
  const un = unmergeCodexConfig(merged.text);
  assert.equal(un.text, user.replace(/\n$/, "") + "\n");
  assert.equal(unmergeCodexConfig(fresh.text).text, null);
  assert.equal(mergeCodexConfig("[broken", entries).ok, false);
});

test("persona TOML round-trips bodies with ''' and quotes (H6)", () => {
  const body = "Line with ''' and \"\"\" and \\ backslash\nSecond line\n";
  const text = personaFile({ name: "p", description: 'Says "hi"' }, body);
  const parsed = tomlParse(text);
  assert.equal(parsed.name, "p");
  assert.equal(parsed.description, 'Says "hi"');
  assert.equal(parsed.developer_instructions, body);
});

test("semver compare (C1)", () => {
  assert.equal(compare("1.10.0", "1.9.0"), 1);
  assert.equal(compare("1.0.0-rc.1", "1.0.0"), -1);
  assert.equal(compare("1.0.0-rc.2", "1.0.0-rc.10"), -1);
  assert.equal(compare("v2.0.0", "2.0.0"), 0);
  assert.throws(() => compare("x", "1.0.0"));
});
