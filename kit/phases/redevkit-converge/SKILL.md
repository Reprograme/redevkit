---
name: redevkit-converge
description: Compare code with spec, plan and tasks; append gaps as Convergence tasks.
---

# redevkit-converge

Internal phase. Closes the gap between what the feature's artifacts ask for and what the
code does. Called by `{{CMD:redevkit-verify}}` as its step 2. It assesses the current
code only: no git history, no branch comparison.

## Input (from the calling command)

- Feature directory (default: the active feature in `.redevkit/memory/active.md`).

## Prerequisites

`spec.md`, `plan.md` and `tasks.md` are required, except that a lightweight spec from the
enhance command (D55) has no `plan.md`: then compare against `spec.md`, `tasks.md` and
`.redevkit/memory/tech.md`/`system.md`. If a required file is missing, stop and name the step
of `{{CMD:redevkit-plan}}` that produces it; produce no partial output. Read
`.redevkit/memory/constitution.md` as governing constraints; if it is still an unfilled
template, skip the constitution checks and say so.

## Append-only contract

The only write this phase may make is appending one new
`## Phase N: Convergence` (`## Fase N: Convergência` in pt-BR) section at the end of
`tasks.md`. It must not:

- modify `spec.md` or `plan.md`;
- rewrite, renumber, reorder or delete any existing task, including earlier Convergence
  phases;
- create, modify or delete application code (the appended tasks are for
  `redevkit-implement`).

When nothing remains, `tasks.md` stays byte-for-byte unchanged (no empty header).

## Steps

1. **Load intent** (progressive): from the spec, FR-/SC- items that need buildable work,
   user stories and acceptance scenarios (`US1/AC2`), edge cases; from the plan, decisions,
   data model, contracts and named files; from `tasks.md`, IDs, phases and paths; from the
   constitution, MUST and SHOULD statements and the `**TDD**` line.
2. **Bound the scope.** The files named in the plan and tasks, plus a keyword search for each
   requirement's concepts. Do not assess beyond what the artifacts define.
3. **Assess the code.** Every existing task is part of the intent, checked or not: a `[X]`
   is a claim, not evidence. Check current behavior against the intent, reading the code
   and running the relevant tests when they exist. Record a finding only for a gap:
   - `missing`: the work is absent;
   - `partial`: it exists but does not fully satisfy the requirement;
   - `contradicts`: it conflicts with the intent or a constitution MUST;
   - `unrequested`: code not called for by the artifacts (surfaced for review in the report
     only: it never becomes a task and never blocks `converged`; converge never deletes
     code).

   With little or no code yet, the whole specified scope is `missing`.

   A gap already covered by an open `[ ]` task in an existing Convergence phase is not a new
   finding: list it in the report with that task ID (for example "covered by T042") and do
   not append it again.
4. **Assign severity.** CRITICAL: violates a constitution MUST, or a `missing`/`contradicts`
   gap that blocks a P1 story. HIGH: `missing` or `partial` on a core requirement. MEDIUM:
   `partial` on a secondary requirement, or `unrequested` with unclear justification. LOW:
   polish, low-risk `unrequested`.
5. **Show the findings** before writing anything:

   ```markdown
   ## Convergence Findings

   | ID | Gap type | Severity | Source | Evidence | Remaining work |
   | --- | --- | --- | --- | --- | --- |
   | F1 | missing | HIGH | FR-008 | no score persistence in src/services/score.ts | Persist scores |
   ```

   Add the counts: requirements and acceptance criteria checked, plan decisions checked,
   constitution principles checked (or "skipped - template"), findings by gap type and by
   severity.
6. **Append or report converged.**
   - **New findings** (`tasks_appended`): next ID = highest `T` number + 1; next phase number =
     highest phase number + 1. Write one task per finding except `unrequested`, CRITICAL and constitution
     findings first, following
     the grammar in `{{SKILLDIR:redevkit-tasks}}/references/task-format.md`. Choose the
     persona with `{{SKILL:redevkit-route}}`. Put the trace and gap type in the description:

     ```markdown
     - [ ] T042 [US1] Persist scores per FR-008 (missing) — src/services/score.ts — @backend-specialist — VERIFY: `npx vitest run tests/integration/score.test.ts` passes
     ```

     When a gap has no test yet and TDD is required, add the failing-test task before its
     fix task.
   - **Only gaps already covered** (`tasks_open`): do not touch `tasks.md`; report the
     covering task IDs. This still counts as gaps for the caller.
   - **No gaps at all** (`converged`): do not touch `tasks.md`; report "Converged: the
     implementation satisfies the spec, plan and tasks", with the counts.

## Report to the caller

- Outcome: `converged`, `tasks_appended` (with the phase number and task IDs appended) or
  `tasks_open`.
- The findings table and counts.
- Gaps skipped because an open Convergence task already covers them, with the task IDs.
- CRITICAL constitution findings: gate G3, the calling command stops for the user.
- Next step: `tasks_appended` or `tasks_open` → the calling command hands off to the create
  command, which implements the open Convergence tasks; `converged` → continue the
  verification.
