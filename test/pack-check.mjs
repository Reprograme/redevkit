// `npm pack --dry-run` contains only the "files" allowlist and no Python bytecode (lesson H4).
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

export const packFiles = () => {
  // Fixed command string, no user input: a shell is needed on Windows to resolve npm.cmd.
  const r = spawnSync("npm pack --dry-run --json --ignore-scripts", { cwd: root, encoding: "utf8", shell: true });
  if (r.status !== 0) throw new Error(`npm pack failed: ${r.stderr}`);
  const data = JSON.parse(r.stdout.slice(r.stdout.indexOf("[")));
  return data[0].files.map((f) => f.path.replace(/\\/g, "/"));
};

export const checkPack = (files) => {
  const pkg = JSON.parse(fs.readFileSync(path.join(root, "package.json"), "utf8"));
  const allow = [...pkg.files, "package.json"].map((f) => f.replace(/\/$/, ""));
  const problems = [];
  for (const f of files) {
    if (!allow.some((a) => f === a || f.startsWith(`${a}/`))) problems.push(`not in allowlist: ${f}`);
    if (/__pycache__|\.pyc$/.test(f)) problems.push(`python bytecode: ${f}`);
    if (/(^|\/)(desktop\.ini|thumbs\.db|\.ds_store)$/i.test(f)) problems.push(`junk file: ${f}`);
  }
  for (const must of ["bin/redevkit.js", "src/cli.js", "kit/context/AGENTS.block.md", "LICENSE", "NOTICE", "README.md"]) {
    if (!files.includes(must)) problems.push(`missing from package: ${must}`);
  }
  return problems;
};

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const files = packFiles();
  const problems = checkPack(files);
  console.log(`${files.length} files in package`);
  for (const p of problems) console.log(`ERROR ${p}`);
  process.exitCode = problems.length ? 1 : 0;
}
