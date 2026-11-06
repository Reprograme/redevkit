// Tolerant frontmatter parser for the small YAML subset used by the kit (H5: CRLF safe).
// Supports: `key: value`, quoted strings, flow lists `[a, b]`, block lists (`- item`),
// one level of nested maps (`metadata:` + indented `key: value`), comments and booleans/numbers.

const FENCE = /^---[ \t]*$/;

const unquote = (raw) => {
  const v = raw.trim();
  if (v.startsWith('"') && v.endsWith('"') && v.length >= 2) {
    try {
      return JSON.parse(v);
    } catch {
      return v.slice(1, -1);
    }
  }
  if (v.startsWith("'") && v.endsWith("'") && v.length >= 2) return v.slice(1, -1).replace(/''/g, "'");
  return v;
};

const stripComment = (v) => {
  // Remove ` # comment` outside quotes.
  let inS = false;
  let inD = false;
  for (let i = 0; i < v.length; i += 1) {
    const c = v[i];
    if (c === "'" && !inD) inS = !inS;
    else if (c === '"' && !inS && v[i - 1] !== "\\") inD = !inD;
    else if (c === "#" && !inS && !inD && (i === 0 || /\s/.test(v[i - 1]))) return v.slice(0, i).trimEnd();
  }
  return v;
};

const scalar = (raw) => {
  const v = stripComment(raw).trim();
  if (v === "") return "";
  if (v.startsWith("[") && v.endsWith("]")) {
    const inner = v.slice(1, -1).trim();
    if (!inner) return [];
    return inner.split(",").map((s) => unquote(s)).filter((s) => s !== "");
  }
  if (v === "true") return true;
  if (v === "false") return false;
  if (v === "null" || v === "~") return null;
  if (/^-?\d+(\.\d+)?$/.test(v)) return Number(v);
  return unquote(v);
};

/**
 * Split a Markdown document into frontmatter data and body.
 * Returns { data, body, hasFrontmatter, errors }.
 */
export const parseFrontmatter = (text) => {
  const src = (text.charCodeAt(0) === 0xfeff ? text.slice(1) : text).replace(/\r\n?/g, "\n");
  const lines = src.split("\n");
  if (!FENCE.test(lines[0] ?? "")) return { data: {}, body: src, hasFrontmatter: false, errors: [] };
  let end = -1;
  for (let i = 1; i < lines.length; i += 1) {
    if (FENCE.test(lines[i])) {
      end = i;
      break;
    }
  }
  if (end === -1) return { data: {}, body: src, hasFrontmatter: false, errors: ["unterminated frontmatter"] };

  const data = {};
  const errors = [];
  let currentKey = null; // key whose value continues on indented lines
  for (let i = 1; i < end; i += 1) {
    const line = lines[i];
    if (!line.trim() || line.trim().startsWith("#")) continue;
    const indented = /^\s+/.test(line);
    if (indented && currentKey) {
      const t = line.trim();
      if (t.startsWith("- ")) {
        if (!Array.isArray(data[currentKey])) data[currentKey] = [];
        data[currentKey].push(scalar(t.slice(2)));
        continue;
      }
      const m = /^([A-Za-z0-9_.-]+):\s*(.*)$/.exec(t);
      if (m) {
        if (typeof data[currentKey] !== "object" || data[currentKey] === null || Array.isArray(data[currentKey])) data[currentKey] = {};
        data[currentKey][m[1]] = scalar(m[2]);
        continue;
      }
      errors.push(`line ${i + 1}: cannot parse "${t}"`);
      continue;
    }
    const m = /^([A-Za-z0-9_.-]+):(?:\s+(.*)|\s*)$/.exec(line);
    if (!m) {
      errors.push(`line ${i + 1}: expected "key: value"`);
      currentKey = null;
      continue;
    }
    const [, key, rest = ""] = m;
    if (Object.prototype.hasOwnProperty.call(data, key)) errors.push(`line ${i + 1}: duplicate key "${key}"`);
    if (rest.trim() === "" || rest.trim() === "|" || rest.trim() === ">") {
      data[key] = rest.trim() === "" ? null : "";
      currentKey = key;
      if (rest.trim() === "|" || rest.trim() === ">") {
        // Block scalar: collect indented lines verbatim.
        const block = [];
        while (i + 1 < end && (/^\s+/.test(lines[i + 1]) || lines[i + 1].trim() === "")) {
          i += 1;
          block.push(lines[i].replace(/^\s{2}/, ""));
        }
        data[key] = rest.trim() === "|" ? block.join("\n").trimEnd() : block.join(" ").replace(/\s+/g, " ").trim();
        currentKey = null;
      }
    } else {
      data[key] = scalar(rest);
      currentKey = null;
    }
  }
  const body = lines.slice(end + 1).join("\n");
  return { data, body, hasFrontmatter: true, errors };
};

/** Normalize a list-like value (flow list, comma string or array) into an array of strings. */
export const asList = (value) => {
  if (value === null || value === undefined || value === "") return [];
  if (Array.isArray(value)) return value.map(String).map((s) => s.trim()).filter(Boolean);
  return String(value).split(",").map((s) => s.trim()).filter(Boolean);
};

const PLAIN_SAFE = /^[A-Za-z0-9_./(][^\n]*$/;

/** Quote a YAML scalar only when needed. */
export const yamlScalar = (value) => {
  if (typeof value === "boolean" || typeof value === "number") return String(value);
  const s = String(value);
  const needsQuote =
    !PLAIN_SAFE.test(s) ||
    /:\s|:$|\s#|^[-?:,[\]{}#&*!|>'"%@`]/.test(s) ||
    /^(true|false|null|yes|no|on|off|~)$/i.test(s) ||
    /^-?\d+(\.\d+)?$/.test(s) ||
    s !== s.trim();
  return needsQuote ? JSON.stringify(s) : s;
};

/** Serialize an ordered list of [key, value] pairs (value may be a nested object) as frontmatter. */
export const stringifyFrontmatter = (pairs) => {
  const out = ["---"];
  for (const [key, value] of pairs) {
    if (value === undefined || value === null) continue;
    if (Array.isArray(value)) {
      out.push(`${key}:`);
      for (const item of value) out.push(`  - ${yamlScalar(item)}`);
    } else if (typeof value === "object") {
      out.push(`${key}:`);
      for (const [k, v] of Object.entries(value)) if (v !== undefined && v !== null) out.push(`  ${k}: ${yamlScalar(v)}`);
    } else {
      out.push(`${key}: ${yamlScalar(value)}`);
    }
  }
  out.push("---");
  return out.join("\n");
};
