---
name: redevkit-verify
description: Full verification - test run, convergence with spec, build and flows, audits, verdict report.
short-description: Verify code against spec with real execution
argument-hint: "[--auto] [feature or scope]"
---

# redevkit-verify

**Input:** {{ARGS}}

Flags: `--auto` follows the handoff on its own: to the create command on `gaps` and, on
`failed`, to the command the failure names. Optional scope: a feature (`specs/NNN-short-name`) or an area;
default is the active feature and everything changed since the last verification. Write
artifacts in {{LANG}}; answer the user in the user's language.

## Purpose

The full verification (D25): prove the feature against its spec with a test run on the
current code, check that the code does what the spec, plan and tasks say (convergence), prove
it by running it (build, critical flows), run the audits, and write a verdict with the code
state. Mandatory after a debug (D26); suggested after a `PASS` test run, before a deploy.

## Preconditions

- Memory initialized. If not, suggest `{{CMD:redevkit-new}}` and stop.
- An active feature (or the one given) with `spec.md`, `tasks.md` and `plan.md`. A
  lightweight spec of the enhance command (D55) has no `plan.md`: converge against `spec.md`
  and `tasks.md`, and take the Project Type and the technical context from `tech.md`.
- Without a feature: convergence is `SKIPPED (no feature spec)`; step 1 always runs the test
  procedure (there is no `test-report.md` to reuse or append to: the suite result goes to the
  answer and `active.md` › Last results), then steps 3 and 4. No report file is written, step 6
  does not apply, and `--auto` never continues: stop and suggest `{{CMD:redevkit-plan}}`.
- G5 not pending: if the Correction cycle line names the active feature and says G5 was
  reached, present the G5 question again before anything else (answers in step 6, as at a
  precondition).
- Read `active.md` › Last results › `- Verify pending:` now, before anything is written: its
  reason for the active feature (`no`, `debug <slug>`, `gaps` or `failed`) is the **reason at
  the start** that step 6 uses.
- Templates resolve per T10: `.redevkit/templates/overrides/reports/verification.md` if it
  exists, otherwise `.redevkit/templates/reports/verification.md`.

## Memory phase 1

Recall per `{{SKILL:redevkit-memanager}}`: `MEMORY.md`, `active.md` (Last results: test,
verify, debug, verify pending, correction cycle; Known issues), the invariants in `system.md`, `tech.md`
(build, test and dev commands, port). Print `📖 Memory loaded. Last entry: YYYY-MM-DD.`

## Questions

Ask only what changes the verification scope, one question at a time, at most 3 options with
the recommended one first and marked "(Recommended)", at most 5 questions in this run (the
test procedure in step 1 shares this budget). Record every assumption in `verification.md`.
Personas never ask: they return the question to you. In `--auto` or non-interactive runs,
adopt the recommendation and record it as an assumption, except at gates.

{{ASK}}

## Steps

### 1. Test run on the current code

Take the Tree fingerprint recorded in the latest feature-wide run (Scope `feature`) of the
feature's `test-report.md` and compare it with the current code, as
`{{SKILLDIR:redevkit-test}}/references/code-state.md` § Compare describes (the `--expect`
option of `code_state.py` prints `SAME` or `DIFFERENT`). A fingerprint that is `n/a`, or a
run recorded without one, never counts as the same code state:

| Latest test run | Same code state as now | Action |
| --- | --- | --- |
| `PASS` | yes | Reuse it; do not run the tests again |
| `FAIL` | yes | Reuse it, with its failure classes: the verdict is `failed`; go to step 5 |
| Any, or none | no, or no run | Run the test procedure below |

**Test procedure.** Execute steps 1–6 of `{{SKILLDIR:redevkit-test}}/SKILL.md` (map
scenarios to tests, generate the missing tests, run the full suite, classify the failures,
record the code state, append the run to `test-report.md` with **Run by**
`redevkit-verify (step 1)` and Scope `feature`). Skip that
file's memory phases, handoff and `--auto` continuation: this command does the memory and the
handoff once.

- `FAIL` → the verdict is `failed`, with the failure classes of that run. Skip steps 2–4
  (record them as `SKIPPED (test run FAIL)`) and go to step 5.
- `PASS` → continue. The run's **Not verified** scenarios carry over to this report.

### 2. Converge

Follow `{{SKILL:redevkit-converge}}`: compare the code with `spec.md`, `plan.md` (when present)
and `tasks.md` (requirements, acceptance scenarios, contracts, data model, tasks marked `[X]`).
Each new gap becomes a task appended under `## Phase N: Convergence` (`## Fase N: Convergência`
in pt-BR) in `tasks.md` (append-only, same task grammar, `@persona` chosen with
`{{SKILL:redevkit-route}}`); a gap already covered by an open or blocked task is cited, not
appended. Outcome `tasks_appended` or `tasks_open` means gaps remain (verdict `gaps` at
best); `converged` means none.

### 3. Execute

Prove the behavior by running it, with the method in [execution](references/execution.md):
identify what changed, pick the method per change type, run the build and — when the Project
Type has a runtime — start the app in the background as `{{SKILL:redevkit-preview}}` describes
for `start`, walk the critical flows of `quickstart.md` (happy path and error paths), then
stop it. For bug fixes, reproduce the original scenario from
`.redevkit/bugs/<slug>/assessment.md`. The test suite is not run again here: step 1 is its
evidence. Delegate browser flows when needed: {{DELEGATE:qa-automation-engineer}}.

### 4. Audit

Run the audits as [execution](references/execution.md) § Audits describes: Python detection
per `.redevkit/audits/README.md`; `verify_all.py` or `checklist.py` chosen by the Project Type
in `plan.md` (or `tech.md` for a lightweight spec); `--no-runtime` when no app is running or
the type has no runtime; always `--no-tests` (step 1 is the test evidence). No Python →
`SKIPPED (no Python interpreter)` plus the project's own lint and type-check commands.
Audit exit codes: `0` PASS, `1` FAIL, `2` usage error, `3` SKIPPED. Exit `3` is never a pass:
record `SKIPPED (<reason printed by the script>)`. One orchestrator run is the suite; give
the call a timeout above its duration or run it in the background, as the test procedure
does for the suite. Then triage the findings by file (same reference, step 6): only findings
in files this feature created or changed are **in scope**; findings in the rest of the
project are the **baseline**, and findings in third-party or generated code are out of
scope. Baseline and out-of-scope findings never become tasks or `failed`.

### 5. Report

Append a `## Run YYYY-MM-DD HH:MM — <verdict>` section (`## Execução …` in pt-BR) to
`specs/NNN-short-name/verification.md` (create the file from the template when missing;
append-only, never edit a past run):

- Code state table, recorded as `{{SKILLDIR:redevkit-test}}/references/code-state.md`
  describes.
- Test evidence: the `test-report.md` run used, whether it ran in step 1 or was reused, its
  failure classes when it is `FAIL`, and the verify-pending reason at the start.
- Convergence result and the tasks appended.
- Execution evidence: commands with exit codes and observed results; critical flows walked.
- Audit table (`PASS`, `FAIL`, `SKIPPED (reason)`), runner and Project Type; in Notes, the
  findings counted as in scope, baseline and out of scope.
- **Not verified** list with reasons, including the open items of domain checklists
  (`checklists/<domain>.md`) and the test run's Not verified scenarios.
- Assumptions taken in this run.
- Verdict `converged+verified`, `gaps` or `failed` (rules in the reference), the correction
  cycle counters and the verify-pending value after step 6, and the next step. Tokens stay in
  English in every language. Date and time come from the system clock, never guessed.

The verify command does not edit application code. It writes test files and
`test-report.md` only through the test procedure of step 1.

### 6. Verify pending, correction cycle and G5

This step is the single definition of the verify-pending flag and of the correction cycle;
other commands refer to it. Both live in `active.md` › Last results, on the lines
`- Verify pending: specs/NNN-name — <reason>` (or `- Verify pending: no`) and
`- Correction cycle: specs/NNN-name — …`. They belong to the feature the line names: when a
line names another feature (or none), verify pending is `no`, the counters start from zero
with no G5 marker, and this command rewrites both lines for the active feature.

**Verify pending** means the feature needs a verify that ends in `converged+verified` before
it can be deployed. It is a flag, so no command compares dates to know what came first:

- the debug command sets the reason `debug <slug>` when it changed code;
- this command sets `gaps` or `failed` when it ends with that verdict;
- only this command clears it, writing `no`, on `converged+verified`;
- while it is set, a `PASS` test run hands off to this command, and the deploy is `BLOCKED`.

An `active.md` written by an older kit version has no such line: treat it as `debug <slug>`
when a `- Debug:` line names the active feature and the latest run of its `verification.md`
is not `converged+verified` (or there is none), otherwise as `no`, and write the line.

The correction cycle counters:

- **Follows a debug:** the verify-pending reason at the start of this run is `debug <slug>`.
- **Failed after debug:** add 1 when the verdict is `failed` and this run follows a debug,
  whatever the failing test or bug. Reset it to 0 on `converged+verified` or `gaps`.
- **Rounds without convergence:** add 1 for every verdict other than `converged+verified`.
  Reset it to 0 on `converged+verified`. Test runs never change it, so a gaps → create → test
  `PASS` → verify loop still reaches G5.
- A `failed` verdict that reused a `FAIL` run and does not follow a debug (step 1, second
  row) changes neither counter, and neither does a `failed` verdict whose only failure class
  is `environment`: the code was not judged.
- Both counters reset when the user chooses to continue at G5; a new active feature starts a
  new line.

**G5** is reached when failed after debug is 2 or more, or rounds without convergence is 3 or
more. Write `G5 reached` with the date to the Correction cycle line, present the evidence of
the runs that counted and ask:

1. Revise the plan with `{{CMD:redevkit-plan}}` (Recommended): clear the G5 marker, reset both
   counters and hand off to the plan.
2. Continue: clear the G5 marker, reset both counters and follow the normal handoff.
3. Stop: keep the G5 marker; the chain ends. The next verify or debug asks again.

The chain stops here even in `--auto`; no handoff runs until the user answers. Only these
answers clear the marker. When the question is asked again at a precondition (of this command
or of the debug command), there is no verdict yet: continue means proceed with that run,
revise hands off to the plan, stop ends the run.

## Gates that apply

| Gate | Where |
| --- | --- |
| G5 | Step 6, the correction cycle reached its limit |
| G4 | Steps 1 and 3, tests or flows that write to real external systems or delete data need confirmation |
| G3 | Step 1, a requirement can only be tested by violating the constitution; step 2, a CRITICAL constitution finding: stop and report |

## Artifacts

- `specs/NNN-short-name/verification.md` (appended dated run with code state and verdict).
- `specs/NNN-short-name/test-report.md` and new test files, when step 1 ran the test
  procedure.
- `tasks.md` with the appended `Phase N: Convergence` (when there are gaps).

## Memory phase 3

Save per `{{SKILL:redevkit-memanager}}`: `changelog.md` (verification event and verdict),
`active.md` › Last results (Test when step 1 ran the test procedure; Verify: date, verdict,
link; Verify pending; Correction cycle) and Known issues (failing tests or checks on `failed`; on
`converged+verified`, every `- Bug <slug>: open` of this feature becomes
`- Bug <slug>: closed (verify YYYY-MM-DD)`), `tech.md` when the test command was detected
or changed, `MEMORY.md`. Print `💾 Memory updated (files).`

## Evidence rule

Every line of the report comes from a command that ran and its observed output, or from the
reused `test-report.md` run it names. A skipped audit or flow is `SKIPPED (reason)`, never
`PASS`. `converged+verified` is allowed only when the test run is `PASS`, convergence found no
gaps and every executed check passed (audit findings that are all out of scope aside).

## Handoff

- G5 reached → no handoff; wait for the user's answer (step 6).
- `converged+verified` → `{{CMD:redevkit-deploy}}` (the user triggers it; this run stops).
- `gaps` → `{{CMD:redevkit-create}}` to implement the Convergence tasks, or
  `{{CMD:redevkit-enhance}}` when a gap needs a spec change. The test run that follows hands
  back to this command, because a verify is pending.
- `failed` → by what failed; the first that applies wins:
  - a `FAIL` test run whose failure class is `environment` → no command: name what must be
    fixed, then run `{{CMD:redevkit-verify}}` again;
  - a `FAIL` test run with `not-implemented` → `{{CMD:redevkit-create}}` for the open tasks
    (only blocked `[!]` tasks → name them and what each needs);
  - anything else (a `product-defect`, a build failure, an application that does not start, a
    broken flow, a blocking audit) → `{{CMD:redevkit-debug}}` with the failing evidence.
- `--auto`: `gaps` → continue with `{{CMD:redevkit-create}}` `--auto`; its chain runs the test
  command and comes back here, and the correction cycle bounds the loop. `failed` → continue
  with `{{CMD:redevkit-debug}}` `--auto`, or with `{{CMD:redevkit-create}}` `--auto` for
  `not-implemented` with open `[ ]` tasks; stop on `environment` and when only blocked tasks
  remain. `converged+verified` → stop before the deploy.
