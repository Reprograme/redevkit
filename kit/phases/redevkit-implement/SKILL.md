---
name: redevkit-implement
description: Execute tasks.md phase by phase with TDD, delegating tasks to personas.
---

# redevkit-implement

Internal phase. Executes the active feature's `tasks.md`. Called by
`{{CMD:redevkit-create}}` and `{{CMD:redevkit-enhance}}` (and for appended Convergence tasks
after
`{{CMD:redevkit-verify}}` reports gaps).

The task format, phase headings and TDD rule are defined in
`{{SKILLDIR:redevkit-tasks}}/references/task-format.md`; the phases here are exactly the
phases of that format (T4).

## Input (from the calling command)

- Feature directory (default: the active feature in `.redevkit/memory/active.md`).
- Scope: all unchecked tasks (default), one phase, or a list of task IDs. Blocked `[!]`
  tasks are in scope only when the caller says to retry them.
- `--auto` flag, if the command runs in auto mode.

## Prerequisites

`tasks.md` is required. `plan.md` is required too, except for a lightweight spec created by
the enhance command (D55): when `spec.md` and `tasks.md` exist without `plan.md`, continue and
take the technical context from `.redevkit/memory/tech.md` and `.redevkit/memory/system.md`.
If `tasks.md` is missing (or both `plan.md` and `spec.md` are), stop and point the caller to
`{{CMD:redevkit-plan}}`. Read as well: `spec.md`, `.redevkit/memory/constitution.md`,
`.redevkit/memory/tech.md` (build, test and lint commands), `DESIGN.md` for UI tasks, and
`data-model.md`, `contracts/`, `research.md`, `quickstart.md` when present.

## Steps

### 1. Checklists (read-only)

Never change checklist markers.

- **`checklists/requirements.md`** (spec quality): count `[ ]` and `[x]`. If any item is
  unchecked, ask whether to proceed or stop and fix the spec (Recommended). In `--auto`,
  proceed and record the open items as an assumption.
- **Domain checklists** (`checklists/<domain>.md`) are informational. If any has open
  items, show ONE warning at the start listing them per file (checklist, open count, item
  IDs), then continue: do not stop and do not ask. The verify command lists them under Not
  verified.

{{ASK}}

### 2. Parse `tasks.md`

Phases in file order: Setup, Foundational, US1..n, Polish, then any appended phase
(Enhancement, Convergence). For each task: ID, `[P]`, `[USn]`, paths, persona, VERIFY and
state: open `[ ]`, done `[X]` or blocked `[!]` (with its `BLOCKED` note). Read whether TDD is required (`**TDD**` line in the constitution).

### 3. Ignore files

Before the first Setup task, make sure ignore files match the stack in the plan:
`.gitignore` when `git rev-parse --git-dir` succeeds, `.dockerignore` when Docker is used,
and the linter or formatter ignore settings that exist. Append missing essential patterns
(dependencies, build output, logs, `.env*`); never remove user entries.

### 4. Execute phase by phase

A phase starts when every task of the previous one is `[X]` or blocked `[!]`; tasks that
depend on a blocked task are skipped and stay `[ ]` (step 7). Within a phase:

- Delegate each task to its `@persona` through `{{SKILL:redevkit-orchestrate}}`. Pass the
  task line, the spec and plan excerpts it needs, the files it touches and its VERIFY
  criterion. Never delegate the understanding of the task: the coordinator reads the
  context first and writes a self-contained brief.
- Run `[P]` tasks in parallel only when their paths are disjoint; tasks that touch the
  same file run in order.

### 5. TDD in each user story phase

When TDD is required:

1. Run the tests sub-section tasks: the persona writes the tests.
2. Run the story's tests and confirm they **fail** for the expected reason (missing
   behavior, not a syntax or import error). Keep the command and the failure summary as
   evidence. A test that already passes does not test the new behavior: fix the test
   before continuing.
3. Run the implementation tasks.
4. Run the story's tests and confirm they **pass**. Keep the command and the result. A
   failure follows the retry and blocked-task rules in step 7.

### 6. Mark progress

Change `- [ ]` to `- [X]` for a task only after its VERIFY criterion was observed. Save
`tasks.md` after each task, and report progress after each task.

### 7. Failures

Retries and blocked tasks follow `{{SKILL:redevkit-orchestrate}}`: at most 2 attempts per
task (the first try plus one corrected brief); then the task is marked `[!]` in `tasks.md`
with its `BLOCKED` note (format in `{{SKILLDIR:redevkit-tasks}}/references/task-format.md`),
the tasks that depend on it are skipped, and independent work continues. Report every
blocked task with the error, context and what it needs. A run that completes no task and
leaves only blocked tasks and their dependents ends with that report: the caller never hands
off to itself. A
detected violation of a constitution MUST principle is gate G3: stop and report. Destructive or
irreversible actions (deleting data, rewriting history, dropping tables) are gate G4: ask
the user first. Never commit.

### 8. Light verification (D25)

After the last task in scope, check with evidence:

- build (the build command in `tech.md` or the plan);
- the tests touched by this run;
- lint on the changed files.

Each item is `PASS` with the command and its observed result, `FAIL` with the output
summary, or `SKIPPED (reason)`; never `PASS` without a command that ran.

## Report to the caller

- Tasks completed per phase (`[X]`/total), the tasks left and the blocked tasks (`[!]`).
- TDD evidence per story: failing run, then passing run (commands and summaries).
- Light verification table with evidence.
- Files changed, personas used, blockers and gates hit.
- Progress for the command's memory save (`active.md`: phase and progress).
