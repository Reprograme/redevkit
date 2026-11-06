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
| Reference run | [test-report.md or verification.md, run YYYY-MM-DD HH:MM] | — | — |
| Reference verdict | [PASS or converged+verified] | — | OK / BLOCKED |
| Commit (HEAD) | `[SHA]` | `[SHA]` | OK / BLOCKED |
| Working tree | [clean / dirty] | [clean / dirty] | OK / BLOCKED |
| Status fingerprint | `[HASH]` | `[HASH]` | OK / BLOCKED |
| Diff fingerprint | `[HASH]` | `[HASH]` | OK / BLOCKED |
| Verify after debug | [required: yes / no] | [run YYYY-MM-DD HH:MM, or none] | OK / BLOCKED |

- **Precondition status**: OK / BLOCKED / OVERRIDDEN
- **Verify suggested**: [yes, not run / ran on YYYY-MM-DD / not needed]
- **Override reason**: [required when OVERRIDDEN, written in the user's words; otherwise none]

<!--
BLOCKED when the reference run is not green, or when the code changed after it
(HEAD, tree state or fingerprints differ). Then run redevkit-test again before deploying.
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
