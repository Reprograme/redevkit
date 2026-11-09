---
name: redevkit-tasks
description: Generate tasks.md by user story: failing tests first, persona and VERIFY per task.
---

# redevkit-tasks

Internal phase. Turns the active feature's `spec.md` and `plan.md` into an executable,
dependency-ordered `tasks.md`. Called by `{{CMD:redevkit-plan}}` (after the plan and the
`DESIGN.md` gate) and by `{{CMD:redevkit-enhance}}`.

Write the artifact in the project language ({{LANG}}). The line grammar, phase headings and
TDD rule are in [task-format](references/task-format.md): follow it exactly.

## Input (from the calling command)

- Feature directory `specs/NNN-short-name/` (default: the active feature in
  `.redevkit/memory/active.md`).
- Mode: `generate` (default) or `append` (enhance: add a dated phase to an existing file).
- `--auto` flag, if the command runs in auto mode.

## Prerequisites

| File | Need |
| --- | --- |
| `spec.md` | Required: user stories with priorities, acceptance scenarios, FR/SC IDs |
| `plan.md` | Required (stack, structure, Project Type, Domain Routing), except for a lightweight spec from the enhance command (D55): use `.redevkit/memory/tech.md` and `system.md` |
| `.redevkit/memory/constitution.md` | Required: principles and the `**TDD**` line |
| `data-model.md`, `contracts/`, `research.md`, `quickstart.md` | Optional |
| `DESIGN.md` (project root) | Required when the feature has UI |

If `spec.md` is missing, or `plan.md` is missing outside the D55 lightweight case, stop and tell
the caller which step is missing.

## Steps

1. **Resolve the template.** Use `.redevkit/templates/overrides/tasks.md` if it exists,
   otherwise `.redevkit/templates/tasks.md`. Keep its frontmatter valid: the first line is
   `---`, one `key: value` per line, closing `---`, no blank line inside.
2. **Existing file.** If `tasks.md` exists and mode is `generate`, see Existing tasks.md
   below before continuing.
3. **Load context.** From the plan: stack, Project Type, source structure, Domain Routing
   table, Design Source-of-Truth deltas. From the spec: user stories in priority order,
   acceptance scenarios, FR-/SC- IDs, edge cases. From data-model and contracts: entities,
   constraints, interfaces. From the constitution: MUST principles and whether TDD is
   required or waived.
4. **Map work to phases.**
   - Phase 1 Setup: project initialization and shared tooling (scaffolding from the
     `app-builder` template when the plan says new app).
   - Phase 2 Foundational: blocking prerequisites for every story (schema, auth framework,
     routing, base config). Nothing story-specific.
   - One phase per user story, in priority order (P1 first). Map each entity, contract,
     screen and service to the earliest story that needs it.
   - Final phase Polish: docs, cleanup, performance, security hardening, `quickstart.md`
     validation.
5. **Write the tasks of each story phase** (TDD, D37):
   - Tests first: tasks that write failing tests for the story's acceptance scenarios and
     contracts; VERIFY says the test fails before the implementation.
   - Then implementation in dependency order: models → services → endpoints or UI →
     integration. The last task's VERIFY says the story's tests pass.
   - If the constitution waived TDD (`**TDD**: waived`), test tasks are optional; still give
     every task a VERIFY.
6. **Assign a persona to every task.** Follow `{{SKILL:redevkit-route}}` with the task's
   domain and the plan's Domain Routing table. Respect project-type rules (a mobile app's
   UI goes to `@mobile-developer`, a web UI to `@frontend-specialist`). Test tasks usually
   go to `@test-engineer`. Never `@orchestrator`: split a task that spans several domains
   into one task per owner. Do not ask the user about personas; when the route is
   ambiguous, pick the plan's primary persona and note it in the report.
7. **Mark parallelism.** Add `[P]` only when the task's paths are disjoint from all other
   tasks in the same phase and it has no dependency on an unfinished task of that phase.
8. **Write the dependency sections**: phase dependencies, story dependencies (most stories
   independent after Foundational), order within a story, and parallel opportunities.
   Include one parallel example per story with `[P]` tasks.
9. **Write the implementation strategy**: MVP first (Setup + Foundational + US1, then stop
   and validate), then incremental delivery story by story.
10. **Validate before saving.**
    - Every task line matches the grammar in [task-format](references/task-format.md).
    - Every user story from the spec has a phase; every FR has at least one task.
    - With TDD, every story phase starts with failing-test tasks.
    - No sample task from the template remains; no fill-in token remains.
11. **Save** `specs/NNN-short-name/tasks.md`.

## Existing tasks.md

If no task is `[X]`, regenerate the file. If some task is `[X]`, ask with these options:
keep done tasks and their IDs and regenerate only unchecked ones (Recommended); regenerate
everything; keep the file as is.

{{ASK}}

## Append mode

In `append` mode, keep the file intact and add one new phase at the end, continuing IDs and
phase numbers as the reference describes.

## Report to the caller

- Path of `tasks.md`; total tasks; tasks per phase and per story.
- `[P]` opportunities; personas used and how many tasks each.
- Independent test criterion per story; suggested MVP scope (usually US1).
- Format validation result (all lines valid, or the invalid lines).
- Questions asked (they count toward the command's limit of 5) and assumptions made.
