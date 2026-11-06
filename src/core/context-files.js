// AGENTS.md managed block and CLAUDE.md pointer/migration (D07, D40, D50, §4.4).

export const BEGIN = "<!-- REDEVKIT:BEGIN (managed by the redevkit CLI; edit outside this block) -->";
export const END = "<!-- REDEVKIT:END -->";
const BEGIN_RE = /<!--\s*REDEVKIT:BEGIN[^>]*-->/;
const END_RE = /<!--\s*REDEVKIT:END\s*-->/;

export const NOTES_HEADING = { "pt-BR": "## Notas do projeto", en: "## Project notes" };

const nl = (s) => s.replace(/\r\n?/g, "\n");

export const wrapBlock = (block) => `${BEGIN}\n\n${block.trim()}\n\n${END}`;

/** Locate the managed block. Returns {start, end} offsets or null; throws on malformed markers. */
export const findBlock = (text) => {
  const b = BEGIN_RE.exec(text);
  const e = END_RE.exec(text);
  if (!b && !e) return null;
  if (!b || !e || e.index < b.index) throw new Error("AGENTS.md has a malformed REDEVKIT block (BEGIN/END markers mismatch)");
  return { start: b.index, end: e.index + e[0].length, inner: text.slice(b.index + b[0].length, e.index).trim() };
};

/** Insert or replace the managed block. Idempotent. */
export const upsertAgentsBlock = (existing, block, lang) => {
  const wrapped = wrapBlock(block);
  if (existing === null || existing === undefined || existing.trim() === "") {
    return `${wrapped}\n\n${NOTES_HEADING[lang] ?? NOTES_HEADING.en}\n`;
  }
  const text = nl(existing);
  const found = findBlock(text);
  if (found) return text.slice(0, found.start) + wrapped + text.slice(found.end);
  // Insert at the top, keeping the user's content below.
  return `${wrapped}\n\n${text.replace(/^\n+/, "")}`;
};

/** Remove the managed block, keeping everything else (uninstall). */
export const removeAgentsBlock = (existing) => {
  if (!existing) return existing;
  const text = nl(existing);
  const found = findBlock(text);
  if (!found) return text;
  const out = (text.slice(0, found.start) + text.slice(found.end)).replace(/^\n+/, "").replace(/\n{3,}/g, "\n\n");
  return out;
};

export const blockInner = (existing) => {
  if (!existing) return null;
  const found = findBlock(nl(existing));
  return found ? found.inner : null;
};

/** True when CLAUDE.md content is (any language variant of) the pointer. */
export const isPointer = (content, pointers) => {
  const norm = (s) => nl(s).trim().replace(/\s+/g, " ");
  return pointers.some((p) => norm(p) === norm(content));
};

/** Content to migrate from an existing CLAUDE.md: drop a bare "@AGENTS.md" line (self-import). */
export const migratableContent = (content) =>
  nl(content)
    .split("\n")
    .filter((line) => line.trim() !== "@AGENTS.md")
    .join("\n")
    .trim();

/** Append migrated CLAUDE.md content to AGENTS.md (outside the block). */
export const appendMigratedNotes = (agentsText, migrated, lang, date) => {
  const heading =
    lang === "pt-BR"
      ? `## Notas do projeto (migrado de CLAUDE.md em ${date})`
      : `## Project notes (migrated from CLAUDE.md on ${date})`;
  const base = nl(agentsText).replace(/\n*$/, "");
  return `${base}\n\n${heading}\n\n${migrated}\n`;
};

/** Minimal unified-style diff for the confirmation prompt (D40). */
export const simpleDiff = (before, after, label = "CLAUDE.md") => {
  const a = nl(before).split("\n");
  const b = nl(after).split("\n");
  const lines = [`--- ${label} (current)`, `+++ ${label} (new)`];
  for (const l of a) lines.push(`- ${l}`);
  for (const l of b) lines.push(`+ ${l}`);
  return lines.join("\n");
};
