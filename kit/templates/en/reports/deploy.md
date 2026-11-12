---
type: deploy
---

# Deploy: [ENVIRONMENT] — [YYYY-MM-DD]

- **Environment**: [ENVIRONMENT]
- **Production**: yes / no
- **Started**: [YYYY-MM-DD HH:MM]
- **Triggered by**: [USER] (deploys run only when the user invokes them)
- **Features**: `specs/[NNN-short-name]/`
- **Outcome**: [succeeded | failed | rolled-back | aborted]

<!--
Never write secrets (tokens, passwords, keys, connection strings) in this file.
Keep these tokens in English: PASS, FAIL, SKIPPED, OK, BLOCKED, OVERRIDDEN, succeeded,
failed, rolled-back, aborted, clean, dirty.
-->

## Preconditions

| Check | Reference (from report) | Current | Result |
| --- | --- | --- | --- |
| Verify pending | [no / yes: debug <slug>, gaps or failed] | — | OK / BLOCKED |
| Reference run | [test-report.md, run YYYY-MM-DD HH:MM, run by redevkit-test / redevkit-verify (step 1)] | — | — |
| Reference verdict | [PASS] | — | OK / BLOCKED |
| Tree fingerprint | `sha256:[HASH]` | `sha256:[HASH]` | OK / BLOCKED |
| Commit (HEAD) | `[SHA]` | `[SHA]` | — |
| Working tree | [clean / dirty] | [clean / dirty] | — |

- **Precondition status**: OK / BLOCKED / OVERRIDDEN
- **Verify suggested**: [not needed (the latest verify is converged+verified on this same code) / suggested, user chose: verify first or deploy now]
- **Override reason**: [required when OVERRIDDEN, written in the user's words; otherwise none]

<!--
Reference run and comparison: redevkit-test/references/code-state.md (the single
definition). BLOCKED when a verify is pending, when there is no reference, when the latest
feature-wide test run is not PASS, when the Tree fingerprint differs (the code changed after
it) or when the code state cannot be computed. Commit and working tree are context only.
-->

## Deploy plan

| # | Step | Command or action | Expected result |
| --- | --- | --- | --- |
| 1 | [STEP] | `[COMMAND]` | [EXPECTED RESULT] |

- **Version or artifact**: [TAG, IMAGE, BUILD ID]
- **Migrations**: [none, or list with reversibility]
- **Configuration and secrets**: [where they come from, never their values]
- **Expected downtime**: [none, or estimate]

## Rollback plan

- **Trigger**: [conditions that start a rollback, e.g. smoke test FAIL, error rate above N%]
- **Data considerations**: [backups taken, irreversible migrations, or none]

| # | Step | Command or action | Expected result |
| --- | --- | --- | --- |
| 1 | [STEP] | `[COMMAND]` | [EXPECTED RESULT] |

## Production confirmation

- **Required**: yes / no
- **Confirmation**: [the user's explicit confirmation, quoted, with time] / not applicable
- **Rollback plan reviewed by the user**: yes / no / not applicable

## Execution log

| Time | Step | Command | Exit code | Observed result |
| --- | --- | --- | --- | --- |
| [HH:MM] | [STEP] | `[COMMAND]` | [EXIT CODE] | [RESULT] |

```text
[SHORT OUTPUT EXCERPTS]
```

## Post-deploy smoke test

| Check | Command or URL | Expected | Observed | Result |
| --- | --- | --- | --- | --- |
| [CHECK] | `[COMMAND OR URL]` | [EXPECTED] | [OBSERVED] | PASS / FAIL / SKIPPED ([REASON]) |

## Outcome

[One or two sentences: what was deployed, where, and the evidence that it works. If rolled
back, what triggered it and the state after the rollback.]

- **Follow-ups**: [monitoring, cleanup, tickets, or none]
