---
type: test-report
---

# Test report: [FEATURE NAME]

- **Feature**: `specs/[NNN-short-name]/`
- **Spec**: `specs/[NNN-short-name]/spec.md`

<!--
Append-only. Add one "Run" section at the end of this file for each execution.
Never edit or delete a past run. Scope spec: redevkit-test ran the tests of this feature
only (spec (full suite) when the test command cannot select files). Scope global:
redevkit-verify (step 1) ran the whole suite. redevkit-verify (step 1, with its rules) reuses
a global run (never a FAIL with the environment or test-defect class, nor a PASS followed by
a FAIL run), and a spec (full suite) run only when it is PASS and its Outside the spec list
has no failure; the deploy never takes a test run as its reference (it takes the latest
verify, redevkit-test/references/code-state.md; a FAIL run appended after the run that verify
used blocks the deploy until a new verify).
Keep these tokens in English: PASS, FAIL, SKIPPED, MISSING, clean, dirty, the scopes, and the
failure classes product-defect, not-implemented, test-defect, environment, baseline.
-->

## Run [YYYY-MM-DD HH:MM] — [PASS | FAIL]

- **Run by**: [redevkit-test | redevkit-verify (step 1)]
- **Scope**: [spec | spec (full suite) | global]
- **Spec test set** (scope spec): [test files passed to the runner, or the reason the whole suite ran]

### Code state

| Field | Value |
| --- | --- |
| Commit (HEAD) | `[SHA]` or `n/a (not a git repository)` |
| Branch | `[BRANCH]` |
| Working tree | clean / dirty |
| Changed files | [none, or the `git status --porcelain` list] |
| Tree fingerprint | `sha256:[HASH]` or `n/a (no Python interpreter)` |

<!--
Record these values right after the suite with `code_state.py`, as
redevkit-test/references/code-state.md describes. Two runs are on the same code when their
Tree fingerprint is equal.
-->

### Commands executed

| # | Command | Exit code | Duration | Summary |
| --- | --- | --- | --- | --- |
| 1 | `[COMMAND]` | [EXIT CODE] | [DURATION] | [N passed, N failed, N skipped] |

### Results

- **Total**: [N] · **Passed**: [N] · **Failed**: [N] · **Skipped**: [N]
- **Failures** (one line each, with its class):
  - `[TEST ID]` — [product-defect | not-implemented | test-defect | environment | baseline] — [assertion or error excerpt]
  - `[SCENARIO]` — test-defect (missing test: still MISSING after generation) — [why it was not generated]
- **Failure class** (all that remain on a FAIL run; none on PASS): [product-defect | not-implemented | test-defect | environment | none]
- **Baseline failures** (scope global, before the project's first fully green whole-suite run: a PASS with scope global and no baseline failure, or a PASS with scope spec (full suite) and no failure under Outside the spec, also when redevkit-verify reused it; never make the run FAIL): [test — file, or none]
- **Outside the spec** (tests generated on request for behavior outside the spec, and in scope spec (full suite) every other test of the suite; never make the run FAIL, the verify judges them): [test — file — result, or none]

```text
[SHORT OUTPUT EXCERPT: final summary lines or the failing assertion]
```

### Acceptance-scenario coverage

| Spec scenario | Test | Status |
| --- | --- | --- |
| [US1 / Scenario 1 — Given, When, Then summary] | `[path/to/test::name]` | PASS / FAIL / SKIPPED ([REASON]) / MISSING |

- **Tests generated in this run**: [list, or none]
- **Tests corrected in this run** (test-defect, with the spec scenario or the error that proves it): [list, or none]
- **Scenarios still without a test** (automatable: class test-defect, one more generation attempt, then a question for the user): [list, or none]
- **Not verified** (cannot be automated here; never counted as PASS): [scenario — manual check
  needed, or none]

### Assumptions

- [Assumption taken in this run and why, or none]

### Verdict

**[PASS | FAIL]** — [one sentence with the decisive evidence].

<!--
PASS only when no test of this run's scope failed: every command exited 0, or its only
failures are baseline failures (scope global) or tests listed under Outside the spec (scope
spec (full suite)); and every automatable acceptance scenario maps to a passing test. Anything else is FAIL. Scenarios that cannot be automated
here go to Not verified: they do not make the run FAIL and are never PASS.
-->

- **Next step**: [PASS: redevkit-verify (the only way to the deploy), or redevkit-plan for the next feature | FAIL, by class: environment → fix it and run again; test-defect → answer the question it names (a spec decision, or how to test a scenario still MISSING), then run again (redevkit-verify for scope global); not-implemented → redevkit-create; product-defect → redevkit-debug (test cycle N/5) | inside redevkit-verify: the verification continues (PASS) or stops as failed (FAIL)]
