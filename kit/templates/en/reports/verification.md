---
type: verification
---

# Verification: [FEATURE NAME]

- **Feature**: `specs/[NNN-short-name]/`
- **Inputs**: `spec.md`, `plan.md`, `tasks.md`, `test-report.md` (same directory)

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
| Status fingerprint | `[HASH]` |
| Diff fingerprint | `[HASH]` |

<!--
Same commands as the test report:
  git rev-parse HEAD
  git status --porcelain -- . ':(exclude).redevkit' ':(exclude)specs'
  git status --porcelain -- . ':(exclude).redevkit' ':(exclude)specs' | git hash-object --stdin   (status fingerprint)
  git diff HEAD -- . ':(exclude).redevkit' ':(exclude)specs' | git hash-object --stdin            (diff fingerprint)
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
| Full test suite | `[COMMAND]` | [EXIT CODE] | [N passed, N failed, N skipped] |
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
| [AUDIT NAME] | `[COMMAND]` | PASS / FAIL / SKIPPED ([REASON]) | [FINDINGS SUMMARY] |

### Not verified

- [What could not be exercised and why, or none]

### Verdict

**[converged+verified | gaps | failed]** — [one or two sentences with the decisive evidence].

<!--
converged+verified: no convergence gaps; build, full suite and critical flows pass; no audit FAIL.
gaps: execution passes, but convergence found gaps (tasks were appended).
failed: build, suite, a critical flow or a blocking audit fails.
-->

- **Next step**: [redevkit-deploy | redevkit-create or redevkit-enhance (gaps) | redevkit-debug (failed, cycle [1 | 2] of 2)]
