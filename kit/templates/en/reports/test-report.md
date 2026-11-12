---
type: test-report
---

# Test report: [FEATURE NAME]

- **Feature**: `specs/[NNN-short-name]/`
- **Spec**: `specs/[NNN-short-name]/spec.md`

<!--
Append-only. Add one "Run" section at the end of this file for each execution.
Never edit or delete a past run. Only feature-wide runs (Scope: feature) count: the latest one
is the run redevkit-verify (step 1) may reuse, and the deploy reference is chosen as
redevkit-test/references/code-state.md describes; both compare code states there.
Keep these tokens in English: PASS, FAIL, SKIPPED, MISSING, clean, dirty, and the failure
classes product-defect, not-implemented, test-defect, environment.
-->

## Run [YYYY-MM-DD HH:MM] — [PASS | FAIL]

- **Run by**: [redevkit-test | redevkit-verify (step 1)]
- **Scope**: [feature | file or scenario: …]

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
  - `[TEST ID]` — [product-defect | not-implemented | test-defect | environment] — [assertion or error excerpt]
- **Failure class** (all that remain on a FAIL run; none on PASS): [product-defect | not-implemented | test-defect | environment | none]

```text
[SHORT OUTPUT EXCERPT: final summary lines or the failing assertion]
```

### Acceptance-scenario coverage

| Spec scenario | Test | Status |
| --- | --- | --- |
| [US1 / Scenario 1 — Given, When, Then summary] | `[path/to/test::name]` | PASS / FAIL / SKIPPED ([REASON]) / MISSING |

- **Tests generated in this run**: [list, or none]
- **Tests corrected in this run** (test-defect, with the spec scenario or the error that proves it): [list, or none]
- **Scenarios still without a test**: [list, or none]
- **Not verified** (cannot be automated here; never counted as PASS): [scenario — manual check
  needed, or none]

### Assumptions

- [Assumption taken in this run and why, or none]

### Verdict

**[PASS | FAIL]** — [one sentence with the decisive evidence].

<!--
PASS only when every command exited 0, no test failed and every automatable acceptance
scenario maps to a passing test. Anything else is FAIL. Scenarios that cannot be automated
here go to Not verified: they do not make the run FAIL and are never PASS.
-->

- **Next step**: [PASS: redevkit-verify when a verify is pending, otherwise redevkit-deploy, suggesting redevkit-verify first | FAIL, by class: environment → fix it and run again; not-implemented → redevkit-create; product-defect → redevkit-debug | inside redevkit-verify: the verification continues (PASS) or stops as failed (FAIL)]
