---
name: redevkit-enhance
description: Change existing code - spec delta and appended tasks, same engine as create; big changes go to plan.
short-description: Change an existing feature
argument-hint: "[--auto] <change description>"
---

# redevkit-enhance

**Input:** {{ARGS}}

Flags: `--auto` adopts recommendations and continues to the test command. The rest of the
input describes the change. Write artifacts in {{LANG}}; answer the user in the user's
language.

## Purpose

Change something that already exists (D23): record the change as a dated delta in the
feature's spec, append tasks, then implement them with the same engine as the create command
(orchestrator, personas, TDD). A big change is redirected to the plan.

## Preconditions

- Memory initialized (`.redevkit/memory/constitution.md` exists). If not, suggest
  `{{CMD:redevkit-new}}` and stop.
- There is existing code to change. If the project is empty, suggest `{{CMD:redevkit-plan}}`.
- Templates resolve per T10: `.redevkit/templates/overrides/<name>` if it exists, otherwise
  `.redevkit/templates/<name>`.

## Memory phase 1

Recall per `{{SKILL:redevkit-memanager}}`: `MEMORY.md`, `active.md`, the invariants in
`system.md`, `tech.md`. Read `.redevkit/memory/constitution.md`. Print
`📖 Memory loaded. Last entry: YYYY-MM-DD.`

## Questions

Ask only what changes scope or architecture, one question at a time, at most 3 options with
the recommended one first and marked "(Recommended)", at most 5 questions in this run. Record
every assumption in the spec delta. Personas never ask the user: they return the question to
you. In `--auto` or non-interactive runs, adopt the recommendation and record it as an
assumption, except at gates.

{{ASK}}

## Steps

### 1. Understand the current state

Analyze the affected area together with the memory (invariants, stack, conventions):
{{DELEGATE:code-archaeologist}}. Expect back: affected files, dependencies, risks, and
conflicts with the current stack or invariants (for example "use Firebase" in a PostgreSQL
project). Warn about each conflict and ask how to proceed before going on.

### 2. Locate the feature and draft the delta

Search `specs/` for the feature the change belongs to (spec titles, user stories, paths in
`tasks.md`, the active feature in `active.md`).

- **Feature exists:** draft a dated section in its `spec.md` —
  `## Enhancements` › `### YYYY-MM-DD — <title>` with changed or added requirements,
  acceptance scenarios and assumptions. Draft the tasks for `tasks.md` under
  `## Phase N: Enhancement YYYY-MM-DD`, following the rules of `{{SKILL:redevkit-tasks}}`
  (grammar, TDD first, `@persona` from `{{SKILL:redevkit-route}}`, numbering continues).
  Completed tasks are never rewritten. In `pt-BR` artifacts the headings are
  `## Melhorias` › `### AAAA-MM-DD — <título>` and `## Fase N: Melhoria AAAA-MM-DD`. If that
  feature is not the active one, make it active in `active.md` (`- Feature:`, which also
  starts a new Correction cycle line per `{{CMD:redevkit-verify}}` step 6).
- **No feature (D55):** create a lightweight spec with the light mode of
  `{{SKILL:redevkit-specify}}` (next `NNN`, template, only what the change needs: summary, the
  change's user story, acceptance scenarios, requirements delta, assumptions). Tasks follow `{{SKILL:redevkit-tasks}}` for the change only.
  No `plan.md` is written: the technical context comes from `tech.md` and `system.md`, and
  `{{SKILL:redevkit-implement}}` accepts a lightweight spec with `spec.md` + `tasks.md`.
  Record it as the active feature in `active.md` (`- Feature: specs/NNN-short-name`,
  `- Plan approved: no` until step 4).

### 3. Big-change check

The change is big when any of these holds: a new user story with its own flows or actors, a
data model change, an architecture change, a breaking public contract change (changing or
removing API, CLI, schema or event behavior that consumers already rely on), or about 10
tasks or more. Then ask: run the full plan (Recommended) or continue as an enhancement.
Choosing the plan hands the drafted delta to `{{CMD:redevkit-plan}}` as its input and ends
this run.

A small, backward-compatible addition on an existing surface (a new endpoint, an optional
field, a new flag) with fewer than about 10 tasks is **not** big: continue as an enhancement
without asking. When the size is borderline and the user invoked this command, recommend
continuing as an enhancement.

### 4. Approve the change plan

Check the delta against the constitution (violation → G3). Present: affected and new files,
the tasks to append, risks and scope. Ask for approval (approve (Recommended) or request
changes). In `--auto`, the approval is adopted and recorded as an assumption. Then write the
delta and the tasks to the files, and set `active.md` › `- Plan approved: YYYY-MM-DD` (this
approval of the change plan stands in for G2, for an existing feature and for a lightweight
spec).

### 5. Implement

Same engine as the create command: follow `{{SKILL:redevkit-implement}}` with
`{{SKILL:redevkit-orchestrate}}` on the appended phase only — persona per task, `[P]` in
parallel when files are disjoint, failing tests first (D37), `[X]` only after the `VERIFY:`
criterion was observed. Destructive or irreversible actions need confirmation (G4).

### 6. Light verification (D25)

On the changed files, with evidence: build or type check, the touched and new tests, lint.
Fix failures caused by this change; record the rest in `active.md` › Known issues.

## Gates that apply

| Gate | Where |
| --- | --- |
| G3 | Step 4 or 5, the change violates the constitution |
| G4 | Step 5, deleting files or data, migrations that drop data, any irreversible action |

## Artifacts

- `specs/NNN-short-name/spec.md` (`## Enhancements` section) and `tasks.md` (appended phase).
- Lightweight `specs/NNN-short-name/spec.md` + `tasks.md` when no feature existed.
- Changed code and tests.

## Memory phase 3

Save per `{{SKILL:redevkit-memanager}}`: `active.md` (active feature, progress, Known
issues, next steps), `changelog.md` (Unreleased › Changed or Added), `tech.md` and
`system.md` when dependencies or patterns changed (invariants only after confirmation),
`project.md` when the visible scope changed, `MEMORY.md`. Print `💾 Memory updated (files).`

## Evidence rule

Every completed task and every light-verification line shows the command and its observed
result. Conflicts and risks cite the file where they were found.

## Handoff

- Done → `{{CMD:redevkit-test}}` to run the full suite against the spec.
- Redirected at step 3 → `{{CMD:redevkit-plan}}` with the drafted delta.
- `--auto`: continue with `{{CMD:redevkit-test}}` `--auto`; at step 3 the recommendation
  (plan) is adopted and the chain continues with `{{CMD:redevkit-plan}}` `--auto`.
