---
name: redevkit-analyze
description: Read-only consistency check of spec, plan, tasks and constitution.
---

# redevkit-analyze

Internal phase. Finds inconsistencies, duplication, ambiguity, gaps and constitution
conflicts across the active feature's artifacts before implementation. Called by
`{{CMD:redevkit-plan}}` after `redevkit-tasks`.

**Strictly read-only.** Do not modify any file. The output is a report returned to the
caller, which fixes CRITICAL findings and runs this phase again (round limit in "Next
actions for the caller"). Write the report in the user's language.

## Input (from the calling command)

- Feature directory (default: the active feature in `.redevkit/memory/active.md`).
- Optional focus (for example "security coverage").

## Prerequisites

`spec.md`, `plan.md` and `tasks.md` in the feature directory, and
`.redevkit/memory/constitution.md`. If one is missing, report it as CRITICAL, name the step
that produces it, and stop.

## Constitution authority

`.redevkit/memory/constitution.md` is non-negotiable here. A conflict with a MUST principle
is always CRITICAL and is fixed in the spec, plan or tasks, never by weakening the principle.
Changing a principle is a separate amendment through `redevkit-constitution` (gate G1); a
conflict the caller cannot fix in the artifacts stops at gate G3.

## Steps

1. **Load only what is needed.**
   - spec: overview, functional requirements (FR-), success criteria (SC-), user stories
     and acceptance scenarios, edge cases, assumptions, clarifications.
   - plan: stack, Project Type, Domain Routing, Constitution Check (`## Verificação da
     Constituição` in pt-BR), structure, Design Source-of-Truth, Complexity Tracking.
   - tasks: IDs, phases, `[P]`, `[USn]`, paths, `@persona`, `VERIFY:`.
   - constitution: principle names, MUST and SHOULD statements, the `**TDD**` line.
   - `DESIGN.md` at the project root, when the feature has UI.
2. **Build internal models** (never paste raw artifacts into the report): a requirements
   inventory keyed by FR-/SC- IDs (only success criteria that need buildable work), a story
   and acceptance inventory, a task-to-requirement map, and the constitution rule set.
3. **Run the detection passes** (at most 50 findings; summarize the overflow):
   - **A. Duplication**: near-duplicate requirements; mark the weaker wording.
   - **B. Ambiguity**: vague adjectives without numbers; leftover placeholders (TODO,
     `???`, `[NEEDS CLARIFICATION]`, unfilled `[FIELD]`).
   - **C. Underspecification**: requirements without an object or measurable outcome;
     stories without acceptance scenarios; tasks naming files or components absent from
     the spec and plan.
   - **D. Constitution alignment**: any element that conflicts with a MUST principle;
     mandated sections or gates missing; the plan's Constitution Check not citing
     `.redevkit/memory/constitution.md` or citing an older version.
   - **E. Coverage**: requirements with no task; tasks with no requirement or story;
     buildable success criteria (performance, security, availability) with no task.
   - **F. Inconsistency**: terminology drift; entities in the plan but not in the spec (or
     the reverse); task order contradictions; conflicting technology choices.
   - **G. Task contract**: lines that break the grammar in
     `{{SKILLDIR:redevkit-tasks}}/references/task-format.md`; a story phase whose failing
     tests do not come first while TDD is required; `[P]` tasks sharing a file in the same
     phase; a persona that does not fit the route (for example `@frontend-specialist` on
     a native mobile app).
   - **H. Design**: a feature with UI but no `DESIGN.md`, or a plan without its Design
     Source-of-Truth section.
4. **Assign severity.**
   - CRITICAL: violates a constitution MUST (including missing failing tests first while TDD
     is required); a core artifact missing; a requirement with zero coverage that blocks
     baseline functionality.
   - HIGH: duplicate or conflicting requirements; ambiguous security or performance
     attribute; untestable acceptance criterion; task line without `@persona` or `VERIFY:`.
   - MEDIUM: terminology drift; missing non-functional coverage; underspecified edge case.
   - LOW: wording, minor redundancy.
5. **Write the report** (see below). Rerunning on unchanged artifacts must give the same IDs
   and counts.

## Report

```markdown
## Specification Analysis Report

| ID | Category | Severity | Location | Summary | Recommendation |
| --- | --- | --- | --- | --- | --- |
| D1 | Constitution | CRITICAL | tasks.md Phase 3 | US1 has no failing test before T014 | Add failing-test tasks first |

**Coverage**

| Requirement | Has task? | Task IDs | Notes |
| --- | --- | --- | --- |

**Constitution alignment:** <principle → finding, quoting `.redevkit/memory/constitution.md`>
**Unmapped tasks:** <IDs>
**Metrics:** requirements, tasks, coverage %, ambiguities, duplicates, CRITICAL count
```

Finding IDs use the pass letter plus a number (A1, D2, G3).

## Next actions for the caller

- CRITICAL findings: list each with the concrete fix (which file, which section). The caller
  applies the fixes and runs this phase again: **at most 3 analyze rounds** per plan run.
  If CRITICAL findings remain after round 3, the caller stops and asks the user; a
  remaining constitution finding stops at gate G3 instead.
- Only MEDIUM or LOW: the plan may proceed; list improvement suggestions.
- Zero findings: report success with the coverage metrics.
