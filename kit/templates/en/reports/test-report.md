---
type: test-report
---

# Test report: [FEATURE NAME]

- **Feature**: `specs/[NNN-short-name]/`
- **Spec**: `specs/[NNN-short-name]/spec.md`

<!--
Append-only. Add one "Run" section at the end of this file for each execution.
Never edit or delete a past run. The latest run is the one redevkit-verify (step 1) may reuse
and the reference redevkit-deploy compares with the current code; both compare code states as
redevkit-test/references/code-state.md describes.
Keep these tokens in English: PASS, FAIL, SKIPPED, MISSING, clean, dirty.
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
| Status fingerprint | `[HASH]` |
| Diff fingerprint | `[HASH]` |

<!--
Record these values right after the suite with the commands in
redevkit-test/references/code-state.md (same shell type as the deploy will use).
-->

### Commands executed

| # | Command | Exit code | Duration | Summary |
| --- | --- | --- | --- | --- |
| 1 | `[COMMAND]` | [EXIT CODE] | [DURATION] | [N passed, N failed, N skipped] |

### Results

- **Total**: [N] · **Passed**: [N] · **Failed**: [N] · **Skipped**: [N]
- **Failures**:
  - `[TEST ID]` — [assertion or error excerpt]

```text
[SHORT OUTPUT EXCERPT: final summary lines or the failing assertion]
```

### Acceptance-scenario coverage

| Spec scenario | Test | Status |
| --- | --- | --- |
| [US1 / Scenario 1 — Given, When, Then summary] | `[path/to/test::name]` | PASS / FAIL / SKIPPED ([REASON]) / MISSING |

- **Tests generated in this run**: [list, or none]
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

- **Next step**: [redevkit-deploy, suggesting redevkit-verify first | redevkit-debug | inside redevkit-verify: the verification continues (PASS) or stops as failed (FAIL)]
