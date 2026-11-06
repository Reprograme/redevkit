// OpenAI Codex target: skills in .agents/skills, personas as custom agents in .codex/agents (D18).
import { stringify as tomlStringify } from "smol-toml";
import { stringifyFrontmatter } from "../frontmatter.js";

export const id = "codex";
export const label = "Codex";

export const paths = {
  skillDir: (name) => `.agents/skills/${name}`,
  skillFile: (name) => `.agents/skills/${name}/SKILL.md`,
  persona: (name) => `.codex/agents/${name}.toml`,
};

export const INTERNAL_PREFIX = "[internal] ";

export const placeholders = {
  CMD: (x) => `$${x}`,
  SKILL: (x) => paths.skillFile(x),
  SKILLDIR: (x) => paths.skillDir(x),
  PERSONA: (x) => paths.persona(x),
  DELEGATE: (x) =>
    `spawn the \`${x}\` agent with \`spawn_agent\` (\`agent_type: "${x}"\`); if custom agents are unavailable (for example in an untrusted project), read \`${paths.persona(x)}\` and apply its \`developer_instructions\` inline`,
  ARGS: () => "the request the user wrote alongside this skill invocation",
  ASK: () =>
    [
      "**Asking the user:** if the `request_user_input` tool is available (Plan mode, or Default mode",
      "with `features.default_mode_request_user_input`), use it: one question, at most 3 options, the",
      "recommended option first and labeled \"(Recommended)\". Otherwise ask ONE plain-text question that",
      "states your recommendation and why, with the alternatives in prose (no numbered multiple choice).",
      "At most 5 questions in this command; ask only what changes scope or architecture and record every",
      "assumption. In `codex exec`, `--auto` or other non-interactive runs, do not ask: adopt the",
      "recommendation and record it as an assumption. Gates G1-G7 always stop and report to the user.",
    ].join("\n"),
};

export const skillFrontmatter = (kind, data) => {
  const description = kind === "phase" ? `${INTERNAL_PREFIX}${data.description}` : data.description;
  const pairs = [
    ["name", data.name],
    ["description", description],
  ];
  if (data["short-description"]) pairs.push(["metadata", { "short-description": data["short-description"] }]);
  return stringifyFrontmatter(pairs);
};

/** Custom agent TOML generated with a TOML library (H6). */
export const personaFile = (data, body) =>
  tomlStringify({
    name: data.name,
    description: data.description,
    developer_instructions: body.trim() + "\n",
  }) + "\n";

/** Extra files for a skill (D28: explicit-only invocation through agents/openai.yaml). */
export const extraFiles = (kind, data) => {
  if (data.invocation === "user-only") {
    return [[`${paths.skillDir(data.name)}/agents/openai.yaml`, "policy:\n  allow_implicit_invocation: false\n"]];
  }
  return [];
};
