---
type: assess-decision
---

# Decision: [SHORT TITLE]

- **Slug**: [SLUG]
- **Decided**: [YYYY-MM-DD]
- **Verdict**: [go | needs-clarification | kill]
- **Artifacts reviewed**: [intake.md, research.md, definition.md, shape.md]

<!--
Keep these tokens in English: go, needs-clarification, kill, strong, adequate, weak, unknown.
A go requires problem validity adequate or better, evidence strength adequate or better
(never weak or unknown) and a recommended option in shape.md. Otherwise the honest verdict
is needs-clarification. A kill is a valid outcome.
-->

## Scorecard

| Criterion | Rating | Justification |
| --- | --- | --- |
| Problem validity | strong / adequate / weak / unknown | [FROM definition.md AND research.md] |
| Evidence strength | strong / adequate / weak / unknown | [FROM research.md] |
| Value vs. cost of inaction | strong / adequate / weak / unknown | [FROM definition.md] |
| Feasibility and appetite fit | strong / adequate / weak / unknown | [FROM shape.md] |
| Strategic fit | strong / adequate / weak / unknown | [CONSTITUTION AND PROJECT GOALS] |
| Risk posture | strong / adequate / weak / unknown | [strong = key risks known and mitigated] |

## Verdict and rationale

[The call and why, in a short paragraph that references the scorecard. Acknowledge every
unknown rating.]

## If needs-clarification

- **Blocking questions**: [NEEDS CLARIFICATION: QUESTION]
- **Revisit stage**: [intake | research | define | shape]

## If kill

- **Decisive reason**: [weak problem, better alternative, cost above value, out of scope,
  superseded]

## If go — brief for redevkit-plan

```text
Feature: [SHORT TITLE]
Problem: [ONE-LINE PROBLEM STATEMENT]
Users: [WHO IS AFFECTED]
Approach: [RECOMMENDED OPTION, CONCEPT LEVEL]
In scope: [SUMMARY]
Out of scope: [SUMMARY]
Success metrics: [METRIC: BASELINE -> TARGET]
Constraints and assumptions: [SUMMARY]
Open questions: [LIST, or none]
Source: .redevkit/assessments/[SLUG]/decision.md
```

## Revisions

<!--
Append-only. When the decision is revisited, add a dated entry here with the new scorecard
and rationale, update the Verdict line in the header and fill the section of the new
verdict. Never rewrite earlier content.
-->

- [YYYY-MM-DD] — [previous verdict -> new verdict]: [what changed and why], or none
