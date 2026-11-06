---
name: redevkit-checklist
description: Write a requirements-quality checklist for one domain from spec.md.
---

# redevkit-checklist

Internal phase. Writes "unit tests for requirements": a checklist that checks whether the
spec's requirements in one domain are complete, clear, consistent and measurable. It never
tests the implementation. Called by `{{CMD:redevkit-plan}}` when the risk calls for it (UI,
security, public API, performance).

Write the checklist in the project language ({{LANG}}).

## Input (from the calling command)

- Feature directory (default: the active feature in `.redevkit/memory/active.md`).
- Domain: `ux`, `security`, `api`, `performance`, `data`, `accessibility` or another short
  name.
- Optional: depth (`standard` or `release-gate`), audience (author or reviewer), must-have
  items.
- `--auto` flag, if the command runs in auto mode.

## Prerequisites (T2)

Only `spec.md` is required. `plan.md` and `tasks.md` are read when they exist and only add
context. If `spec.md` is missing, stop and tell the caller to run the specify step of
`{{CMD:redevkit-plan}}`.

## Ownership

- Domain checklists are reviewer-owned. `[x]` means a reviewer judged the requirement
  quality criterion satisfied; it never means the work is done.
- This phase creates or appends items and leaves them all unchecked `[ ]`.
- `checklists/requirements.md` belongs to `redevkit-specify` and `redevkit-clarify`; never
  write domain items into it.

## Steps

### 1. Resolve the template (T10)

Use `.redevkit/templates/overrides/checklist.md` if it exists, otherwise
`.redevkit/templates/checklist.md`. This is the only template source.

### 2. Clarify intent only if needed

If the domain, depth or scope is unclear, ask at most 3 questions, one at a time, each with
a recommendation; they count toward the command's limit of 5. Never ask what the caller
already said. Defaults: depth `standard`, audience reviewer, focus on the two most relevant
risk areas.

{{ASK}}

### 3. Load context

Read the spec sections relevant to the domain; summarize instead of copying. Add plan and
tasks details only when they exist and matter.

### 4. Write the file

Target: `checklists/<domain>.md` (create `checklists/` if needed).

- New file: start at `CHK001`.
- Existing file: append, continuing after the last `CHK` ID. Never delete or rewrite
  existing items.

### 5. Write the items

Group them by quality dimension: Completeness, Clarity, Consistency, Acceptance criteria
quality, Scenario coverage (primary, alternate, error, recovery, non-functional),
Non-functional requirements, Dependencies and assumptions, Ambiguities and conflicts.

- Each item is a question about what is written (or missing) in the spec, with its
  dimension in brackets and a reference: `[Spec §FR-004]`, or `[Gap]`, `[Ambiguity]`,
  `[Conflict]`, `[Assumption]`. At least 80% of items carry a reference.
- Soft cap of 40 items: merge near-duplicates, prioritize by risk.

### 6. Self-check

No item tests behavior: nothing starting with "Verify", "Test", "Confirm" or "Check" plus an
implementation action; no "displays correctly", "click", "renders", "returns 200"; no
frameworks or APIs.

## Item examples

| Wrong (tests the implementation) | Right (tests the requirement) |
| --- | --- |
| Verify the page shows 3 cards | Are the number and layout of featured cards specified? [Completeness, Spec §FR-001] |
| Test hover states on desktop | Are hover state requirements consistent for all interactive elements? [Consistency] |
| Confirm the API returns 401 | Are error responses specified for every authentication failure? [Gap] |
| Check the page loads fast | Is "fast" quantified with a timing threshold? [Clarity, Spec §SC-002] |

Domain starters:

- **ux**: visual hierarchy measurable; interaction states; keyboard and screen-reader
  requirements; empty, loading and error states; alignment with `DESIGN.md` tokens.
- **security**: authentication for every protected resource; data protection for
  sensitive fields; threat model documented; breach and failure response.
- **api**: error formats for every failure; rate limits quantified; auth consistent across
  endpoints; versioning; timeouts and retries for dependencies.
- **performance**: metrics quantified per critical journey; load conditions; degradation
  behavior.

## Report to the caller

Path of the checklist, created or appended, item count, focus areas, depth, audience, and
the must-have items included.
