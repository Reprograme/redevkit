#!/usr/bin/env node
// Builds e2e/RESULTS.md from the result.json of the given run directories.
// Usage: node e2e/summarize.mjs <runDir> [<runDir> …]
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const dirs = process.argv.slice(2);
const rows = [];
const details = [];
for (const dir of dirs) {
  const file = path.join(dir, "result.json");
  if (!fs.existsSync(file)) {
    rows.push(`| ${path.basename(dir)} | — | not run | — |`); // 4 cells, like the header (MD056)
    continue;
  }
  const r = JSON.parse(fs.readFileSync(file, "utf8"));
  const steps = fs.existsSync(path.join(dir, "steps.json")) ? JSON.parse(fs.readFileSync(path.join(dir, "steps.json"), "utf8")).steps : [];
  const minutes = Math.round(steps.reduce((s, x) => s + (x.seconds ?? 0), 0) / 60);
  const passed = r.results.filter((x) => x.ok).length;
  rows.push(`| ${r.id} | ${passed}/${r.results.length} | ${r.passed ? "PASS" : "FAIL"} | ${minutes} min |`);
  details.push(`### ${r.id}`, "", "| Check | Result | Detail |", "| --- | --- | --- |");
  for (const x of r.results) details.push(`| ${x.name} | ${x.ok ? "PASS" : "FAIL"} | ${String(x.detail ?? "").replace(/\|/g, "/").replace(/\n/g, " ").slice(0, 160)} |`);
  details.push("");
}
const allPass = rows.every((r) => r.includes("| PASS |"));
const out = [
  "# Resultados do E2E",
  "",
  `Gerado por \`e2e/summarize.mjs\` em ${new Date().toISOString().slice(0, 16).replace("T", " ")} UTC. Roteiro e checagens em [README.md](README.md).`,
  "",
  "| Run | Checagens | Veredito | Duração dos passos |",
  "| --- | --- | --- | --- |",
  ...rows,
  "",
  `**Resultado:** ${rows.filter((r) => r.includes("| PASS |")).length} de ${rows.length} aprovados${allPass ? "." : " (ver detalhes)."}`,
  "",
  "## Detalhes",
  "",
  ...details,
];
fs.writeFileSync(path.join(HERE, "RESULTS.md"), `${out.join("\n").replace(/\n+$/, "")}\n`);
console.log(out.slice(0, 12).join("\n"));
