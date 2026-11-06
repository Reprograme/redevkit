// Claude Code target: skills in .claude/skills, personas as subagents in .claude/agents (D17).
import { asList, stringifyFrontmatter } from "../frontmatter.js";

export const id = "claude";
export const label = "Claude Code";

export const paths = {
  skillDir: (name) => `.claude/skills/${name}`,
  skillFile: (name) => `.claude/skills/${name}/SKILL.md`,
  persona: (name) => `.claude/agents/${name}.md`,
};

export const placeholders = {
  CMD: (x) => `/${x}`,
  SKILL: (x) => paths.skillFile(x),
  SKILLDIR: (x) => paths.skillDir(x),
  PERSONA: (x) => paths.persona(x),
  DELEGATE: (x) => `delegate to the \`${x}\` subagent with the Agent tool (\`subagent_type: "${x}"\`)`,
  ARGS: () => "$ARGUMENTS",
  ASK: () =>
    [
      "**Asking the user:** use the AskUserQuestion tool. One question at a time, at most 3 options,",
      "the recommended option first and labeled \"(Recommended)\", at most 5 questions in this command.",
      "Ask only what changes scope or architecture and record every assumption. In `--auto` or",
      "non-interactive runs (`claude -p`), do not ask: adopt the recommendation and record it as an",
      "assumption. Gates G1-G7 always stop for the user.",
    ].join("\n"),
};

/** Frontmatter for a skill (command, phase, memory or knowledge). */
export const skillFrontmatter = (kind, data) => {
  const pairs = [
    ["name", data.name],
    ["description", data.description],
  ];
  if (kind === "command" || kind === "memory") {
    if (data["argument-hint"]) pairs.push(["argument-hint", data["argument-hint"]]);
  }
  if (kind === "phase") pairs.push(["user-invocable", false]);
  if (data.invocation === "user-only") pairs.push(["disable-model-invocation", true]);
  if (kind === "knowledge" && data.paths) {
    const list = asList(data.paths);
    if (list.length) pairs.push(["paths", list]);
  }
  return stringifyFrontmatter(pairs);
};

/** Subagent file `.claude/agents/<name>.md`. */
export const personaFile = (data, body) => {
  const pairs = [
    ["name", data.name],
    ["description", data.description],
  ];
  const tools = asList(data.tools);
  if (tools.length) pairs.push(["tools", tools.join(", ")]);
  pairs.push(["model", "inherit"]);
  const skills = asList(data.skills);
  if (skills.length) pairs.push(["skills", skills]);
  return `${stringifyFrontmatter(pairs)}\n${body.replace(/^\n+/, "\n")}`;
};

/** Thin skill that points at the subagent (D17). */
export const personaSkill = (data) => {
  // Short on purpose (RC1 catalog budget): the subagent's own description is already listed by
  // the Agent tool, so the pointer skill only needs to be findable by name.
  const fm = stringifyFrontmatter([
    ["name", data.name],
    ["description", `Persona pointer: delegate to the ${data.name} subagent.`],
  ]);
  return `${fm}

# ${data.name} (persona)

This skill is a pointer to the \`${data.name}\` specialist.

- To delegate work to it, use the Agent tool with \`subagent_type: "${data.name}"\`.
- Its full instructions are in \`${paths.persona(data.name)}\`. If you cannot delegate, read
  that file and apply it inline.
- Subagents never ask the user directly; they return open questions to the caller.
`;
};

export const extraFiles = () => [];
