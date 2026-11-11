#!/usr/bin/env node
// REDEVKIT E2E (PLANO §15.2): 2 scenarios × 2 runtimes, real `claude -p` and `codex exec`.
// The work dir uses the long Windows path (realpath): Claude Code refuses writes through 8.3
// short names such as RICARD~1.
// Usage: node e2e/run.mjs --scenario A|B --runtime claude|codex [--out <dir>] [--work <dir>]
//        node e2e/run.mjs --check <workDir> --scenario A|B --runtime claude|codex   (checks only)
import { spawn, spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { which } from "../src/commands/doctor.js";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "..");
const BIN = path.join(ROOT, "bin", "redevkit.js");

const arg = (name, def = null) => {
  const i = process.argv.indexOf(`--${name}`);
  return i > 0 ? process.argv[i + 1] : def;
};

const NONINTERACTIVE =
  "Execução não interativa (E2E): não há usuário para responder. Assuma as recomendações e registre-as como suposições.";

export const SCENARIOS = {
  A: {
    title: "Projeto novo: jogo de nave 2D para web",
    steps: [
      { id: "new", cmd: "redevkit-new", text: `projeto novo: jogo de nave 2D para web. ${NONINTERACTIVE} Eu aprovo a constituição proposta (gate G1).` },
      { id: "plan", cmd: "redevkit-plan", text: `--auto mover, atirar, pontuar. ${NONINTERACTIVE} Eu aprovo o plano (gate G2); pare depois da aprovação, sem implementar.` },
      { id: "create", cmd: "redevkit-create", text: `Plano aprovado (G2). ${NONINTERACTIVE} Implemente a feature ativa; pare antes do redevkit-test.` },
      { id: "test", cmd: "redevkit-test", text: `${NONINTERACTIVE}` },
    ],
  },
  B: {
    title: "Projeto existente: API com memory-bank, CLAUDE.md e bug latente",
    fixture: "api-b",
    steps: [
      { id: "new", cmd: "redevkit-new", text: `projeto existente. Há memória legada em memory-bank/: escolho importar e arquivar (gate G7). ${NONINTERACTIVE} Eu aprovo a constituição proposta (gate G1).` },
      { id: "enhance", cmd: "redevkit-enhance", text: `adicionar endpoint GET /health que responde {"status":"ok","uptime":<segundos>}. ${NONINTERACTIVE} Eu aprovo o plano da mudança. Pare antes do redevkit-test.` },
      { id: "test", cmd: "redevkit-test", text: `Gere também os testes que faltam para comportamentos existentes sem cobertura registrados na memória (o /about não tem testes). ${NONINTERACTIVE} Não corrija código neste comando.` },
      { id: "debug", cmd: "redevkit-debug", text: `corrija as falhas do último test-report. ${NONINTERACTIVE} Pare antes do redevkit-verify.` },
      { id: "verify", cmd: "redevkit-verify", text: `${NONINTERACTIVE}` },
    ],
  },
};

/** Steps used with --resume, following the handoffs of a red test (D26). */
const EXTRA_STEPS = {
  debug: { id: "debug", cmd: "redevkit-debug", text: `corrija as falhas do último test-report. ${NONINTERACTIVE} Pare antes do redevkit-verify.` },
  verify: { id: "verify", cmd: "redevkit-verify", text: `${NONINTERACTIVE}` },
  test: { id: "test", cmd: "redevkit-test", text: `${NONINTERACTIVE}` },
};

const CLAUDE_TOOLS = [
  "Read", "Write", "Edit", "Glob", "Grep", "Skill", "Agent", "TodoWrite",
  "Bash(npm *)", "Bash(npx *)", "Bash(node *)", "Bash(mv memory-bank *)", "PowerShell(Move-Item memory-bank *)", "Bash(python *)", "Bash(py *)", "Bash(ls *)", "Bash(mkdir *)", "Bash(cat *)", "Bash(cd *)",
  "Bash(git status *)", "Bash(git diff *)", "Bash(git log *)", "Bash(git rev-parse *)", "Bash(git branch *)", "Bash(git hash-object *)", "Bash(git show *)",
  "PowerShell(npm *)", "PowerShell(node *)", "PowerShell(python *)", "PowerShell(git status *)", "PowerShell(git diff *)", "PowerShell(git rev-parse *)",
];

const runtimeCommand = (runtime, workDir, prompt) => {
  if (runtime === "claude") {
    const exe = which("claude");
    if (!exe) throw new Error("claude not found on PATH");
    return [exe, ["-p", prompt, "--output-format", "stream-json", "--verbose", "--permission-mode", "acceptEdits", "--allowedTools", ...CLAUDE_TOOLS]];
  }
  const exe = which("codex");
  if (!exe) throw new Error("codex not found on PATH");
  return [exe, ["exec", "--sandbox", "workspace-write", "--skip-git-repo-check", "--json", "-c", "sandbox_workspace_write.network_access=true", "-C", workDir, prompt]];
};

const runStep = (runtime, workDir, step, logFile, timeoutMs) =>
  new Promise((resolve) => {
    const invoke = runtime === "claude" ? `/${step.cmd}` : `$${step.cmd}`;
    const prompt = `${invoke} ${step.text}`.trim();
    const [exe, args] = runtimeCommand(runtime, workDir, prompt);
    const out = fs.createWriteStream(logFile);
    out.write(`# prompt: ${prompt}\n`);
    const started = Date.now();
    const child = spawn(exe, args, { cwd: workDir, env: { ...process.env, CI: "1" }, stdio: ["ignore", "pipe", "pipe"] });
    child.stdout.pipe(out, { end: false });
    child.stderr.pipe(out, { end: false });
    const timer = setTimeout(() => child.kill(), timeoutMs);
    let finished = false;
    const finish = (code, error) => {
      if (finished) return; // 'close' may follow 'error'
      finished = true;
      clearTimeout(timer);
      out.end(error ? `\n# spawn error: ${error}\n` : undefined);
      resolve({ id: step.id, code, ...(error ? { error } : {}), seconds: Math.round((Date.now() - started) / 1000) });
    };
    // Without this listener a spawn failure (ENOENT, EACCES…) is an uncaught 'error' event that
    // kills the runner instead of being recorded as a failed step.
    child.on("error", (err) => finish(null, err.message));
    child.on("close", (code) => finish(code));
  });

const git = (cwd, args) => spawnSync("git", args, { cwd, encoding: "utf8" });

const copyDir = (src, dst) => fs.cpSync(src, dst, { recursive: true });

const filesUnder = (dir, base = dir) => {
  if (!fs.existsSync(dir)) return [];
  const out = [];
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    if (e.name === "node_modules" || e.name === ".git") continue;
    const abs = path.join(dir, e.name);
    if (e.isDirectory()) out.push(...filesUnder(abs, base));
    else out.push(path.relative(base, abs).split(path.sep).join("/"));
  }
  return out;
};

/** Verdicts of the dated runs, in order: "## Run|Execução YYYY-MM-DD HH:MM — <verdict>". */
export const runVerdicts = (text) =>
  [...String(text).matchAll(/^##\s+(?:Run|Execução)\b[^\n]*?[—-]\s*([A-Za-z+-]+)\s*$/gm)].map((m) => m[1]);

const readIf = (p) => (fs.existsSync(p) ? fs.readFileSync(p, "utf8") : "");

const DESTRUCTIVE = [
  /rm\s+-rf?\s+(\/|~|\*|\.\s|C:)/i,
  /git\s+push\s+(-f|--force)/i,
  /git\s+reset\s+--hard/i,
  /git\s+clean\s+-[a-z]*f/i,
  /drop\s+(table|database)/i,
  /format\s+[a-z]:/i,
  /Remove-Item[^\n"]*-Recurse[^\n"]*(C:\\|~|\$HOME)/i,
  /mkfs\./i,
];

/** Acceptance checks per scenario (§15.2). Returns [{name, ok, detail}]. */
export const check = ({ scenario, workDir, transcripts, commitsBefore }) => {
  const res = [];
  const ok = (name, cond, detail = "") => res.push({ name, ok: Boolean(cond), detail });
  const mem = (f) => readIf(path.join(workDir, ".redevkit", "memory", f));
  const specs = fs.existsSync(path.join(workDir, "specs")) ? fs.readdirSync(path.join(workDir, "specs")).filter((d) => /^\d{3}-/.test(d)) : [];
  const feature = specs.sort()[0];
  const fdir = feature ? path.join(workDir, "specs", feature) : null;
  const doc = (f) => (fdir ? readIf(path.join(fdir, f)) : "");

  const doctor = spawnSync(process.execPath, [BIN, "doctor", "--json"], { cwd: workDir, encoding: "utf8" });
  let doctorReport = {};
  try {
    doctorReport = JSON.parse(doctor.stdout);
  } catch {
    // keep empty
  }
  const doctorErrors = (doctorReport.issues ?? []).filter((i) => i.level === "error");
  ok("redevkit doctor passes", doctor.status === 0, doctorErrors.map((i) => `${i.file}: ${i.message}`).join("; "));

  const core = ["MEMORY.md", "constitution.md", "project.md", "system.md", "tech.md", "active.md", "changelog.md", "user.md"];
  ok("memory complete", core.every((f) => fs.existsSync(path.join(workDir, ".redevkit", "memory", f))), core.filter((f) => !fs.existsSync(path.join(workDir, ".redevkit", "memory", f))).join(", "));
  ok("constitution has Test-First", /test[- ]first|TDD\*\*:\s*required/i.test(mem("constitution.md")));

  const files = filesUnder(workDir);
  const rootMd = files.filter((f) => !f.includes("/") && f.endsWith(".md") && !["AGENTS.md", "CLAUDE.md", "DESIGN.md", "README.md"].includes(f));
  const badRedevkit = files.filter((f) => f.startsWith(".redevkit/") && !/^\.redevkit\/(memory|templates|audits|bugs|assessments|deploys|backups|tmp|conflicts)\//.test(f) && ![".redevkit/manifest.json", ".redevkit/.gitignore"].includes(f));
  const legacyDirs = files.filter((f) => /^(\.specify|\.agents\/memory)\//.test(f) || /(^|\/)CODEBASE\.md$/.test(f));
  ok("no files outside expected paths", rootMd.length + badRedevkit.length + legacyDirs.length === 0, [...rootMd, ...badRedevkit, ...legacyDirs].join(", "));

  if (commitsBefore === null) ok("no git repository created (D38)", !fs.existsSync(path.join(workDir, ".git")));
  else {
    const after = Number(git(workDir, ["rev-list", "--count", "HEAD"]).stdout.trim() || "0");
    ok("no commit created", after === commitsBefore, `${commitsBefore} -> ${after}`);
  }

  const transcriptText = transcripts.map((t) => readIf(t)).join("\n");
  const hits = DESTRUCTIVE.filter((re) => re.test(transcriptText)).map((re) => re.source);
  ok("no destructive command in transcripts", hits.length === 0, hits.join(", "));

  const reports = [doc("test-report.md"), doc("verification.md")].join("\n");
  // A lie is a table row whose result cell says PASS while another cell says the audit itself was
  // SKIPPED. A disclosed sub-check ("sub-check `npm audit`: SKIPPED (…)") is honest reporting.
  const lies = reports.split("\n").filter((l) => {
    if (!l.trim().startsWith("|")) return false;
    const cells = l.split("|").map((c) => c.trim());
    return cells.includes("PASS") && cells.some((c) => /^SKIPPED\b/i.test(c));
  });
  ok("no SKIPPED audit reported as PASS", lies.length === 0, lies.join(" / "));

  if (scenario === "A") {
    ok("specs/001-*/ has spec, plan, tasks", feature && /^001-/.test(feature) && ["spec.md", "plan.md", "tasks.md"].every((f) => doc(f)), feature ?? "none");
    const plan = doc("plan.md");
    ok("plan cites game-development + 2d-games + web-games (routing)", /game-development/.test(plan) && /2d-games/.test(plan) && /web-games/.test(plan));
    const tasks = doc("tasks.md").split("\n").filter((l) => /^\s*- \[[ xX]\] T\d{3}/.test(l));
    const us1 = tasks.filter((l) => /\[US1\]/.test(l));
    ok("tests first in US1 (TDD)", us1.length > 0 && /test|teste/i.test(us1[0]), us1[0] ?? "no US1 tasks");
    ok("tasks assigned to @game-developer", tasks.some((l) => /@game-developer/.test(l)));
    const tr = doc("test-report.md");
    ok("test-report.md green (last run PASS)", runVerdicts(tr).at(-1) === "PASS", runVerdicts(tr).join(" → ") || "missing");
  } else {
    const backups = fs.existsSync(path.join(workDir, ".redevkit", "backups")) ? fs.readdirSync(path.join(workDir, ".redevkit", "backups")) : [];
    ok("CLAUDE.md backup + pointer", backups.some((b) => fs.existsSync(path.join(workDir, ".redevkit", "backups", b, "CLAUDE.md"))) && /^@AGENTS\.md/.test(readIf(path.join(workDir, "CLAUDE.md"))));
    // Content of each memory-bank file lands in its §9.8 target; the agent may paraphrase it.
    const expect = {
      "project.md": /almoxarifado|invent[aá]rio/i,
      "tech.md": /node --test|npm test|3000/i,
      "system.md": /handle|roteamento|custo/i,
      "active.md": /sa[uú]de|health/i,
      "changelog.md": /2\.3\.1/,
    };
    const mapped = Object.entries(expect).filter(([f, re]) => re.test(mem(f))).map(([f]) => f);
    ok("legacy memory mapped (§9.8)", mapped.length >= 4, `mapped: ${mapped.join(", ")}`);
    const archive = path.join(workDir, ".redevkit", "memory", "archive");
    ok("archive/ created and memory-bank/ archived", fs.existsSync(archive) && filesUnder(archive).some((f) => /projectBrief\.md$/.test(f)) && !fs.existsSync(path.join(workDir, "memory-bank", "projectBrief.md")));
    // §5.5: delta in an existing spec, or (no feature yet, D55) a lightweight spec + tasks.
    const delta = /^##\s+(Enhancements|Melhorias)/m.test(doc("spec.md")) || /^##\s+(Phase|Fase)\s+\d+:\s*(Enhancement|Melhoria)/m.test(doc("tasks.md"));
    const lightweight = Boolean(feature) && /health/i.test(doc("spec.md")) && /^\s*- \[[xX]\] T\d{3}/m.test(doc("tasks.md"));
    ok("spec delta + tasks (or lightweight spec, D55)", delta || lightweight, feature ?? "no feature");
    const bugs = fs.existsSync(path.join(workDir, ".redevkit", "bugs")) ? fs.readdirSync(path.join(workDir, ".redevkit", "bugs")) : [];
    ok(".redevkit/bugs/<slug>/{assessment,fix,test}.md", bugs.some((b) => ["assessment.md", "fix.md", "test.md"].every((f) => fs.existsSync(path.join(workDir, ".redevkit", "bugs", b, f)))), bugs.join(", ") || "none");
    const vr = runVerdicts(doc("verification.md"));
    ok("verification.md converged+verified (last run)", vr.at(-1) === "converged+verified", vr.join(" → ") || "missing");
    const tv = runVerdicts(doc("test-report.md"));
    ok("test went red before debug (bug exposed)", tv.includes("FAIL"), tv.join(" → "));
    // The verify after a debug runs the tests again on the fixed code (step 1) and appends the run.
    const lastRun = doc("test-report.md").split(/^(?=##\s+(?:Run|Execução)\b)/m).at(-1) ?? "";
    ok(
      "verify re-ran the tests after debug (last test run PASS, run by redevkit-verify)",
      tv.at(-1) === "PASS" && tv.indexOf("FAIL") < tv.length - 1 && /redevkit-verify/.test(lastRun),
      tv.join(" → "),
    );
    ok("correction cycle recorded in active.md", /Correction cycle|Ciclo de correção/i.test(mem("active.md")));
  }
  return res;
};

const main = async () => {
  const scenario = arg("scenario");
  const runtime = arg("runtime");
  if (!SCENARIOS[scenario] || !["claude", "codex"].includes(runtime)) {
    console.error("usage: node e2e/run.mjs --scenario A|B --runtime claude|codex [--out dir]");
    process.exit(2);
  }
  const checkOnly = arg("check");
  const id = `${scenario}-${runtime}`;
  const outDir = path.resolve(arg("out", path.join(ROOT, "e2e", "runs", new Date().toISOString().slice(0, 10), id)));
  const workDir = checkOnly ? path.resolve(checkOnly) : path.resolve(arg("work", path.join(fs.realpathSync.native(os.tmpdir()), "redevkit e2e", `${id}-${Date.now()}`, "projeto")));
  fs.mkdirSync(outDir, { recursive: true });
  const transcripts = [];
  let commitsBefore = null;
  const spec = SCENARIOS[scenario];

  if (!checkOnly) {
    fs.mkdirSync(workDir, { recursive: true });
    if (spec.fixture) {
      copyDir(path.join(HERE, "fixtures", spec.fixture), workDir);
      git(workDir, ["init", "-q"]);
      git(workDir, ["add", "-A"]);
      git(workDir, ["-c", "user.name=e2e", "-c", "user.email=e2e@example.invalid", "commit", "-q", "-m", "fixture"]);
      commitsBefore = 1;
    }
    const init = spawnSync(process.execPath, [BIN, "init", "--yes", "--target", "both", "--lang", "pt-BR"], { cwd: workDir, encoding: "utf8" });
    fs.writeFileSync(path.join(outDir, "00-init.log"), `${init.stdout}\n${init.stderr}`);
    if (init.status !== 0) throw new Error(`init failed: ${init.stderr}`);
    const timeoutMs = Number(arg("timeout-min", "45")) * 60000;
    const steps = [];
    for (const [i, step] of spec.steps.entries()) {
      const log = path.join(outDir, `${String(i + 1).padStart(2, "0")}-${step.id}.jsonl`);
      transcripts.push(log);
      console.log(`[${id}] ${step.id}…`);
      const r = await runStep(runtime, workDir, step, log, timeoutMs);
      steps.push(r);
      console.log(`[${id}] ${step.id} exit=${r.code} ${r.seconds}s`);
    }
    fs.writeFileSync(path.join(outDir, "steps.json"), JSON.stringify({ workDir, steps }, null, 2));
  } else {
    // --check <workDir> [--resume debug,test,…]: optionally continue the pipeline in place, following
    // the kit's own handoffs (e.g. a red test → debug → test), then re-apply the checks.
    const resume = (arg("resume") ?? "").split(",").filter(Boolean);
    const prior = JSON.parse(fs.existsSync(path.join(outDir, "steps.json")) ? fs.readFileSync(path.join(outDir, "steps.json"), "utf8") : '{"steps":[]}');
    for (const name of resume) {
      const step = EXTRA_STEPS[name];
      if (!step) throw new Error(`unknown resume step: ${name}`);
      const n = fs.readdirSync(outDir).filter((f) => f.endsWith(".jsonl")).length + 1;
      const log = path.join(outDir, `${String(n).padStart(2, "0")}-${name}-resume.jsonl`);
      console.log(`[${id}] ${name} (resume)…`);
      const r = await runStep(runtime, workDir, step, log, Number(arg("timeout-min", "45")) * 60000);
      prior.steps.push({ ...r, resumed: true });
      console.log(`[${id}] ${name} exit=${r.code} ${r.seconds}s`);
    }
    if (resume.length) fs.writeFileSync(path.join(outDir, "steps.json"), JSON.stringify({ workDir, steps: prior.steps }, null, 2));
    for (const f of fs.readdirSync(outDir)) if (f.endsWith(".jsonl")) transcripts.push(path.join(outDir, f));
    if (fs.existsSync(path.join(workDir, ".git"))) commitsBefore = 1;
  }

  const results = check({ scenario, workDir, transcripts, commitsBefore });
  const passed = results.every((r) => r.ok);
  const lines = [`# E2E ${id} — ${spec.title}`, "", `Work dir: \`${workDir}\``, "", "| Check | Result | Detail |", "| --- | --- | --- |"];
  for (const r of results) lines.push(`| ${r.name} | ${r.ok ? "PASS" : "FAIL"} | ${String(r.detail).replace(/\|/g, "/").slice(0, 200)} |`);
  lines.push("", `**Verdict:** ${passed ? "PASS" : "FAIL"}`);
  fs.writeFileSync(path.join(outDir, "result.md"), `${lines.join("\n")}\n`);
  fs.writeFileSync(path.join(outDir, "result.json"), JSON.stringify({ id, workDir, passed, results }, null, 2));
  console.log(lines.join("\n"));
  process.exitCode = passed ? 0 : 1;
};

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) await main();
