// Catalog budget per target (D46, RC1): the sum of the skill descriptions the runtime lists.
import { parseFrontmatter } from "./frontmatter.js";

export const BUDGET_LIMIT = 12000; // plan §4.3 initial limit, per target
// Claude Code lists skills within 1% of the context window, 8,000 characters as fallback (RC1).
// Codex limits the catalog to ~2% of the context (8,000 characters fallback) unless
// skills.max_context_tokens is raised (the CLI raises it, D51).
export const SOFT_LIMIT = 8000;

/** files: Map<rel, content> rendered for ONE target. */
export const measureCatalog = (files, targetId) => {
  const entries = [];
  const isSkill = targetId === "claude" ? /^\.claude\/skills\/[^/]+\/SKILL\.md$/ : /^\.agents\/skills\/[^/]+\/SKILL\.md$/;
  for (const [rel, content] of files) {
    if (!isSkill.test(rel)) continue;
    const { data } = parseFrontmatter(String(content));
    const description = String(data.description ?? "");
    entries.push({ name: String(data.name ?? rel), description, length: description.length });
  }
  const total = entries.reduce((s, e) => s + e.length, 0);
  return {
    target: targetId,
    count: entries.length,
    total,
    limit: BUDGET_LIMIT,
    softLimit: SOFT_LIMIT,
    withinLimit: total <= BUDGET_LIMIT,
    withinSoftLimit: total <= SOFT_LIMIT,
    longest: [...entries].sort((a, b) => b.length - a.length).slice(0, 5),
  };
};
