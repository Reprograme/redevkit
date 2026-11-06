// redevkit target add|remove <claude|codex>  (§10). AGENTS.md always stays.
import { t } from "../core/i18n.js";
import { CliError } from "./init.js";
import { requireManifest, runSync } from "./update.js";

export const runTarget = async (action, target, opts, { log = console.log, projectDir = process.cwd() } = {}) => {
  const manifest = requireManifest(projectDir);
  if (!["claude", "codex"].includes(target)) throw new CliError(t("invalidTarget", { v: target }), 2);
  let targets;
  if (action === "add") {
    if (manifest.targets.includes(target)) {
      log(t("alreadyTarget", { v: target }));
      return { noop: true };
    }
    targets = [...manifest.targets, target].sort();
  } else if (action === "remove") {
    if (!manifest.targets.includes(target)) {
      log(t("notTarget", { v: target }));
      return { noop: true };
    }
    targets = manifest.targets.filter((x) => x !== target);
    if (targets.length === 0) throw new CliError(t("lastTarget"), 2);
  } else {
    throw new CliError(`Unknown action: ${action} (use add or remove)`, 2);
  }
  return runSync(projectDir, manifest, targets, { ...opts, migrateClaude: action === "add" && target === "claude" ? Boolean(opts.yes) : undefined }, log);
};
