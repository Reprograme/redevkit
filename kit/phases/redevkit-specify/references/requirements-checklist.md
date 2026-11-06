# Spec quality checklist (`checklists/requirements.md`)

`redevkit-specify` creates this file; `redevkit-clarify` re-validates it. It is a built-in
checklist maintained by the agent, unlike the reviewer-owned domain checklists written by
`redevkit-checklist`.

Write it in the project language. Keep the item order and the `CHK` IDs.

```markdown
---
type: checklist
created: YYYY-MM-DD
updated: YYYY-MM-DD
---

# Specification Quality Checklist: <feature name>

**Purpose**: Validate specification completeness and quality before planning
**Feature**: `specs/NNN-short-name/spec.md`

## Content Quality

- [ ] CHK001 No implementation details (languages, frameworks, APIs)
- [ ] CHK002 Focused on user value and business needs
- [ ] CHK003 Written for non-technical stakeholders
- [ ] CHK004 All mandatory sections completed

## Requirement Completeness

- [ ] CHK005 No [NEEDS CLARIFICATION] markers remain
- [ ] CHK006 Requirements are testable and unambiguous
- [ ] CHK007 Success criteria are measurable
- [ ] CHK008 Success criteria are technology-agnostic
- [ ] CHK009 All acceptance scenarios are defined
- [ ] CHK010 Edge cases are identified
- [ ] CHK011 Scope is clearly bounded
- [ ] CHK012 Dependencies and assumptions identified

## Feature Readiness

- [ ] CHK013 All functional requirements have clear acceptance criteria
- [ ] CHK014 User scenarios cover primary flows
- [ ] CHK015 Feature meets the measurable outcomes in Success Criteria
- [ ] CHK016 No implementation details leak into the specification

## Notes

- Failing items require spec updates before planning continues.
```

## Validation loop

1. For each item, decide pass or fail against the current spec; note the specific issue and
   quote the spec section for every failure.
2. Mark passing items `[x]`, failing items `[ ]`.
3. Fix the spec for each failing item (except CHK005, which `redevkit-clarify` resolves).
4. Repeat at most 3 iterations. If items still fail, list them under Notes and warn the
   caller.
5. When re-validating, toggle only the markers whose state changed; leave every other line
   untouched to avoid noisy diffs.
