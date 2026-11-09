---
name: redevkit-plan
description: Plan a feature - spec, domain routing, plan, DESIGN.md gate, TDD tasks, analysis and approval.
short-description: Plan a feature (spec to tasks)
argument-hint: "[--auto] <feature description>"
---

# redevkit-plan

**Input:** {{ARGS}}

Flags: `--auto` adopts recommendations and continues to the create command after approval.
The rest of the input is the feature description (or the brief from a brainstorm `decision.md`). Write
every artifact in {{LANG}}; answer the user in the user's language.

## Purpose

Answer WHAT (spec), IN WHAT ORDER (plan, tasks) and WHO (persona per task) for one feature
(D22). The spec is born here. The run ends at the plan approval gate (G2). No application code
is written.

## Preconditions

- Memory initialized (`.redevkit/memory/constitution.md` exists). If not, suggest
  `{{CMD:redevkit-new}}` and stop.
- Empty input and no active feature: ask for the feature description (or suggest
  `{{CMD:redevkit-brainstorm}}` when the idea is vague).
- Templates resolve per T10: `.redevkit/templates/overrides/<name>` if it exists, otherwise
  `.redevkit/templates/<name>` (`spec.md`, `plan.md`, `tasks.md`, `checklist.md`, `design.md`).

## Memory phase 1

Recall per `{{SKILL:redevkit-memanager}}`: `MEMORY.md`, `active.md`, the invariants in
`system.md`, `tech.md` (stack and setup), `project.md` (scope, out of scope). Read
`.redevkit/memory/constitution.md` before planning. Print
`📖 Memory loaded. Last entry: YYYY-MM-DD.`

## Questions

Ask only what changes scope or architecture, one question at a time, at most 3 options with
the recommended one first and marked "(Recommended)". At most 5 questions in the whole run;
the phases (clarify, design) share this budget, ordered by impact. Gate approvals do not
count. Record every assumption in the spec's Assumptions section or in `research.md`.
Subagents never ask: they return their question to you. In `--auto` or non-interactive runs,
adopt the recommendation and record it as an assumption, except at gates (G2, G3, G4).

{{ASK}}

## Steps

### 1. Specify

Run when there is no active feature or the input describes another feature (if unclear, ask:
new feature (Recommended when the input names new behavior) or continue the active one).

1. Follow `{{SKILL:redevkit-specify}}`: next `NNN` (highest 3-digit prefix in `specs/` + 1,
   D53) and short-name; `specs/NNN-short-name/spec.md`; the `checklists/requirements.md`
   quality loop; at most 3 `[NEEDS CLARIFICATION]` markers, resolved inside the phase.
2. The phase records the active feature in `active.md` (`- Feature: specs/NNN-short-name`, phase `specify`, `- Plan approved: no`).
3. **Branch offer (D38).** The specify phase owns it (preference `always | never | ask` in
   `active.md` › Workflow preferences); do not ask again here.

Continuing an existing feature: skip this step, but `spec.md` must exist (T7); if it does not,
run this step.

### 2. Domain routing

Follow `{{SKILL:redevkit-route}}` for each part of the feature (UI, API, data, game, mobile,
security, …). Announce the choice in one line per part (persona + skills + references). Load
the chosen knowledge skills for the plan. Consult domain personas for their part (for example
{{DELEGATE:database-architect}} for the data model); they return findings, never questions.
Record the routing table in `plan.md` › Technical Context.

### 3. Plan

Write the plan with the project planner: {{DELEGATE:project-planner}}. Follow
[plan-stage](references/plan-stage.md) exactly. In short:

- **Re-run detection (T7):** if `plan.md` exists, ask: update it (Recommended) or recreate it.
- `plan.md` from the template: Summary, Technical Context (unknowns marked
  `NEEDS CLARIFICATION`), **Project Type**, Constitution Check, Project Structure, Complexity
  Tracking.
- New application: `{{SKILL:app-builder}}` picks the stack and the scaffolding template; the
  decision goes to `research.md`.
- Phase 0 → `research.md` (Decision, Rationale, Alternatives considered); every
  `NEEDS CLARIFICATION` resolved.
- Phase 1 → `data-model.md`, `contracts/` (only when there are external interfaces),
  `quickstart.md` (runnable validation scenarios, no implementation code).
- **Constitution Check** before Phase 0 and again after Phase 1: an unjustified violation
  stops the run (G3); a justified one is recorded in Complexity Tracking.

### 4. DESIGN.md gate (D39)

If the feature has a UI (screens, components, pages, HUD, mobile views):

1. Follow `{{SKILL:design-spec}}`; read `{{SKILLDIR:design-spec}}/references/collection.md`
   first.
2. Create `DESIGN.md` at the project root from the `design.md` template (T10) when it does not
   exist; otherwise update it in place. There is only one `DESIGN.md`.
3. Add the section **Design Source-of-Truth** to `plan.md` with this feature's deltas
   (tokens, components, screens, states) pointing at `DESIGN.md`.

No UI: write "Design Source-of-Truth: not applicable (no UI)" in `plan.md`.

### 5. Tasks

Follow `{{SKILL:redevkit-tasks}}` → `tasks.md`: phases Setup, Foundational, US1..n, Polish;
in each user story the failing tests come first (D37) unless the constitution waives TDD by
amendment; one line per task:
`- [ ] T001 [P] [US1] description — path — @persona — VERIFY: criterion`. Personas come from
step 2. A new application gets its scaffolding tasks in Setup.

### 6. Analyze

Follow `{{SKILL:redevkit-analyze}}` (read-only): duplication, ambiguity, coverage,
constitution. Fix every CRITICAL finding in `spec.md`, `plan.md` or `tasks.md` and run the
analysis again, within the round limit and stop rule the analyze phase defines (constitution
findings stop at G3). Report the remaining non-critical findings.

### 7. Domain checklist (optional)

When the risk calls for it (authentication, payments, personal data, public API, UI-heavy
feature), follow `{{SKILL:redevkit-checklist}}` for the domain (`security`, `api`, `ux`, …) →
`checklists/<domain>.md`. In `--auto`, generate it whenever one of those triggers matches.
Domain checklists are informational: they never block implementation.

### 8. Plan approval (G2)

Present: feature summary, stack and Project Type, Constitution Check result, design deltas,
task count per phase, analysis result, assumptions taken. Ask for approval (approve, or
request changes). On approval, set `active.md` › Active feature to phase `plan approved` and
`- Plan approved: YYYY-MM-DD` (the label stays in English in every language); later phases
change the phase line but never this one. Without
approval, apply the requested changes and repeat steps 5–8. The chain stops here even in
`--auto`; in a non-interactive run, end the run and report that approval is pending.

## Gates that apply

| Gate | Where |
| --- | --- |
| G2 | Step 8, always |
| G3 | Steps 3 and 6, unjustified constitution violation |
| G4 | Recreating an existing `plan.md` or rewriting `DESIGN.md` sections owned by other features needs explicit confirmation |

## Artifacts

- `specs/NNN-short-name/`: `spec.md`, `checklists/requirements.md`, `plan.md`, `research.md`,
  `data-model.md`, `contracts/`, `quickstart.md`, `tasks.md`, `checklists/<domain>.md`
  (optional).
- `DESIGN.md` at the project root (UI features).

## Memory phase 3

Save per `{{SKILL:redevkit-memanager}}`: `active.md` (active feature, phase, next steps,
workflow preference for branches), `tech.md` (stack, commands decided, `- Project type:` from `plan.md`), `system.md` (design
decisions; new or changed invariants only after confirmation), `changelog.md` (short ADR for
stack and architecture decisions), `project.md` when the visible scope changes, `MEMORY.md`.
Print `💾 Memory updated (files).`

## Evidence rule

Report the paths of every artifact written and the analysis result as counts per severity.
Stack and library claims in `research.md` cite their source (docs, existing code, manifest).
Never mark a Constitution Check as passed without listing each principle checked.

## Handoff

- Approved → `{{CMD:redevkit-create}}` to implement the tasks.
- Changes requested → stay in `{{CMD:redevkit-plan}}`.
- Spec still ambiguous → `{{CMD:redevkit-brainstorm}}` (clarify mode), then back here.
- `--auto`: after the user approves at G2, continue with `{{CMD:redevkit-create}}` `--auto`
  (chain: create → test).
