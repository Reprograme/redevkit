// Managed runtime configuration (D51): only permissions.allow in .claude/settings.json and two
// keys in .codex/config.toml. Nothing else is ever written.
import { parse as tomlParse } from "smol-toml";

export const MARK = "# redevkit:managed";

const nl = (s) => s.replace(/\r\n?/g, "\n");
const stripBom = (s) => (s.charCodeAt(0) === 0xfeff ? s.slice(1) : s);

/**
 * Merge allow entries into settings.json text.
 * Returns { ok, text, added, error, created }. On invalid JSON: ok=false and nothing to write.
 */
export const mergeClaudeSettings = (existing, entries) => {
  let data = {};
  const created = existing === null || existing === undefined;
  if (!created) {
    const src = stripBom(String(existing));
    if (src.trim() !== "") {
      try {
        data = JSON.parse(src);
      } catch (err) {
        return { ok: false, error: `invalid JSON: ${err.message}` };
      }
      if (typeof data !== "object" || data === null || Array.isArray(data)) return { ok: false, error: "settings root is not an object" };
    }
  }
  if (data.permissions !== undefined && (typeof data.permissions !== "object" || data.permissions === null || Array.isArray(data.permissions))) {
    return { ok: false, error: "permissions is not an object" };
  }
  data.permissions = data.permissions ?? {};
  if (data.permissions.allow !== undefined && !Array.isArray(data.permissions.allow)) return { ok: false, error: "permissions.allow is not an array" };
  const allow = data.permissions.allow ?? [];
  const added = [];
  for (const e of entries) {
    if (!allow.includes(e)) {
      allow.push(e);
      added.push(e);
    }
  }
  data.permissions.allow = allow;
  return { ok: true, text: `${JSON.stringify(data, null, 2)}\n`, added, created, changed: added.length > 0 || created };
};

/** Remove previously added entries. Returns { ok, text|null (null = delete file), removed }. */
export const unmergeClaudeSettings = (existing, entries, { deleteIfEmpty = false } = {}) => {
  if (existing === null || existing === undefined) return { ok: true, text: undefined, removed: [] };
  let data;
  try {
    data = JSON.parse(stripBom(String(existing)));
  } catch (err) {
    return { ok: false, error: `invalid JSON: ${err.message}` };
  }
  const allow = data?.permissions?.allow;
  if (!Array.isArray(allow)) return { ok: true, text: undefined, removed: [] };
  const set = new Set(entries);
  const removed = allow.filter((e) => set.has(e));
  data.permissions.allow = allow.filter((e) => !set.has(e));
  if (data.permissions.allow.length === 0) delete data.permissions.allow;
  if (Object.keys(data.permissions).length === 0) delete data.permissions;
  if (deleteIfEmpty && Object.keys(data).length === 0) return { ok: true, text: null, removed };
  return { ok: true, text: `${JSON.stringify(data, null, 2)}\n`, removed };
};

const headerRe = (table) => new RegExp(`^\\s*\\[\\s*${table.replace(/\./g, "\\.")}\\s*\\]\\s*(#.*)?$`);
const anyHeaderRe = /^\s*\[\[?[^\]]+\]\]?\s*(#.*)?$/;

const getPath = (obj, table, key) => {
  let cur = obj;
  for (const part of table.split(".")) {
    if (cur === null || typeof cur !== "object") return undefined;
    cur = cur[part];
  }
  return cur && typeof cur === "object" ? cur[key] : undefined;
};

/**
 * Merge managed keys into config.toml preserving comments (line edits; smol-toml only detects).
 * entries: [{table, key, value}] where value is TOML source text.
 * Returns { ok, text, added: [{table,key}], kept: [{table,key,userValue}], error, changed }.
 */
export const mergeCodexConfig = (existing, entries) => {
  const src = existing === null || existing === undefined ? "" : nl(stripBom(String(existing)));
  let parsed = {};
  try {
    parsed = src.trim() ? tomlParse(src) : {};
  } catch (err) {
    return { ok: false, error: `invalid TOML: ${err.message}` };
  }
  const lines = src === "" ? [] : src.replace(/\n$/, "").split("\n");
  const added = [];
  const kept = [];
  for (const { table, key, value } of entries) {
    const current = getPath(parsed, table, key);
    if (current !== undefined) {
      const ours = lines.some((l) => l.includes(MARK) && new RegExp(`^\\s*${key}\\s*=`).test(l));
      if (!ours) kept.push({ table, key, userValue: current });
      continue;
    }
    const line = `${key} = ${value}   ${MARK}`;
    const h = lines.findIndex((l) => headerRe(table).test(l));
    if (h >= 0) {
      lines.splice(h + 1, 0, line);
    } else if (parsed[table.split(".")[0]] !== undefined && !lines.some((l) => headerRe(table).test(l))) {
      // Table defined through dotted keys or inline: add a dotted key before the first header.
      const firstHeader = lines.findIndex((l) => anyHeaderRe.test(l));
      const dotted = `${table}.${key} = ${value}   ${MARK}`;
      if (firstHeader === -1) lines.push(dotted);
      else lines.splice(firstHeader, 0, dotted);
    } else {
      if (lines.length && lines[lines.length - 1].trim() !== "") lines.push("");
      lines.push(`[${table}]   ${MARK}`, line);
    }
    added.push({ table, key });
  }
  const text = lines.length ? `${lines.join("\n")}\n` : "";
  try {
    tomlParse(text);
  } catch (err) {
    return { ok: false, error: `merge would produce invalid TOML: ${err.message}` };
  }
  return { ok: true, text, added, kept, changed: added.length > 0 };
};

/** Remove every managed line; drop managed table headers left without keys. */
export const unmergeCodexConfig = (existing) => {
  if (existing === null || existing === undefined) return { ok: true, text: undefined, removed: 0 };
  const lines = nl(stripBom(String(existing))).replace(/\n$/, "").split("\n");
  const out = [];
  let removed = 0;
  for (let i = 0; i < lines.length; i += 1) {
    const l = lines[i];
    if (!l.includes(MARK)) {
      out.push(l);
      continue;
    }
    if (anyHeaderRe.test(l.replace(MARK, ""))) {
      // Managed header: keep it (unmarked) if unmanaged keys remain below it.
      let j = i + 1;
      let hasUserKeys = false;
      while (j < lines.length && !anyHeaderRe.test(lines[j])) {
        if (lines[j].trim() && !lines[j].trim().startsWith("#") && !lines[j].includes(MARK)) hasUserKeys = true;
        j += 1;
      }
      if (hasUserKeys) out.push(l.replace(MARK, "").trimEnd());
      else removed += 1;
      continue;
    }
    removed += 1;
  }
  while (out.length && out[out.length - 1].trim() === "") out.pop();
  const text = out.length ? `${out.join("\n")}\n` : "";
  return { ok: true, text: text.trim() === "" ? null : text, removed };
};

/** Report which managed entries are present (doctor). */
export const codexEntriesPresent = (existing, entries) => {
  if (!existing) return entries.map((e) => ({ ...e, present: false }));
  let parsed;
  try {
    parsed = tomlParse(nl(stripBom(existing)));
  } catch {
    return entries.map((e) => ({ ...e, present: false, invalid: true }));
  }
  return entries.map((e) => ({ ...e, present: getPath(parsed, e.table, e.key) !== undefined }));
};
