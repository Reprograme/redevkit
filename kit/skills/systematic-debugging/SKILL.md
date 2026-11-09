---
name: systematic-debugging
description: Four-phase debugging - reproduce, isolate, root cause, fix behind a failing regression test; use for any bug or failure.
---

# Systematic Debugging

> Adapted from obra/superpowers. No fix without a reproduced failure and an understood root
> cause.

## Overview

A structured approach that prevents random guessing: the problem is reproduced and understood
before anything changes, and the fix is proven by a test that failed first (TDD is the
REDEVKIT default).

## Where the Evidence Goes

Inside the pipeline, `{{CMD:redevkit-debug}}` runs three phases and writes one artifact each
under `.redevkit/bugs/<slug>/` (`<slug>` is a short kebab-case name for the bug):

| Phase skill | Debugging phases | Artifact | Template |
| --- | --- | --- | --- |
| `{{SKILL:redevkit-bug-assess}}` | 1 Reproduce, 2 Isolate, 3 Understand | `assessment.md` | `reports/bug-assessment.md` |
| `{{SKILL:redevkit-bug-fix}}` | 4 Fix (regression test first) | `fix.md` | `reports/bug-fix.md` |
| `{{SKILL:redevkit-bug-test}}` | 4 Verify | `test.md` | `reports/bug-test.md` |

Template resolution: use `.redevkit/templates/overrides/<name>` if it exists, otherwise
`.redevkit/templates/<name>`. Link the assessment to the feature (`specs/NNN-name/`) and to the
`test-report.md` that exposed the bug, when they exist. Write artifacts in the project language
(`{{LANG}}`).

Outside the pipeline (a quick question, a one-line fix), follow the same four phases and
report the evidence in your answer.

## Phase 1: Reproduce

Before fixing, reproduce the issue reliably.

```markdown
## Reproduction Steps
1. [Exact step or command]
2. [Next step]
3. [Expected vs actual result, with the exact error output]

## Reproduction Rate
- [ ] Always (100%)
- [ ] Often (50-90%)
- [ ] Sometimes (10-50%)
- [ ] Rare (<10%)
```

If you cannot reproduce it, say so, record what you tried, and gather more evidence (logs,
environment, input data) instead of guessing.

## Phase 2: Isolate

Narrow down the source.

```markdown
## Isolation Questions
- When did this start happening? What changed recently?
- Does it happen in all environments?
- Can we reproduce with minimal code or input?
- What is the smallest change that triggers it?
```

Use `git bisect` when a known-good commit exists.

## Phase 3: Understand

Find the root cause, not just the symptom.

```markdown
## Root Cause Analysis (5 Whys)
1. Why: [First observation]
2. Why: [Deeper reason]
3. Why: [Still deeper]
4. Why: [Getting closer]
5. Why: [Root cause]

## Hypothesis
[One sentence] - confirmed by: [the observation or experiment that proves it]
```

## Phase 4: Fix and Verify

1. **RED:** write a regression test that reproduces the bug. Run it and watch it fail for the
   reason found in Phase 3 (see `{{SKILL:tdd-workflow}}`).
2. **GREEN:** make the smallest change that fixes the root cause.
3. Run the regression test, then the full suite as `{{CMD:redevkit-test}}` step 3 says
   (`test_runner.py` audit when Python is found, otherwise the `tech.md` test command).
4. Search for the same pattern elsewhere in the code.
5. Record the verdict: `verified` (bug gone, suite green), `partial` (bug gone, other failures
   remain) or `failed`.

```markdown
## Fix Verification
- [ ] Regression test failed before the fix and passes after it
- [ ] Full suite run, results recorded (command + observed output)
- [ ] Related functionality still works
- [ ] Similar code checked
- [ ] Root cause documented
```

After a fix, `{{CMD:redevkit-verify}}` is mandatory: it runs the tests again on the fixed code.
Its correction cycle stops for the user at gate G5 (rules in `{{CMD:redevkit-verify}}` step 6).

## Investigation Checklist

```markdown
## Before Starting
- [ ] Can reproduce consistently
- [ ] Have a minimal reproduction case
- [ ] Understand the expected behavior (spec, acceptance scenario, or user)

## During Investigation
- [ ] Check recent changes (git log, git diff)
- [ ] Check logs for errors
- [ ] Add temporary logging if needed (remove it afterwards)
- [ ] Use a debugger or breakpoints where available
```

## Common Commands

```bash
# Recent changes
git log --oneline -20
git diff HEAD~5

# Find the commit that introduced it
git bisect start
git bisect bad
git bisect good <known-good-sha>

# Search for a pattern
grep -rn "errorPattern" --include="*.ts" .
```

On Windows PowerShell, search with `Select-String -Path src\*.ts -Pattern "errorPattern"`, or
use `rg` when it is installed.

## Anti-Patterns

| ❌ Don't | ✅ Do |
| --- | --- |
| Random changes ("maybe if I change this...") | Test one hypothesis at a time |
| Ignore evidence ("that can't be the cause") | Follow the observations |
| Assume ("it must be X") | Prove it with a reproduction |
| Fix without reproducing | Reproduce first, then a failing test |
| Stop at the symptom | Find and fix the root cause |
| Claim "fixed" without a run | Show the command and its result |
