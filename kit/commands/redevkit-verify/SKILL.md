---
name: redevkit-verify
description: Full verification - converge with spec, run build, suite and flows, audits, verdict report.
short-description: Verify code against spec with real execution
argument-hint: "[--auto] [feature or scope]"
---

# redevkit-verify

**Input:** {{ARGS}}

Flags: `--auto` continues to the debug command when the verdict is `failed`. Optional scope:
a feature (`specs/NNN-short-name`) or an area; default is the active feature and everything
changed since the last verification. Write artifacts in {{LANG}}; answer the user in the
user's language.

## Purpose

The full verification (D25): check that the code does what the spec, plan and tasks say
(convergence), prove it by running it (build, suite, critical flows), run the audits, and
write a verdict with the code state. Mandatory after a debug (D26); suggested before a
deploy after a `PASS` test run.

## Preconditions

- Memory initialized. If not, suggest `{{CMD:redevkit-new}}` and stop.
- An active feature (or the one given) with `spec.md`, `plan.md` and `tasks.md`. Without a
  feature, convergence is `SKIPPED (no feature spec)`; run steps 2–3 and report in the answer
  and in `active.md`, then suggest `{{CMD:redevkit-plan}}`.
- Templates resolve per T10: `.redevkit/templates/overrides/reports/verification.md` if it
  exists, otherwise `.redevkit/templates/reports/verification.md`.

## Memory phase 1

Recall per `{{SKILL:redevkit-memanager}}`: `MEMORY.md`, `active.md` (latest results, known
problems, debug → verify cycle count), the invariants in `system.md`, `tech.md` (build, test,
dev commands, port). Print `📖 Memory loaded. Last entry: YYYY-MM-DD.`

## Questions

Ask only what changes the verification scope, one question at a time, at most 3 options with
the recommended one first and marked "(Recommended)", at most 5 questions in this run. Record
every assumption in `verification.md`. Personas never ask: they return the question to you.
In `--auto` or non-interactive runs, adopt the recommendation and record it as an assumption,
except at gates.

{{ASK}}

## Steps

### 1. Converge

Follow `{{SKILL:redevkit-converge}}`: compare the code with `spec.md`, `plan.md` and
`tasks.md` (requirements, acceptance scenarios, contracts, data model, tasks marked `[X]`).
Each gap becomes a task appended under `## Phase N: Convergence` (`## Fase N: Convergência` in pt-BR) in `tasks.md` (append-only,
same task grammar, `@persona` chosen with `{{SKILL:redevkit-route}}`).

### 2. Execute

Prove the behavior by running it, with the method in [execution](references/execution.md):
identify what changed, pick the method per change type, run the build and the full suite,
and — when the Project Type has a runtime — start the app in the background as
`{{SKILL:redevkit-preview}}` describes for `start`, walk the critical flows of
`quickstart.md` (happy path and error paths), then stop it. For bug fixes, reproduce the
original scenario from `.redevkit/bugs/<slug>/assessment.md`. Delegate browser flows when
needed: {{DELEGATE:qa-automation-engineer}}.

### 3. Audit

Run the audits as [execution](references/execution.md) § Audits describes: Python detection
per `.redevkit/audits/README.md`; `verify_all.py` or `checklist.py` chosen by the Project Type
in `plan.md`; `--no-runtime` when no app is running or the type has no runtime. No Python →
`SKIPPED (no Python interpreter)` plus the project's own lint and type-check commands.
Audit exit codes: `0` PASS, `1` FAIL, `2` usage error, `3` SKIPPED. Exit `3` is never a pass:
record `SKIPPED (<reason printed by the script>)`.

### 4. Report

Record the code state (HEAD, branch, working tree, changed files, status and diff
fingerprints) as `{{SKILLDIR:redevkit-test}}/references/code-state.md` describes. Append a
`## Run YYYY-MM-DD HH:MM — <verdict>` section (`## Execução …` in pt-BR) to `specs/NNN-short-name/verification.md`
(create the file from the template when missing; append-only, never edit a past run):

- Code state table; convergence result and the tasks appended.
- Execution evidence: commands with exit codes and observed results; critical flows walked.
- Audit table (`PASS`, `FAIL`, `SKIPPED (reason)`), runner and Project Type.
- **Not verified** list with reasons.
- Verdict `converged+verified`, `gaps` or `failed` (rules in the reference) and the next step
  with the debug cycle number. Tokens stay in English in every language. The verify command
  does not edit application code.

### 5. Debug cycle accounting (G5)

When this run follows a debug, update the cycle count in `active.md` › Latest results:

- `converged+verified` or `gaps` → the cycle ends; reset the count.
- `failed` → increment. On the **second consecutive** failed debug → verify cycle, stop at
  G5: present the evidence of both cycles and ask how to proceed (revise the plan
  (Recommended), keep debugging, or stop). The chain stops here even in `--auto`.

## Gates that apply

| Gate | Where |
| --- | --- |
| G5 | Step 5, two consecutive failed debug → verify cycles |
| G4 | Step 2, flows that write to real external systems or delete data need confirmation |

## Artifacts

- `specs/NNN-short-name/verification.md` (appended dated run with code state and verdict).
- `tasks.md` with the appended `Phase N: Convergence` (when there are gaps).

## Memory phase 3

Save per `{{SKILL:redevkit-memanager}}`: `changelog.md` (verification event and verdict),
`active.md` › Latest results (date, verdict, link, debug → verify cycle count) and Known
problems, `MEMORY.md`. Print `💾 Memory updated (files).`

## Evidence rule

Every line of the report comes from a command that ran and its observed output. A skipped
audit or flow is `SKIPPED (reason)`, never `PASS`. `converged+verified` is allowed only when
convergence found no gaps and every executed check passed.

## Handoff

- `converged+verified` → `{{CMD:redevkit-deploy}}` (the user triggers it; this run stops).
- `gaps` → `{{CMD:redevkit-create}}` to implement the Convergence tasks, or
  `{{CMD:redevkit-enhance}}` when a gap needs a spec change.
- `failed` → `{{CMD:redevkit-debug}}` with the failing evidence (at most 2 cycles, then G5).
- `--auto`: `failed` → continue with `{{CMD:redevkit-debug}}` `--auto` until G5; `gaps` →
  continue with `{{CMD:redevkit-create}}` `--auto` (it ends at the test command);
  `converged+verified` → stop before the deploy.
