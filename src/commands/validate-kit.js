// redevkit validate-kit: validates the kit shipped in this package (maintainers and CI).
import { KIT_ROOT, loadKit } from "../core/render.js";
import { validateKit } from "../core/validate.js";

export const runValidateKit = async (opts, { log = console.log, kitRoot = KIT_ROOT } = {}) => {
  const kit = loadKit(kitRoot);
  const { issues, budgets, blocks } = validateKit({ kit, kitRoot });
  const errors = issues.filter((i) => i.level === "error");
  if (opts.json) {
    log(JSON.stringify({ ok: errors.length === 0, budgets, blocks, issues }, null, 2));
    return { ok: errors.length === 0, issues, budgets, blocks };
  }
  log(`skills: ${kit.skills.length} · personas: ${kit.personas.length}`);
  for (const [t, b] of Object.entries(budgets)) log(`catalog ${t}: ${b.count} entries, ${b.total}/${b.limit} chars (fallback listing budget ${b.softLimit})`);
  for (const [k, b] of Object.entries(blocks)) log(`AGENTS.md block (${k}): ${b.lines} lines, ${b.bytes} bytes`);
  for (const i of issues) log(`${i.level.toUpperCase().padEnd(5)} ${i.file}: ${i.message}`);
  log(errors.length ? `${errors.length} error(s)` : "Kit valid.");
  return { ok: errors.length === 0, issues, budgets, blocks };
};
