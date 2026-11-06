---
type: bug-test
---

# Bug verification: [SHORT TITLE]

- **Slug**: [SLUG]
- **Tested**: [YYYY-MM-DD]
- **Assessment**: `assessment.md` (same directory)
- **Fix**: `fix.md` (same directory)
- **Result**: [verified | partial | failed]

<!--
Keep these tokens in English: verified, partial, failed, PASS, FAIL, SKIPPED, clean, dirty.
verified: the original reproduction was exercised and no longer fails, the regression test
passes and the relevant suite is green.
partial: the symptom is gone but a check is inconclusive or skipped (including a reproduction
that could not be exercised), or an unrelated regression appeared.
failed: the symptom still reproduces, or the fix breaks the suite.
-->

## Summary

[One or two sentences: does the bug still reproduce, did the fix hold, any regressions.]

## Checks

| Check | Command or action | Result | Notes |
| --- | --- | --- | --- |
| Original reproduction (after the fix) | `[COMMAND OR STEPS]` | PASS / FAIL / SKIPPED ([REASON]) | [PASS = the symptom no longer occurs] |
| Regression test | `[COMMAND]` | PASS / FAIL | [NOTE] |
| Relevant suite | `[COMMAND]` | PASS / FAIL / SKIPPED ([REASON]) | [N passed, N failed, N skipped] |
| Lint / type-check | `[COMMAND]` | PASS / FAIL / SKIPPED ([REASON]) | [NOTE] |

## Output excerpts

```text
[FINAL SUMMARY LINES OR THE FAILING ASSERTION]
```

## Code state

- **Commit (HEAD)**: `[SHA]` or `n/a (not a git repository)`
- **Working tree**: [clean / dirty — changed files]

## Residual risks

- [Environment not covered, intermittent behavior, or none]

## Recommendation

[Close the bug and continue to redevkit-verify / hold: reproduction inconclusive /
reopen: the symptom still reproduces, assess again with this evidence.]
