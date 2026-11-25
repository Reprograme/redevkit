#!/usr/bin/env node
// Coverage matrix of an E2E round: which commands, phases, personas, knowledge skills, audits and
// gates each runtime actually went through. Only what the agent invoked or opened counts (Claude
// tool calls, Codex shell commands and the step prompts), never the text of a file it read, so a
// skill that lists every persona path does not mark them all as covered. Gates come from the
// passing checks of each run's result.json.
// Usage: node e2e/coverage.mjs <roundDir> [<roundDir>...] [--out <file>]
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const KIT = path.join(HERE, "..", "kit");
const names = (dir, strip = "") => fs.readdirSync(path.join(KIT, dir)).map((f) => f.replace(strip, "")).filter((f) => !f.endsWith(".md") || strip).sort();

export const INVENTORY = {
  commands: [...names("commands"), "redevkit-memanager"],
  phases: names("phases"),
  personas: names("personas", /\.md$/),
  skills: names("skills"),
  audits: fs.readdirSync(path.join(KIT, "audits")).filter((f) => f.endsWith(".py") && !["audit_common.py", "validation_runner.py"].includes(f)).sort(),
  gates: ["G1", "G2", "G3", "G4", "G5", "G6", "G7"],
};

// A gate counts as exercised when a run passed a check that proves it.
const GATE_CHECKS = {
  G1: /constitution has Test-First/,
  G2: /specs\/001-\*\/ has spec, plan, tasks|spec delta \+ tasks/,
  G3: /g3: the agent stopped at G3/,
  G4: /g4: the agent stopped at G4/,
  G5: /test-auto-g5: the agent stopped at G5|G5: active\.md Test cycle records G5 reached/,
  G6: /deploy report \.redevkit\/deploys\/\*-staging\.md with outcome succeeded|no deploy without the user \(G6\)/,
  G7: /archive\/ created and memory-bank\/ archived/,
};

const events = (file) =>
  fs
    .readFileSync(file, "utf8")
    .split("\n")
    .flatMap((l) => {
      if (!l.startsWith("{")) return [];
      try {
        return [JSON.parse(l)];
      } catch {
        return [];
      }
    });

/** The strings that show what the agent did in one transcript: prompt, tool inputs, shell commands. */
export const actions = (file) => {
  const text = fs.readFileSync(file, "utf8");
  const out = [/^# prompt: (\S+)/.exec(text)?.[1] ?? ""];
  for (const e of events(file)) {
    if (e.type === "assistant") {
      for (const c of e.message?.content ?? []) {
        if (c.type !== "tool_use") continue;
        const i = c.input ?? {};
        out.push([c.name, i.skill, i.subagent_type, i.file_path, i.path, i.pattern, i.command].filter(Boolean).join(" "));
      }
    }
    if (e.type === "item.completed" && e.item?.type === "command_execution") out.push(String(e.item.command ?? ""));
  }
  return out.join("\n").replace(/\\\\?/g, "/");
};

const esc = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

/** Which inventory items one transcript touched. */
export const touched = (file) => {
  const a = actions(file);
  const hit = (re) => re.test(a);
  return {
    commands: INVENTORY.commands.filter((n) => hit(new RegExp(`(^|[/$\\s])${esc(n)}(\\b|$)`, "m"))),
    phases: INVENTORY.phases.filter((n) => hit(new RegExp(`skills/${esc(n)}/|Skill ${esc(n)}\\b`))),
    personas: INVENTORY.personas.filter((n) => hit(new RegExp(`agents/${esc(n)}\\.(md|toml)|personas/${esc(n)}\\.md|(Agent|Task) ${esc(n)}\\b`))),
    skills: INVENTORY.skills.filter((n) => hit(new RegExp(`skills/${esc(n)}/|Skill ${esc(n)}\\b`))),
    audits: INVENTORY.audits.filter((n) => hit(new RegExp(`${esc(n)}\\b`))),
  };
};

const main = () => {
  const args = process.argv.slice(2);
  const oi = args.indexOf("--out");
  const outFile = oi >= 0 ? args.splice(oi, 2)[1] : null;
  const rounds = args.map((r) => path.resolve(r));
  const cover = { claude: {}, codex: {} };
  const add = (rt, kind, item, where) => {
    const k = `${kind}:${item}`;
    (cover[rt][k] ??= new Set()).add(where);
  };
  const runs = [];
  for (const round of rounds) {
    for (const id of fs.readdirSync(round)) {
      const dir = path.join(round, id);
      const m = /^([A-Z])-(claude|codex)/.exec(id);
      if (!m || !fs.statSync(dir).isDirectory()) continue;
      const [, scenario, rt] = m;
      let result = null;
      try {
        result = JSON.parse(fs.readFileSync(path.join(dir, "result.json"), "utf8"));
      } catch {
        // run unfinished
      }
      runs.push({ id, round: path.basename(round), passed: result?.passed ?? null, verdict: result?.verdict ?? null });
      for (const f of fs.readdirSync(dir).filter((f) => f.endsWith(".jsonl"))) {
        const t = touched(path.join(dir, f));
        for (const [kind, items] of Object.entries(t)) for (const item of items) add(rt, kind, item, scenario);
      }
      // Harness-run audits (scenario G): every check of the installed verify_all.py report.
      for (const r of result?.results ?? []) {
        if (/verify_all\.py ran all 17 checks/.test(r.name) && r.ok) for (const a of INVENTORY.audits) if (!["code_state.py", "checklist.py", "verify_all.py"].includes(a)) add(rt, "audits", a, `${scenario}(harness)`);
        if (/checklist\.py and code_state\.py ran/.test(r.name) && r.ok) for (const a of ["checklist.py", "code_state.py", "verify_all.py"]) add(rt, "audits", a, `${scenario}(harness)`);
        for (const [gate, re] of Object.entries(GATE_CHECKS)) if (re.test(r.name) && r.ok) add(rt, "gates", gate, scenario);
      }
    }
  }
  const lines = ["# E2E coverage", "", `Rounds: ${rounds.map((r) => path.basename(r)).join(", ")}`, "", "| Run | Verdict |", "| --- | --- |"];
  for (const r of runs.sort((a, b) => a.id.localeCompare(b.id))) lines.push(`| ${r.round}/${r.id} | ${r.passed === null ? "unfinished" : r.verdict ?? (r.passed ? "PASS" : "FAIL")} |`);
  const summary = [];
  for (const [kind, items] of Object.entries(INVENTORY)) {
    lines.push("", `## ${kind} (${items.length})`, "", "| Item | Claude | Codex |", "| --- | --- | --- |");
    const counts = { claude: 0, codex: 0 };
    for (const item of items) {
      const cell = (rt) => {
        const s = cover[rt][`${kind}:${item}`];
        if (s) counts[rt] += 1;
        return s ? [...s].sort().join(" ") : "—";
      };
      lines.push(`| \`${item}\` | ${cell("claude")} | ${cell("codex")} |`);
    }
    summary.push(`| ${kind} | ${counts.claude}/${items.length} | ${counts.codex}/${items.length} |`);
  }
  lines.splice(4, 0, "| Kind | Claude | Codex |", "| --- | --- | --- |", ...summary, "");
  const md = `${lines.join("\n")}\n`;
  if (outFile) fs.writeFileSync(outFile, md);
  console.log(md);
};

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) main();
