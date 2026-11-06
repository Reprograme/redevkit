// Shared console reporting for init / update / target.
import path from "node:path";
import { summarize } from "../core/install.js";
import { CONFLICT_ROOT } from "../core/managed-tree.js";
import { t } from "../core/i18n.js";

export const printPlan = (sync, { verbose = false, out = console.log } = {}) => {
  out(t("planSummary", summarize(sync.plan)));
  if (verbose) for (const a of sync.plan.actions) out(`  ${a.type.padEnd(6)} ${a.file}`);
  if (sync.plan.conflicts.length) {
    out(t("conflictsHeader", { dir: `${CONFLICT_ROOT}/<run>/` }));
    for (const c of sync.plan.conflicts) out(`  ! ${c.file} (${c.reason})`);
  }
  const notable = sync.plan.preserved.filter((p) => p.reason !== "user-owned file");
  if (notable.length) {
    out(t("preservedHeader"));
    for (const p of notable) out(`  = ${p.file} (${p.reason})`);
  }
};

export const printMessages = (messages, { out = console.log } = {}) => {
  for (const m of messages) out(`${m.level === "warn" ? "! " : ""}${t(m.key, m.vars)}`);
};

export const printConfigPreview = (sync, { out = console.log } = {}) => {
  for (const [target, c] of Object.entries(sync.config)) {
    if (!c) continue;
    const file = target === "claude" ? ".claude/settings.json" : ".codex/config.toml";
    if (!c.ok) out(`! ${t("configInvalid", { file, err: c.error })}`);
    else if (c.changed) out(`  config ${file}: +${c.added.length}`);
    for (const k of c.kept ?? []) out(`  ${t("configKept", { file, key: `${k.table}.${k.key}`, val: JSON.stringify(k.userValue) })}`);
  }
};

export const writeConflictReport = (projectDir, file, sync, runId) => {
  const report = {
    runId,
    createdAt: new Date().toISOString(),
    summary: summarize(sync.plan),
    actions: sync.plan.actions,
    conflicts: sync.plan.conflicts,
    preserved: sync.plan.preserved,
  };
  return { path: path.resolve(projectDir, file), text: `${JSON.stringify(report, null, 2)}\n` };
};
