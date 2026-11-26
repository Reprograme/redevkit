// Scenario L's saboteur: keeps src/ frozen on the broken snapshot the harness took, so no fix the
// agent makes ever holds, and logs a timeline of the loop lines of active.md. It runs detached,
// outside the agent's view (its files live next to the project folder, not inside it).
//
// Usage: node e2e/saboteur.mjs <projectDir> <snapshot.json> <log file> <stop file>
// It exits when the stop file appears (or on SIGTERM).
import fs from "node:fs";
import path from "node:path";

const [projectDir, snapshotFile, logFile, stopFile] = process.argv.slice(2);
const snapshot = JSON.parse(fs.readFileSync(snapshotFile, "utf8")); // { "src/x.js": "content" }
const src = path.join(projectDir, "src");
const active = path.join(projectDir, ".redevkit", "memory", "active.md");
const LOOP_LINES = /^- (Failing scope|Test cycle|Correction cycle):.*$/gm;

const log = (event) => fs.appendFileSync(logFile, `${JSON.stringify({ t: new Date().toISOString(), ...event })}\n`);

const filesUnder = (dir, base = dir) => {
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((e) => {
    const p = path.join(dir, e.name);
    return e.isDirectory() ? filesUnder(p, base) : [path.relative(base, p).split(path.sep).join("/")];
  });
};

let lastLoop = "";
const tick = () => {
  // 1. Undo every change under src/: edited files go back, new files go away, deleted ones return.
  const present = new Set(filesUnder(src).map((f) => `src/${f}`));
  for (const rel of present) {
    const file = path.join(projectDir, rel);
    try {
      if (!(rel in snapshot)) {
        fs.rmSync(file, { force: true });
        log({ revert: rel, how: "removed new file" });
      } else if (fs.readFileSync(file, "utf8") !== snapshot[rel]) {
        fs.writeFileSync(file, snapshot[rel]);
        log({ revert: rel, how: "restored broken content" });
      }
    } catch (e) {
      log({ error: `${rel}: ${e.message}` });
    }
  }
  for (const rel of Object.keys(snapshot)) {
    if (present.has(rel)) continue;
    try {
      fs.mkdirSync(path.dirname(path.join(projectDir, rel)), { recursive: true });
      fs.writeFileSync(path.join(projectDir, rel), snapshot[rel]);
      log({ revert: rel, how: "recreated deleted file" });
    } catch (e) {
      log({ error: `${rel}: ${e.message}` });
    }
  }
  // 2. Timeline of the loop lines (Failing scope, Test cycle, Correction cycle).
  try {
    const lines = (fs.readFileSync(active, "utf8").match(LOOP_LINES) ?? []).join("\n");
    if (lines !== lastLoop) {
      lastLoop = lines;
      log({ loop: lines.split("\n") });
    }
  } catch {
    // active.md may be mid-write or missing: next tick
  }
  if (fs.existsSync(stopFile)) {
    log({ stop: "stop file" });
    process.exit(0);
  }
};

process.on("SIGTERM", () => {
  log({ stop: "SIGTERM" });
  process.exit(0);
});
log({ start: Object.keys(snapshot) });
setInterval(tick, 1000);
