---
type: bug-fix
---

# Bug fix: [SHORT TITLE]

- **Slug**: [SLUG]
- **Fixed**: [YYYY-MM-DD]
- **Assessment**: `assessment.md` (same directory)
- **Status**: [applied | partial | not-applied]

<!--
Keep these tokens in English: applied, partial, not-applied, PASS, FAIL, SKIPPED,
clean, dirty.
-->

## Summary

[One or two sentences: what changed and why it removes the root cause.]

## Regression test (written first)

- **Test**: `[path/to/test::name]`
- **Command**: `[COMMAND]`
- **Before the fix**: FAIL
- **Fails for the right reason**: [yes — the assertion matches the symptom / no — explain]
- **After the fix**: PASS
- **Test-first waiver**: [none / constitution amendment that waives it; test added after the fix]

```text
[FAILING OUTPUT BEFORE THE FIX]
```

```text
[PASSING OUTPUT AFTER THE FIX]
```

## Changes

| File | Change | Notes |
| --- | --- | --- |
| `[path/to/file]` | [added / modified / removed] | [NOTE] |
| `[path/to/test]` | added test | [NOTE] |

## Light verification

| Check | Command | Result | Notes |
| --- | --- | --- | --- |
| Regression test | `[COMMAND]` | PASS / FAIL | [NOTE] |
| Tests for changed modules | `[COMMAND]` | PASS / FAIL / SKIPPED ([REASON]) | [N passed, N failed] |
| Lint / type-check | `[COMMAND]` | PASS / FAIL / SKIPPED ([REASON]) | [NOTE] |

## Code state

- **Commit (HEAD)**: `[SHA]` or `n/a (not a git repository)`
- **Working tree**: [clean / dirty — changed files]

## Deviations from the assessment

[Scope expansions, a different root cause, a fix that did not hold; or none.]

## Follow-ups

- [Cleanup, monitoring, documentation, similar code to check, or none]
