---
name: redevkit-create
description: Implement the approved tasks of the active feature, one persona per task, tests first.
short-description: Implement the approved feature tasks
argument-hint: "[--auto] [task range, e.g. T001-T020]"
---

# redevkit-create

**Input:** {{ARGS}}

Flags: `--auto` continues to the test command at the end. Optional task range or phase name
limits the run; default is every open task. Write artifacts in {{LANG}}; answer the user in
the user's language.

## Purpose

Build a new feature, including scaffolding, from its approved `tasks.md` (D23). The
orchestrator gives each task to the persona named in it, user story by user story, tests
first. Ends with a light verification (D25) and hands off to the test command.

## Preconditions

- An active feature in `active.md` whose `tasks.md` was approved at G2 (`active.md` phase
  `plan approved` or later). If not, offer `{{CMD:redevkit-plan}}` and stop.
- `spec.md`, `plan.md` and `tasks.md` exist in `specs/NNN-short-name/`.
- UI tasks: `DESIGN.md` exists at the project root. If not, return to the plan's DESIGN.md
  gate.

## Memory phase 1

Recall per `{{SKILL:redevkit-memanager}}`: `MEMORY.md`, `active.md`, the invariants in
`system.md`, `tech.md` (build, test and lint commands). Read
`.redevkit/memory/constitution.md`. Then load `spec.md`, `plan.md`, `tasks.md`, `research.md`,
`data-model.md`, `contracts/`, `quickstart.md` and, for UI work, `DESIGN.md`. Print
`📖 Memory loaded. Last entry: YYYY-MM-DD.`

## Questions

Ask only what changes scope or architecture, one question at a time, at most 3 options with
the recommended one first and marked "(Recommended)", at most 5 questions in this run. Record
every assumption in `tasks.md` (note under the task) or in the final summary. Personas never
ask the user: they return their question to the orchestrator, which asks or, in `--auto` or
non-interactive runs, adopts the recommendation and records it, except at gates.

{{ASK}}

## Steps

### 1. Check readiness

- Open checklists in `checklists/` with unchecked items: list them and ask whether to proceed
  (Recommended: proceed when only non-critical items are open).
- Detect the next open task (`- [ ]`) honoring the requested range.

### 2. Scaffolding (new application)

When `plan.md` records an `app-builder` template, run the Setup tasks with
`{{SKILL:app-builder}}` and that template. Scaffold into an empty or new folder only. If the
scaffold would overwrite existing files, stop for confirmation (G4).

### 3. Implement phase by phase

Follow `{{SKILL:redevkit-implement}}`, which drives `{{SKILL:redevkit-orchestrate}}`:

- Order: Setup → Foundational → US1..n → Polish. A phase starts only when the previous one is
  done.
- Each task goes to the persona in its `@persona` field, for example
  {{DELEGATE:backend-specialist}} for a `@backend-specialist` task. The orchestrator passes
  the task line, the relevant spec and plan excerpts and the files involved; it never
  delegates the understanding of the feature.
- Tasks marked `[P]` whose files are disjoint from the other tasks of the phase run in
  parallel; everything else runs in order.
- **TDD (D37):** in each user story, write its tests first, run them and record that they
  fail for the expected reason; then implement until they pass. Skip only when the
  constitution waives TDD by amendment.
- UI tasks build against the tokens and components in `DESIGN.md`.
- Mark a task `[X]` only after its `VERIFY:` criterion was observed (command and result).
- A task that would violate the constitution stops the run (G3). A destructive or
  irreversible action (deleting files or data, dropping tables, rewriting history) needs
  explicit confirmation (G4).

### 4. Light verification (D25)

On the files changed in this run, with evidence:

1. Build (or type check) with the command from `tech.md`.
2. The tests touched or added in this run.
3. Lint on the changed files.

A failure caused by this run's work is fixed now (same task, same persona). Anything else is
reported under Known problems and left for the test command. This is not the full suite.

### 5. Summary

Report tasks done per phase (`[X]`/total), files changed, light verification results, open
tasks and assumptions taken.

## Gates that apply

| Gate | Where |
| --- | --- |
| G3 | Step 3, a task would violate the constitution |
| G4 | Steps 2 and 3, overwriting files, deleting data or any irreversible action |

## Artifacts

- Application code and tests at the paths named in the tasks.
- `tasks.md` with completed tasks marked `[X]` and notes on assumptions.

## Memory phase 3

Save per `{{SKILL:redevkit-memanager}}`: `active.md` (phase `implementation`, progress per
phase, what works, what is missing, next steps), `changelog.md` (Unreleased › Added),
`tech.md` when dependencies or commands were added, `system.md` when a new pattern appeared
(invariants only after confirmation), `MEMORY.md`. Print `💾 Memory updated (files).`

## Evidence rule

Every `[X]` and every "passes" in the summary is backed by a command that ran and its observed
result (exit code, test counts). The failing-test step of TDD is evidenced too. Never report a
task as done because the code "should work".

## Handoff

- All tasks done → `{{CMD:redevkit-test}}` to map scenarios to tests and run the full suite.
- Tasks still open → `{{CMD:redevkit-create}}` again (or the remaining range).
- `--auto`: continue with `{{CMD:redevkit-test}}` `--auto` automatically.
