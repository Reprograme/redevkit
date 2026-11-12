---
type: verification
---

# Verification: [FEATURE NAME]

- **Feature**: `specs/[NNN-short-name]/`
- **Inputs**: `spec.md`, `plan.md` (when present), `tasks.md`, `test-report.md` (same directory)

<!--
Append-only. Add one "Run" section at the end of this file for each verify execution.
Never edit or delete a past run. Keep these tokens in English: converged+verified, gaps,
failed, PASS, FAIL, SKIPPED, clean, dirty.
-->

## Run [YYYY-MM-DD HH:MM] — [converged+verified | gaps | failed]

### Code state

| Field | Value |
| --- | --- |
| Commit (HEAD) | `[SHA]` or `n/a (not a git repository)` |
| Branch | `[BRANCH]` |
| Working tree | clean / dirty |
| Changed files | [none, or the `git status --porcelain` list] |
| Tree fingerprint | `sha256:[HASH]` or `n/a (no Python interpreter)` |

<!--
Same script as the test report: redevkit-test/references/code-state.md.
-->

### Test evidence

| Field | Value |
| --- | --- |
| Test run | `test-report.md`, run [YYYY-MM-DD HH:MM] — [PASS \| FAIL] |
| Source | [ran in step 1 \| reused: same code state as the current code] |
| Failure class (FAIL run) | [product-defect \| not-implemented \| environment \| none] |
| Verify pending at the start | [no \| debug <slug> \| gaps \| failed] |

<!--
A FAIL test run ends the verification here: verdict failed, and the Convergence, Execution
and Audits sections are SKIPPED (test run FAIL).
-->

### Convergence

- **Result**: converged / gaps found
- **Tasks appended**: `Phase [N]: Convergence` in `tasks.md`, [T0NN–T0NN], or none

| Gap | Source (spec, plan or task) | Task appended |
| --- | --- | --- |
| [WHAT IS MISSING OR DIFFERENT] | [FR-00N, US1 scenario 2, plan section, T0NN] | [T0NN] |

### Execution evidence

| Step | Command | Exit code | Observed result |
| --- | --- | --- | --- |
| Build | `[COMMAND]` | [EXIT CODE] | [compiled without errors, or the error] |
| App start | `[COMMAND]` | [EXIT CODE] | [listening on URL, or the error], or SKIPPED ([REASON]) |

#### Critical flows

| Flow | Steps | Expected | Observed | Result |
| --- | --- | --- | --- | --- |
| [FLOW NAME] | [request, click path or command] | [EXPECTED] | [OBSERVED] | PASS / FAIL / SKIPPED ([REASON]) |

```text
[SHORT OUTPUT EXCERPTS THAT PROVE THE RESULTS ABOVE]
```

### Audits

- **Runner**: `verify_all.py` / `checklist.py` / project commands (no Python available)
- **Project type**: [PROJECT TYPE]

| Audit | Command | Result | Notes |
| --- | --- | --- | --- |
| [AUDIT NAME] | `[COMMAND]` | PASS / FAIL / SKIPPED ([REASON]) | [in scope: N findings; baseline (pre-existing): N findings in N files; out of scope (third-party/generated): paths] |

<!--
Only in-scope findings (files this feature created or changed) become tasks or failed.
Baseline and out-of-scope findings are listed in Notes and never change the verdict.
-->

### Not verified

- [What could not be exercised and why, or none]

### Assumptions

- [Assumption taken in this run and why, or none]

### Verdict

**[converged+verified | gaps | failed]** — [one or two sentences with the decisive evidence].

<!--
converged+verified: test run PASS; no convergence gaps; build and critical flows pass; no audit
FAIL with in-scope findings (baseline findings in files this feature did not touch and findings
in third-party or generated code are listed in Notes and never become tasks).
gaps: test run PASS and execution passes, but convergence or non-critical audits appended tasks.
failed: the test run is FAIL, or the build, a critical flow or a blocking audit fails.
-->

- **Correction cycle** (after this run): failed after debug [N]/2 · rounds without convergence [N]/3
- **Verify pending** (after this run): [no | gaps | failed]
- **Next step**: [redevkit-deploy | redevkit-create or redevkit-enhance (gaps) | redevkit-debug (failed) | redevkit-create (failed: not-implemented) | fix the environment and run redevkit-verify again (failed: environment) | G5 reached: waiting for the user]
