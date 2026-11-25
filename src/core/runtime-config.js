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

const esc = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

/** Marker of a key added inside the user's inline table: "# redevkit:managed inline=<table>.<key>". */
const INLINE_TAG = `${MARK} inline=`;
const inlineTagRe = /\s*# redevkit:managed inline=([A-Za-z0-9_.-]+)/g;

/** Top-level `<table> = {` line (single-segment table name, bare or quoted). */
const inlineDefRe = (table) => new RegExp(`^\\s*(?:${esc(table)}|"${esc(table)}"|'${esc(table)}')\\s*=\\s*\\{`);

/**
 * Scan the single-line inline table that opens at `open` ("{"). Returns { close, entries } with the
 * raw [start, end) span of every top-level entry, or null when the line is not something this
 * scanner understands (multi-line table, comment inside, unbalanced quotes...).
 */
const scanInlineTable = (line, open) => {
  let depth = 0;
  let start = open + 1;
  const entries = [];
  for (let i = open; i < line.length; i += 1) {
    const ch = line[i];
    if (ch === '"' || ch === "'") {
      let j = i + 1;
      while (j < line.length && line[j] !== ch) j += ch === '"' && line[j] === "\\" ? 2 : 1;
      if (j >= line.length) return null;
      i = j;
    } else if (ch === "#") {
      return null;
    } else if (ch === "{" || ch === "[") {
      depth += 1;
    } else if (ch === "}" || ch === "]") {
      depth -= 1;
      if (depth === 0) {
        if (ch !== "}") return null;
        entries.push({ start, end: i });
        return { close: i, entries };
      }
    } else if (ch === "," && depth === 1) {
      entries.push({ start, end: i });
      start = i + 1;
    }
  }
  return null;
};

/** Index of the top-level line that defines `table` as an inline table, or -1. */
const inlineDefLine = (lines, table) => {
  if (table.includes(".")) return -1;
  const firstHeader = lines.findIndex((l) => anyHeaderRe.test(l));
  const re = inlineDefRe(table);
  return lines.findIndex((l, i) => (firstHeader === -1 || i < firstHeader) && re.test(l));
};

/** Add `key = value` inside the inline table on `line`, keeping the user's formatting; null if unsure. */
const insertInline = (line, table, key, value) => {
  const open = inlineDefRe(table).exec(line)[0].length - 1;
  const scan = scanInlineTable(line, open);
  if (!scan || !/^\s*(#.*)?$/.test(line.slice(scan.close + 1))) return null;
  const head = line.slice(0, scan.close);
  const ws = /\s*$/.exec(head)[0];
  const body = head.slice(0, head.length - ws.length);
  const inserted = body.endsWith("{") ? `${body} ${key} = ${value} ` : `${body}, ${key} = ${value}${ws}`;
  return `${inserted}${line.slice(scan.close)}   ${INLINE_TAG}${table}.${key}`;
};

const entryKey = (text) => text.split("=")[0].trim().replace(/^["']|["']$/g, "");

/** Remove `key` from the inline table on `line` (the reverse of insertInline), or null. */
const removeInline = (line, table, key) => {
  const m = inlineDefRe(table).exec(line);
  if (!m) return null;
  const open = m[0].length - 1;
  const scan = scanInlineTable(line, open);
  if (!scan) return null;
  const { entries } = scan;
  const idx = entries.findIndex((e) => entryKey(line.slice(e.start, e.end)) === key);
  if (idx < 0) return null;
  const e = entries[idx];
  if (entries.filter((x) => line.slice(x.start, x.end).trim() !== "").length === 1) return `${line.slice(0, open + 1)}${line.slice(scan.close)}`; // only entry: "{}"
  const valueEnd = e.start + line.slice(e.start, e.end).trimEnd().length;
  if (idx > 0) return line.slice(0, entries[idx - 1].end) + line.slice(valueEnd); // drop ", key = value"
  const lead = /^\s*/.exec(line.slice(e.start, e.end))[0].length;
  return line.slice(0, e.start + lead) + line.slice(entries[1].start).replace(/^\s*/, "");
};

/** Candidate lines with one managed entry added, or null when there is no safe edit. */
const insertEntry = (lines, parsed, table, key, value) => {
  const out = [...lines];
  const line = `${key} = ${value}   ${MARK}`;
  const h = out.findIndex((l) => headerRe(table).test(l));
  if (h >= 0) {
    out.splice(h + 1, 0, line);
    return out;
  }
  const inline = inlineDefLine(out, table);
  if (inline >= 0) {
    // Table written inline (`features = { custom = true }`): it is closed, so neither a [table]
    // header nor a dotted key may extend it. The key goes inside the braces instead (A17).
    const edited = insertInline(out[inline], table, key, value);
    if (edited === null) return null;
    out[inline] = edited;
    return out;
  }
  if (parsed[table.split(".")[0]] !== undefined) {
    // Table defined through dotted keys (or implicitly by a [table.sub] header): add a dotted key
    // before the first header.
    const firstHeader = out.findIndex((l) => anyHeaderRe.test(l));
    const dotted = `${table}.${key} = ${value}   ${MARK}`;
    if (firstHeader === -1) out.push(dotted);
    else out.splice(firstHeader, 0, dotted);
    return out;
  }
  if (out.length && out[out.length - 1].trim() !== "") out.push("");
  out.push(`[${table}]   ${MARK}`, line);
  return out;
};

const toText = (lines) => (lines.length ? `${lines.join("\n")}\n` : "");
const asJson = (v) => JSON.stringify(v, (_, x) => (typeof x === "bigint" ? `${x}n` : x));

/**
 * True when `next` is `before` plus exactly `table.key = value`: the edit added the entry and changed
 * nothing else. A fresh parse of the result is the judge, never the line edit itself.
 */
const addsOnly = (before, next, table, key, value) => {
  try {
    if (asJson(getPath(next, table, key)) !== asJson(tomlParse(`v = ${value}`).v)) return false;
    const copy = JSON.parse(asJson(next));
    const parts = table.split(".");
    const chain = [copy];
    for (const part of parts) chain.push(chain[chain.length - 1][part]);
    delete chain[chain.length - 1][key];
    // Tables the edit created must be empty again once the key is gone; drop them before comparing.
    for (let i = parts.length; i >= 1; i -= 1) {
      let prev = before;
      for (const part of parts.slice(0, i)) prev = prev && typeof prev === "object" ? prev[part] : undefined;
      if (prev === undefined && Object.keys(chain[i]).length === 0) delete chain[i - 1][parts[i - 1]];
    }
    return asJson(copy) === asJson(before);
  } catch {
    return false;
  }
};

/**
 * Merge managed keys into config.toml preserving comments (line edits; smol-toml only detects).
 * entries: [{table, key, value}] where value is TOML source text.
 * Each entry is added and validated on its own (a new parse must show the entry and nothing else
 * changed): an entry that cannot be added safely is skipped and reported, the others still apply.
 * Returns { ok, text, added: [{table,key}], kept: [{table,key,userValue}], skipped: [{table,key,value}], error, changed }.
 */
export const mergeCodexConfig = (existing, entries) => {
  const src = existing === null || existing === undefined ? "" : nl(stripBom(String(existing)));
  let parsed = {};
  try {
    parsed = src.trim() ? tomlParse(src) : {};
  } catch (err) {
    return { ok: false, error: `invalid TOML: ${err.message}` };
  }
  let lines = src === "" ? [] : src.replace(/\n$/, "").split("\n");
  const added = [];
  const kept = [];
  const skipped = [];
  for (const { table, key, value } of entries) {
    const current = getPath(parsed, table, key);
    if (current !== undefined) {
      // Ours under its [table] header, as the dotted `table.key = ...` line added for tables defined
      // through dotted keys, or inside the user's inline table (tagged "inline=table.key").
      const ours = lines.some(
        (l) => l.includes(MARK) && (new RegExp(`^\\s*(?:${esc(table)}\\.)?${esc(key)}\\s*=`).test(l) || l.includes(`${INLINE_TAG}${table}.${key}`)),
      );
      if (!ours) kept.push({ table, key, userValue: current });
      continue;
    }
    const candidate = insertEntry(lines, parsed, table, key, value);
    let next = null;
    try {
      next = candidate ? tomlParse(toText(candidate)) : null;
    } catch {
      next = null;
    }
    if (!next || !addsOnly(parsed, next, table, key, value)) {
      skipped.push({ table, key, value });
      continue;
    }
    lines = candidate;
    parsed = next;
    added.push({ table, key });
  }
  return { ok: true, text: toText(lines), added, kept, skipped, changed: added.length > 0 };
};

/**
 * Remove every managed line and every key added inside an inline table; drop managed table headers
 * left without keys. Returns { ok, text, removed }: `text` is undefined when nothing was removed
 * (leave the file alone, A16) and null when the file would be left empty (delete it).
 */
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
    const tags = [...l.matchAll(inlineTagRe)].map((m) => m[1]);
    if (tags.length) {
      let edited = l.replace(inlineTagRe, "");
      for (const tag of tags) {
        const dot = tag.lastIndexOf(".");
        const next = removeInline(edited, tag.slice(0, dot), tag.slice(dot + 1));
        if (next !== null) edited = next;
      }
      try {
        tomlParse(edited);
      } catch {
        out.push(l); // cannot be undone safely: leave the line as it is
        continue;
      }
      out.push(edited);
      removed += tags.length;
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
  if (removed === 0) return { ok: true, text: undefined, removed: 0 };
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
