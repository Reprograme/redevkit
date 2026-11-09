# Kit authoring guide

This guide is the contract for everything under `kit/`. The CLI renders `kit/` once per
target (Claude Code and Codex). Nobody edits rendered files by hand. `node bin/redevkit.js
validate-kit` enforces most of the rules below.

## 1. Language

- Everything in `kit/` is written in **English** (skills, personas, phases, commands, the
  `AGENTS.md` block), except `kit/templates/pt-BR/`, which is Brazilian Portuguese.
- Artifacts the agent writes (spec, plan, tasks, memory, reports) use the project language
  recorded in `.redevkit/manifest.json` (`lang`). Skills say so with the `{{LANG}}`
  placeholder.
- The agent always answers the user in the user's language.

## 2. Directory layout

| Path | Content | Rendered to (Claude / Codex) |
| --- | --- | --- |
| `kit/commands/redevkit-<cmd>/SKILL.md` | 11 pipeline commands | `.claude/skills/…` / `.agents/skills/…` |
| `kit/phases/redevkit-<phase>/SKILL.md` | 18 internal phases | same, hidden in Claude, `[internal]` in Codex |
| `kit/memory/redevkit-memanager/SKILL.md` | memory skill | same |
| `kit/skills/<name>/SKILL.md` | 39 knowledge skills | same |
| `kit/personas/<name>.md` | 19 personas | `.claude/agents/<name>.md` + thin skill / `.codex/agents/<name>.toml` |
| `kit/context/` | `AGENTS.block.md`, `CLAUDE.<lang>.md` | `AGENTS.md` managed block, `CLAUDE.md` |
| `kit/templates/<lang>/` | artifact templates | `.redevkit/templates/` (chosen language only) |
| `kit/audits/` | Python audits + `README.md` | `.redevkit/audits/` |
| `kit/runtime/` | managed runtime config entries | merged into `.claude/settings.json`, `.codex/config.toml` |

A skill directory holds `SKILL.md` and, optionally, `references/*.md` (one level, Markdown
only). Former sub-skills become `references/<name>.md` and the parent `SKILL.md` keeps a
routing table that points at them with relative links, e.g.
`[2d-games](references/2d-games.md)`. No scripts inside skill directories: every Python
script lives in `kit/audits/`.

## 3. Frontmatter

Frontmatter is a small YAML subset: one `key: value` per line, values on a single line.
Quote a value with double quotes when it contains `:`, `#`, `[`, `{` or starts with a
symbol. Flow lists (`[a, b]`) or comma-separated strings are accepted where a list is
expected. No nested maps, no multi-line values.

### Skills (commands, phases, memanager, knowledge)

```yaml
---
name: redevkit-plan                 # must equal the directory name
description: Plan a feature end to end - spec, routing, plan, DESIGN.md gate, TDD tasks.
short-description: Plan a feature (spec to tasks)   # optional, <= 60 chars; Codex metadata
argument-hint: "[--auto] <feature description>"      # optional; commands only (Claude)
paths: "**/*.tsx, **/*.css"                          # optional; knowledge only (Claude)
invocation: user-only                                # only redevkit-deploy
---
```

Any other key is dropped by the renderer (`version`, `priority`, `trigger`, `when_to_use`,
`effort`, `requires_*`, `artifact_outputs`, `allowed-tools`, `context`, ...). Do not write
them. No skill uses `context: fork`.

**Description rules** (catalog budget, D46): one sentence, "what it does + when to use it",
at most 160 characters, no Markdown. Budget targets (soft): commands <= 130, phases <= 100
(Codex prepends `[internal]`), knowledge <= 120, personas <= 110. The sum per target must
stay under 12,000 characters.

### Personas

```yaml
---
name: game-developer
description: Game development for web, mobile, PC and VR - mechanics, engines, game performance.
tools: Read, Write, Edit, Bash, Grep, Glob
skills: clean-code, game-development     # at most 3, knowledge or phase skill names
---
```

`tools` uses Claude tool names (Read, Grep, Glob, Bash, Write, Edit, Agent, WebFetch,
WebSearch). The renderer adds `model: inherit`. The Codex TOML gets `name`, `description`
and `developer_instructions` (the body); Codex agents inherit the session sandbox.

## 4. Placeholders

Only these placeholders exist. Anything else in `{{...}}` fails validation.

| Placeholder | Claude | Codex |
| --- | --- | --- |
| `{{CMD:x}}` | `/x` | `$x` |
| `{{SKILL:x}}` | `.claude/skills/x/SKILL.md` | `.agents/skills/x/SKILL.md` |
| `{{SKILLDIR:x}}` | `.claude/skills/x` | `.agents/skills/x` |
| `{{PERSONA:x}}` | `.claude/agents/x.md` | `.codex/agents/x.toml` |
| `{{DELEGATE:x}}` | sentence: delegate with the Agent tool, `subagent_type: "x"` | sentence: `spawn_agent` with `agent_type: "x"`, inline fallback from the TOML |
| `{{ASK}}` | paragraph: the AskUserQuestion protocol | paragraph: `request_user_input` or one plain-text question |
| `{{ARGS}}` | `$ARGUMENTS` | "the request the user wrote alongside this skill invocation" |
| `{{LANG}}` | project language (`pt-BR` or `en`) | same |
| `{{VERSION}}` | package version | same |
| `{{#claude}}…{{/claude}}` | kept | removed |
| `{{#codex}}…{{/codex}}` | removed | kept |

Usage rules:

- `{{CMD:x}}`, `{{SKILL:x}}`, `{{SKILLDIR:x}}` and `{{PERSONA:x}}` produce paths or
  invocations relative to the project root. Write them inside backticks, never as Markdown
  link targets: ``Follow `{{SKILL:redevkit-specify}}`.``
- `{{DELEGATE:x}}` is a full clause. Write it in a sentence: `Implement each task:
  {{DELEGATE:backend-specialist}}.` Never inside backticks.
- `{{ASK}}` stands alone on its own line, where the skill first needs to ask the user.
- `{{ARGS}}` appears **exactly once**, only in commands and in `redevkit-memanager`, in a
  line `**Input:** {{ARGS}}` near the top (T6). Phases receive their input from the
  calling command, never from `{{ARGS}}`.
- To point at a reference of another skill: `` `{{SKILLDIR:game-development}}/references/2d-games.md` ``.
- To point at a reference of the same skill: a relative Markdown link
  `[name](references/name.md)`.

## 5. Forbidden content

The validator fails on (case-insensitive): `antigravity`, `gemini`, `run_command`,
`ViewCodeItem`, `FindByName`, `.specify/`, any `/memory/` path not preceded by `.redevkit`
(write `.redevkit/memory/...`), `CODEBASE.md`, leftover `{{...}}` after render, and broken
relative links. Also avoid: `.agents/memory`, `/agents`, `/tasks` slash commands,
`behavioral-modes`, `product-manager` (merged into `product-owner`), `allowed-tools`, any
"Gemini Mode", any tool names that do not exist in Claude Code or Codex.

Exception: legacy memory paths (`memory-bank/`, `.agents/memory/`, `.specify/memory/`) may
appear only in `kit/commands/redevkit-new/SKILL.md` and
`kit/memory/redevkit-memanager/references/legacy-import.md`, which detect and import them.

When an AI search engine must be named (GEO), say "Google AI Overviews" instead of the
forbidden product name.

## 6. Shared paths and names (fixed, use literally)

| Thing | Path |
| --- | --- |
| Project memory | `.redevkit/memory/` (`MEMORY.md`, `constitution.md`, `project.md`, `system.md`, `tech.md`, `active.md`, `changelog.md`, `user.md`, `topics/<topic>.md`, `archive/`) |
| Templates | `.redevkit/templates/<name>`, overridden by `.redevkit/templates/overrides/<name>` |
| Audits | `.redevkit/audits/<script>.py`; interpreter detection in `.redevkit/audits/README.md` |
| Feature artifacts | `specs/NNN-short-name/` (`spec.md`, `plan.md`, `research.md`, `data-model.md`, `quickstart.md`, `tasks.md`, `contracts/`, `checklists/requirements.md`, `checklists/<domain>.md`, `test-report.md`, `verification.md`) |
| Bugs | `.redevkit/bugs/<slug>/{assessment,fix,test}.md` |
| Assessments | `.redevkit/assessments/<slug>/{intake,research,definition,shape,decision}.md` |
| Deploys | `.redevkit/deploys/YYYY-MM-DD-<environment>.md` |
| Design source of truth | `DESIGN.md` at the project root |
| Preview log | `.redevkit/tmp/preview.log` |

Template names (both languages ship the same set):

```text
spec.md  plan.md  tasks.md  constitution.md  checklist.md  design.md
reports/test-report.md  reports/verification.md  reports/deploy.md
reports/bug-assessment.md  reports/bug-fix.md  reports/bug-test.md
assess/intake.md  assess/research.md  assess/definition.md  assess/shape.md  assess/decision.md
memory/MEMORY.md  memory/project.md  memory/system.md  memory/tech.md
memory/active.md  memory/changelog.md  memory/user.md  memory/topic.md
```

Template resolution (T10), to be stated wherever a template is used: use
`.redevkit/templates/overrides/<name>` if it exists, otherwise `.redevkit/templates/<name>`.
Templates use `[FIELD]` or `<FIELD>` for fill-in fields, never `{{...}}`.

## 7. Skill names (closed set)

Commands (11): `redevkit-new`, `redevkit-brainstorm`, `redevkit-plan`, `redevkit-create`,
`redevkit-enhance`, `redevkit-test`, `redevkit-debug`, `redevkit-verify`,
`redevkit-preview`, `redevkit-deploy`, `redevkit-status`.

Memory (1): `redevkit-memanager`.

Phases (18): `redevkit-constitution`, `redevkit-specify`, `redevkit-clarify`,
`redevkit-tasks`, `redevkit-analyze`, `redevkit-checklist`, `redevkit-implement`,
`redevkit-converge`, `redevkit-orchestrate`, `redevkit-route`, `redevkit-bug-assess`,
`redevkit-bug-fix`, `redevkit-bug-test`, `redevkit-assess-intake`,
`redevkit-assess-research`, `redevkit-assess-define`, `redevkit-assess-shape`,
`redevkit-assess-decide`.

Personas (19): `backend-specialist`, `code-archaeologist`, `database-architect`,
`debugger`, `devops-engineer`, `documentation-writer`, `explorer-agent`,
`frontend-specialist`, `game-developer`, `mobile-developer`, `orchestrator`,
`penetration-tester`, `performance-optimizer`, `product-owner`, `project-planner`,
`qa-automation-engineer`, `security-auditor`, `seo-specialist`, `test-engineer`.

Knowledge (39): `api-patterns`, `app-builder`, `architecture`, `bash-linux`,
`batch-operations`, `clean-code`, `code-review-checklist`, `code-review-graph`,
`context-compression`, `database-design`, `deployment-procedures`, `design-spec`,
`documentation-templates`, `frontend-architecture`, `frontend-design`,
`game-development`, `geo-fundamentals`, `i18n-localization`, `lint-and-validate`,
`mcp-builder`, `mobile-design`, `nextjs-react-expert`, `nodejs-best-practices`,
`performance-profiling`, `powershell-windows`, `python-patterns`, `red-team-tactics`,
`rust-pro`, `seo-fundamentals`, `server-management`, `simplify-code`, `skillify`,
`systematic-debugging`, `tailwind-patterns`, `tdd-workflow`, `testing-patterns`,
`vulnerability-scanner`, `web-design-guidelines`, `webapp-testing`.

## 8. Shared protocols (refer to them, do not re-invent)

- **Questions** (D36, D49): ask only what changes scope or architecture; one question at a
  time; at most 3 options with the recommended one first, marked "(Recommended)"; at most 5
  questions per command; record every assumption. Subagents never ask: they return the
  question to the orchestrator. In `--auto` or non-interactive runs, adopt the
  recommendation and record it as an assumption, except at gates G1-G7. Put `{{ASK}}`
  where the skill first asks.
- **Gates** (D29): G1 constitution creation or amendment; G2 plan approval; G3
  constitution violation; G4 destructive or irreversible action; G5 correction cycle without
  convergence (defined only in `redevkit-verify` step 6); G6 deploy (user-triggered only); G7 legacy memory choice. The chain
  always stops at a gate, even with `--auto`.
- **Memory** (§9 of the plan): every command starts with memory phase 1 (recall) and every
  modifying command ends with phase 3 (save) per `{{SKILL:redevkit-memanager}}`. Canonical
  lines: `📖 Memory loaded. Last entry: YYYY-MM-DD.` and `💾 Memory updated (files).`
  (rendered in the user's language by the agent).
- **Evidence** (D05, K12): never claim success without a command that ran and its observed
  result. A skipped audit is `SKIPPED (reason)`, never `PASS`.
- **Handoff** (D29): every command ends with a `## Handoff` section naming the next
  command (`{{CMD:...}}`) and why.
- **Routing**: whoever must choose a persona or skill follows `{{SKILL:redevkit-route}}`.
- **Task line grammar** (`tasks.md`):
  `- [ ] T012 [P] [US1] description — path — @persona — VERIFY: criterion`.
  `[P]` only when files are disjoint from other tasks in the same phase. Phases: Setup,
  Foundational, US1..n, Polish. In each user story, failing tests come first (D37).

## 9. Style

- Markdown that passes markdownlint (the repo config): ATX headings, one H1 per file,
  fenced code blocks with a language, blank lines around lists, headings and fences.
- Lines up to ~100 characters where practical (not enforced for tables).
- Imperative voice, short sections, tables for routing. Keep `SKILL.md` lean and move long
  material to `references/` (progressive disclosure).
- No counts written by hand ("39 skills") in prose that can drift, except in the plan's
  closed lists above.
