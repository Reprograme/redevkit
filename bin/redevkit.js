#!/usr/bin/env node
// Entry point. The guard compares real paths so it works through npm shims, symlinks and
// paths with spaces or accents (lesson from AG Kit H1).
import { realpathSync } from "node:fs";
import { pathToFileURL } from "node:url";
import { main } from "../src/cli.js";

const invokedDirectly = (() => {
  try {
    return import.meta.url === pathToFileURL(realpathSync(process.argv[1])).href;
  } catch {
    return false;
  }
})();

if (invokedDirectly) await main();

export { main };
