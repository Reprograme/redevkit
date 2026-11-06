---
type: checklist
domain: "[DOMAIN]"
created: "[DATE]"
updated: "[DATE]"
---

# [CHECKLIST TYPE] Checklist: [FEATURE NAME]

**Purpose**: [What this checklist covers]

**Created**: [DATE]

**Feature**: `specs/[###-feature-name]/spec.md`

**Review ownership**: this is a reviewer-owned requirements-quality checklist. Mark an item
`[x]` only when a reviewer judges the requirement-quality criterion satisfied.

**Marker semantics**: `[x]` means the requirement is well written (complete, clear,
consistent, measurable). It does not mean the implementation is done.

<!--
  ============================================================================
  The items below are SAMPLES. The checklist phase replaces them with items built from the
  spec (and plan.md and tasks.md when they exist). Each item asks about the quality of
  what is written, carries its dimension and a reference ([Spec §FR-001], [Gap],
  [Ambiguity], [Conflict], [Assumption]) and starts unchecked.
  Do not keep sample items in the generated file.
  ============================================================================
-->

## Requirement Completeness

- [ ] CHK001 Are error handling requirements defined for every failure mode? [Gap]
- [ ] CHK002 Are accessibility requirements specified for all interactive elements? [Completeness]

## Requirement Clarity

- [ ] CHK003 Is "fast loading" quantified with a timing threshold? [Clarity, Spec §SC-002]

## Requirement Consistency

- [ ] CHK004 Are navigation requirements aligned across all screens? [Consistency, Spec §FR-010]

## Scenario Coverage

- [ ] CHK005 Are requirements defined for the empty state (no data yet)? [Coverage, Gap]
- [ ] CHK006 Are recovery requirements defined when a save fails midway? [Coverage, Exception Flow]

## Notes

- Mark items `[x]` only after review confirms the criterion is satisfied.
- Leave items unchecked while they need clarification or correction; add findings inline.
- The implement phase reads these markers as a gate and never changes them.
- `checklists/requirements.md` is the built-in spec-quality checklist and has its own
  lifecycle (specify and clarify phases).
