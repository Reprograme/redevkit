---
name: redevkit-new
description: Initialize a new or existing project - memory, legacy import, domain and constitution. Run once.
short-description: Initialize project memory and constitution
argument-hint: "[--auto] [new|existing] [project description]"
---

# redevkit-new

**Input:** {{ARGS}}

Flags: `--auto` continues to the plan after the constitution gate. The rest of the input is
an optional project description. Write every artifact in {{LANG}}; answer the user in the
user's language.

## Purpose

Set the project up once: decide whether it is new or existing, create or load the project
memory in `.redevkit/memory/`, import legacy memory when the user chooses to, detect the
domain and ratify the constitution inside the memory. This command writes no spec and no
code, never runs `git init` and never commits.

## Preconditions

- `.redevkit/manifest.json` exists (written by `npx redevkit init`). If not, tell the user to
  run `npx redevkit init` first and stop.
- Templates resolve per T10: `.redevkit/templates/overrides/<name>` if it exists, otherwise
  `.redevkit/templates/<name>`.

## Memory phase 1

- If `.redevkit/memory/MEMORY.md` does not exist, skip recall: this run is the bootstrap.
- Otherwise recall per `{{SKILL:redevkit-memanager}}` (`MEMORY.md`, `active.md`, the
  invariants in `system.md`, `tech.md`) and read `.redevkit/memory/constitution.md`. Print
  `📖 Memory loaded. Last entry: YYYY-MM-DD.`

## Questions

This is the only command with a Socratic interview (D36). Ask only what changes scope or
architecture, one question at a time, at most 3 options with the recommended one first and
marked "(Recommended)". At most 5 questions in this run: the new-or-existing question counts;
the gate confirmations (G1, G7) do not. Record every answer and assumption in the memory file
it affects. Subagents never ask: they return their question to you. In `--auto` or
non-interactive runs, adopt the recommendation and record it as an assumption, except at G1
and G7, where the run stops and waits for the user.

{{ASK}}

## Steps

### 1. Detect

Collect facts before asking anything (read-only):

| Fact | Where to look |
| --- | --- |
| Code and manifests | `package.json`, `pyproject.toml`, `requirements.txt`, `go.mod`, `Cargo.toml`, `*.csproj`, `*.sln`, `pom.xml`, `build.gradle`, `Gemfile`, `composer.json`, `pubspec.yaml`, source folders such as `src/`, `app/`, `lib/` |
| REDEVKIT memory | `.redevkit/memory/MEMORY.md`, `.redevkit/memory/constitution.md` |
| Legacy memory | `memory-bank/`, `.agents/memory/`, `.specify/memory/` |
| Git | `git rev-parse --is-inside-work-tree` (read-only; never `git init`) |

### 2. New or existing

Skip this question when the input already says "new" or "existing". Otherwise ask whether the
project is new or existing. Recommend **Existing** when code or manifests were found,
**New** otherwise, and state the evidence in one line.

### 3. Memory already initialized

If `MEMORY.md` and `constitution.md` already exist, do not bootstrap. Ask:

1. Resync the memory with the repository (Recommended)
2. Amend the constitution
3. Exit without changes

- **Resync:** run the `sync` operation of `{{SKILL:redevkit-memanager}}`, report what changed,
  then regenerate `MEMORY.md` as step 9 describes. Do not touch `active.md` › Active feature.
- **Amend:** follow `{{SKILL:redevkit-constitution}}` in `amend` mode (semver bump, Sync
  Impact Report in `changelog.md`). Gate G1. Then regenerate `MEMORY.md` as step 9 describes.
  Do not touch `active.md` › Active feature.
- **Exit:** stop. Nothing is written.

### 4. Bootstrap the memory

Run the `bootstrap` operation of `{{SKILL:redevkit-memanager}}`: it creates the core files of
`.redevkit/memory/` from the {{LANG}} templates. Fields that depend on the user start as
`<PENDING INTERVIEW — reason>` (in pt-BR: `<PENDENTE DE ENTREVISTA — motivo>`).

### 5. Legacy memory (G7)

If step 1 found `memory-bank/`, `.agents/memory/` or `.specify/memory/` — unless
`active.md` › Workflow preferences already records "do not import" for that source, in which
case skip it without asking:

1. Read `{{SKILLDIR:redevkit-memanager}}/references/legacy-import.md`.
2. Show the source → target map for the files actually found.
3. Ask (gate G7, also in `--auto`):
   1. Import and archive (Recommended) — originals go to `.redevkit/memory/archive/<origin>-<date>/`
   2. Import and keep the originals in place
   3. Do not import
4. Run the `import` operation exactly as the reference describes. Nothing is deleted.
   "Do not import" is recorded in `active.md` › Workflow preferences so it is not asked
   again.
5. If a legacy constitution is imported, it keeps its version; step 8 then reviews it as an
   amendment instead of creating v1.0.0.

### 6. Fill project facts

**Existing project — discovery.** Delegate in parallel (disjoint, read-only work):

- Map structure, manifests, scripts, test, build and dev commands, dev port, CI and deploy
  files: {{DELEGATE:explorer-agent}}.
- Describe architecture, patterns in use, code conventions and invariants evident in the code:
  {{DELEGATE:code-archaeologist}}.

Write to `tech.md`, `system.md` and `project.md` **only facts stated explicitly** in code,
manifests or docs, citing the source file. Everything else gets
`<PENDING INTERVIEW — reason>` in {{LANG}}. Spend the remaining question budget on the most
important markers (objective, success criteria, out of scope). In `--auto` the markers stay.

**New project — short interview.** Generate up to 5 questions (fewer when step 2 asked) with
`{{SKILLDIR:redevkit-clarify}}/references/dynamic-questioning.md`, each with a recommendation:
problem and objective, audience, MVP scope and success criteria, platform constraints, out of
scope. Write `project.md` (Scope, Core objective, Success criteria, Out of scope, Problem,
Audience, What "working well" means, Expected experience, Domain). Leave the stack for the
plan: write "decided in `{{CMD:redevkit-plan}}`" under Stack in `tech.md`.

### 7. Domain detection

Follow `{{SKILL:redevkit-route}}` on the description and the facts from step 6. Announce the
domain, persona and skills in one line. Load the domain knowledge skills (for example
`{{SKILL:game-development}}` plus the platform reference
`{{SKILLDIR:game-development}}/references/2d-games.md`) **only** to propose principles and
technical constraints (engine, FPS target, platform, compliance). Do not design or plan here.
Record the domain in `project.md` › Domain and the constraints in `tech.md` › Technical
constraints.

### 8. Constitution (G1)

Follow `{{SKILL:redevkit-constitution}}` to write `.redevkit/memory/constitution.md` v1.0.0
(or the reviewed imported version):

- Test-First is a MUST principle by default (D37). Waiving it requires an explicit user
  choice, recorded as an amendment.
- Domain principles from step 7 are proposed, not imposed.
- Show the draft and ask for approval (gate G1). Without approval, write nothing to
  `constitution.md` and stop.

### 9. Index and state

- `active.md` (only after a bootstrap in step 4): `- Feature: none` (pt-BR:
  `- Feature: nenhuma`), `- Plan approved: no`, `- Verify pending: no`, `- Correction cycle:`
  with both counters at 0; Next steps. In `--auto`,
  record the input description as the first MVP feature (`MVP: <description>`) for the
  plan.
- `MEMORY.md`: regenerate the index through `{{SKILL:redevkit-memanager}}` (entries
  `- [type] summary → file.md`, one per core file).

## Gates that apply

| Gate | Where |
| --- | --- |
| G1 | Step 8 (creation) and step 3 (amendment) |
| G7 | Step 5, legacy memory choice |
| G4 | Not expected: this command deletes nothing and moves legacy files only as chosen at G7 |

## Artifacts

- `.redevkit/memory/` core files: `MEMORY.md`, `constitution.md`, `project.md`, `system.md`,
  `tech.md`, `active.md`, `changelog.md`, `user.md`.
- `.redevkit/memory/archive/<origin>-<date>/` when the user chose "import and archive".

## Memory phase 3

Bootstrap writes the core files directly (no recall needed). At the end, save per
`{{SKILL:redevkit-memanager}}`: `active.md` (event and next steps), `changelog.md` (memory
initialized, constitution ratified, import summary), `user.md` (language and workflow
preferences stated), `MEMORY.md`. The constitution and invariants are written only after
their confirmation (G1). Print `💾 Memory updated (files).`

## Evidence rule

Report only what was read or run: list detected manifests and legacy folders by path, cite the
source file for every discovered fact, and never present a pending marker as a fact.

## Handoff

- Idea still vague (objective or success criteria pending, or the user is unsure what to build
  first) → `{{CMD:redevkit-brainstorm}}` to assess the idea.
- Otherwise → `{{CMD:redevkit-plan}}` with the first feature.
- `--auto`: after G1 approval, continue with `{{CMD:redevkit-plan}}` `--auto` using the MVP
  description (chain: new → plan → create or enhance → test).
- Memory resync or exit only: `{{CMD:redevkit-status}}` to review the state.
