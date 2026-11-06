# Classifying a memory fact

How **save** decides whether a fact is kept, which type it has, and which file and section
receive it. Part of [redevkit-memanager](../SKILL.md). All paths are relative to
`.redevkit/memory/`.

## 1. Should it be saved?

| The fact is... | Do |
| --- | --- |
| On the never-write list (secret, credential, log, code snippet, API surface, absolute path, transcript) | Refuse and say why. For a secret, suggest an environment variable or secret manager |
| Derivable from the code or manifests (folder layout, dependency list, function names) | Do not save; point to where the code shows it |
| Ephemeral (one debug session, a temporary workaround already removed) | Do not save; it belongs in the command's report |
| A decision, reason, convention, state, preference or constraint the code does not show | Save it |

## 2. Which type?

| Type | What it holds | Test |
| --- | --- | --- |
| `user` | Who the user is: environment, tools, communication style | True for this person on any project |
| `feedback` | How the user reacted to the agent's output, and how to adjust | A reaction to the agent's work |
| `project` | Decisions, conventions, scope, state and constraints of this project | True for this project, whoever works on it |
| `reference` | Pointers to external resources: docs, dashboards, trackers, environments (never secrets) | Answers "where do I find X?" |

`user.md` is versioned and shared with the team. Personal facts the user does not want shared
stay out of project memory.

## 3. Which file and section?

| Fact | Destination | Confirmation |
| --- | --- | --- |
| Principle or governance rule for every feature | `constitution.md`, only through `{{SKILL:redevkit-constitution}}` | Yes (G1) |
| Rule the current code must respect, whose violation breaks behavior today | `system.md` › Invariants | Yes |
| Architecture or design decision, and its reason | `system.md` › Design decisions | No |
| Technical option dropped for a reason that still holds | `system.md` › Design decisions | No |
| Pattern in use, coding convention | `system.md` › Patterns in use / Code conventions | No |
| How components connect | `system.md` › Component relationships | No |
| Stack, versions that matter, critical dependency and why | `tech.md` › Stack / Dependencies | No |
| Install, build, test or dev command; preview port | `tech.md` › Dev environment | No |
| Platform, performance or compatibility limit | `tech.md` › Technical constraints | No |
| Scope, objective, success criteria, problem, audience, experience, domain | `project.md` › matching section | No |
| Product idea dropped for a reason that still holds | `project.md` › Out of scope | No |
| Current state, recent event, next step, known issue | `active.md` › matching section | No |
| Test or verify result | `active.md` › Last results | No |
| Branch per feature, when to commit | `active.md` › Workflow preferences | No |
| Delivery or release | `changelog.md` › Unreleased | No |
| Decision that needs a long explanation | `changelog.md` › Architecture decisions (short ADR), plus one line in `system.md` › Design decisions while it still binds the code | No |
| OS, shell, editor, other personal tools | `user.md` › Environment and tools | No |
| How the user wants answers | `user.md` › Communication style | No |
| Reaction to the agent's output | `user.md` › Recorded feedback (`- YYYY-MM-DD — what — how to adjust`) | No |
| Detailed knowledge on one theme that would bloat a core file (glossary, third-party service quirks) | `topics/<topic>.md`, with the fact's type | No |
| External link or location | `topics/<topic>.md` with `type: reference` (for example `topics/links.md`) | No |

Tie-breakers:

- `tech.md` says **what** the project uses; `system.md` says **how** it is built with it.
- Invariant or design decision? Ask "if someone violated it today, would something break?"
  Yes: invariant. No: design decision or convention.
- Product decision or technical decision? Product (what users get) goes to `project.md`;
  technical (how it is built) goes to `system.md`.

## 4. Topic files

- Create a topic when one theme gathers several related facts, or when its detail would make a
  core section long, or when no core section fits.
- Name it `topics/<topic>.md`: short, lowercase, ASCII, kebab-case (`topics/payments.md`).
- Search for an existing topic first and append to it when it fits.
- Create it from the template `memory/topic.md`, resolved as in **bootstrap**, set its `type`
  and its dates.

## 5. Index line

- Every topic file has at least one line in `MEMORY.md`, in the section of its type.
- A fact in a core file gets its own index line only when most tasks need it at a glance
  (for example "use pnpm, never npm"). Otherwise the Core line of that file is enough.
- Format: `- [type] summary → file.md`, summary at most 150 characters.

## 6. Duplicates and contradictions

- An equivalent entry already exists: update it in place and set `updated`.
- The new fact contradicts an entry and the user stated it explicitly: the request is the
  confirmation; replace the entry and add an event to `active.md` when the change matters.
- The contradiction comes from the agent's own inference: ask before replacing (it deletes
  content).
- Invariants always need confirmation.

## 7. Examples

| User says | Type | Destination |
| --- | --- | --- |
| "Remember that I use PowerShell on Windows" | `user` | `user.md` › Environment and tools; index `- [user] Windows + PowerShell; give PowerShell commands → user.md` |
| "Too verbose; use tables for comparisons" | `feedback` | `user.md` › Recorded feedback; index line under Feedback |
| "Lembre disso: usamos pnpm, nunca npm" | `project` | `tech.md` › Dev environment (written in the project language); index `- [project] Use pnpm, never npm → tech.md` |
| "IDs are never reused after a deletion" | `project` | `system.md` › Invariants, after restating the rule (confirmation) |
| "We dropped pagination: the lists are small by design" | `project` | `system.md` › Design decisions (current negative decision, never pruned) |
| "No dark mode in the MVP" | `project` | `project.md` › Out of scope |
| "Anote isso: o cliente quer um relatório mensal em PDF" | `project` | `project.md` › Expected experience |
| "The staging dashboard is the 'App' board in Grafana" | `reference` | `topics/links.md`; index line under Reference |
| "We are halfway through the checkout feature; the payment form is done" | `project` | `active.md` › Where we are and What works |
| "Every feature must work offline" | `project` | Constitution amendment: hand over to `{{SKILL:redevkit-constitution}}` (G1) |
| "The API token is ..." | none | Refuse: secret |
| "Tests live in the tests folder" | none | Do not save: the repository shows it |
