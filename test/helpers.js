import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

export const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
export const BIN = path.join(ROOT, "bin", "redevkit.js");
export const FIXTURE_KIT = path.join(ROOT, "test", "fixtures", "kit");

/** Temp project dir whose path has a space and an accent (Windows lesson). */
export const tmpProject = (label = "projeto ação") => {
  const base = fs.mkdtempSync(path.join(os.tmpdir(), "redevkit-test-"));
  const dir = path.join(base, label);
  fs.mkdirSync(dir, { recursive: true });
  return dir;
};

export const rm = (dir) => fs.rmSync(path.dirname(dir), { recursive: true, force: true });

export const cli = (args, cwd, env = {}) =>
  spawnSync(process.execPath, [BIN, ...args], {
    cwd,
    encoding: "utf8",
    env: { ...process.env, REDEVKIT_NO_TTY: "1", ...env },
    input: "",
  });

export const read = (dir, rel) => fs.readFileSync(path.join(dir, ...rel.split("/")), "utf8");
export const write = (dir, rel, text) => {
  const p = path.join(dir, ...rel.split("/"));
  fs.mkdirSync(path.dirname(p), { recursive: true });
  fs.writeFileSync(p, text);
};
export const has = (dir, rel) => fs.existsSync(path.join(dir, ...rel.split("/")));

/** Snapshot of every file under dir (relative path -> sha-ish content) for "no change" checks. */
export const treeState = (dir) => {
  const out = {};
  const visit = (d) => {
    for (const e of fs.readdirSync(d, { withFileTypes: true })) {
      const abs = path.join(d, e.name);
      if (e.isDirectory()) visit(abs);
      else out[path.relative(dir, abs).split(path.sep).join("/")] = fs.readFileSync(abs, "utf8");
    }
  };
  visit(dir);
  return out;
};
