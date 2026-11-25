---
name: redevkit-verify
description: Full verification - whole suite, convergence with spec, build and flows, audits, verdict.
short-description: Verify code against spec with real execution
argument-hint: "[--auto]"
---

# redevkit-verify

**Input:** {{ARGS}}

Flags: `--auto` follows the handoff on its own: to the create command on `gaps` and, on
`failed`, to the command the failure names. There is no other argument: the verification
covers the active feature and every feature of the Unverified list. Write artifacts in
{{LANG}}; answer the user in the user's language.

## Purpose

The full verification (D25) in the **global scope**: run the whole test suite on the current
code, check that the code does what the spec, plan and tasks say (convergence), prove it by
running it (build, critical flows), run the audits, and write a verdict with the code state.
A `failed` verdict loops verify → debug → verify, bounded by G5. Only a `converged+verified`
verdict opens the way to the deploy. The two loops (spec and global) are defined in
`{{SKILLDIR:redevkit-test}}/references/loops.md`.

## Preconditions

- Memory initialized. If not, suggest `{{CMD:redevkit-new}}` and stop.
- An active feature with `spec.md`, `tasks.md` and `plan.md`. A lightweight spec of the
  enhance command (D55) has no `plan.md`: converge against `spec.md` and `tasks.md`, and take
  the Project Type and the technical context from `tech.md`.
- Without a feature: convergence is `SKIPPED (no feature spec)`; step 1 always runs the whole
  suite (there is no `test-report.md` to reuse or append to: the suite result goes to the
  answer and `active.md` › Last results), then steps 3 and 4. No report file is written, step 6
  does not apply, and `--auto` never continues: stop and suggest `{{CMD:redevkit-plan}}`.
- G5 not pending: if the Correction cycle line names the active feature and says G5 was
  reached, present the G5 question again before anything else (`loops.md` § G5).
- **Features in scope:** the active feature plus every feature listed on `active.md` › Last
  results › `- Unverified:`. Steps 2–4 cover all of them; their in-scope files are the union
  of each feature's files.
- Templates resolve per T10: `.redevkit/templates/overrides/reports/verification.md` if it
  exists, otherwise `.redevkit/templates/reports/verification.md`.

## Memory phase 1

Recall per `{{SKILL:redevkit-memanager}}`: `MEMORY.md`, `active.md` (Last results: test,
verify, debug, Failing scope, Correction cycle, Unverified; Known issues), the invariants in
`system.md`, `tech.md` (build, test and dev commands, port). Print
`📖 Memory loaded. Last entry: YYYY-MM-DD.`

## Questions

Ask only what changes the verification scope, one question at a time, at most 3 options with
the recommended one first and marked "(Recommended)", at most 5 questions in this run (the
test procedure in step 1 shares this budget). Record every assumption in `verification.md`.
Personas never ask: they return the question to you. In `--auto` or non-interactive runs,
adopt the recommendation and record it as an assumption, except at gates.

{{ASK}}

## Steps

### 1. Whole suite on the current code

Take the latest run of the active feature's `test-report.md` that ran the whole suite (Scope
`global`, or `spec (full suite)`) and compare its Tree fingerprint with the current code, as
`{{SKILLDIR:redevkit-test}}/references/code-state.md` § Compare describes (the `--expect`
option of `code_state.py` prints `SAME` or `DIFFERENT`). A fingerprint that is `n/a`, or a
run recorded without one, never counts as the same code state:

| Latest whole-suite run | Same code state as now | Action |
| --- | --- | --- |
| `PASS` with Scope `global` | yes | Reuse it; do not run the tests again |
| `PASS` with Scope `spec (full suite)` whose **Outside the spec** lists no failure | yes | Reuse it; do not run the tests again |
| `FAIL` with Scope `global`, no `environment` class, no `test-defect` class and no debug handback since | yes | Reuse it, with its failure classes: the verdict is `failed`; go to step 5 |
| Any other, or none | no, or no run | Run the test procedure below |

Only a `global` verdict is reused as it stands. A `spec (full suite)` run never judged the
failures outside the spec, so when its **Outside the spec** lists a failure the test procedure
runs and classifies them by the global rules. A `FAIL` with the `environment` class is never
reused: the environment may be fixed while the files stay the same, so the suite runs again.
A `FAIL` with the `test-defect` class is never reused either: the test correction and the
question for the user are resolved only by the test procedure, which runs again and follows
the answer recorded in `spec.md` (`{{SKILLDIR:redevkit-test}}/SKILL.md` step 4). A debug
handback since the `FAIL` (the debug command changed code or tests, or sent a test back as
wrong: the Correction cycle debug rounds in `active.md` differ from the **Correction cycle**
the latest `verification.md` run recorded) asks for a new judgment: the suite runs again. A
`PASS` followed in `test-report.md` by a `FAIL` run is never reused: the suite runs again. A
reused run counts as it stands: a reused `spec (full suite)` `PASS` with no failure under
**Outside the spec** is a fully green whole-suite run for the `baseline` class, like a
`global` `PASS` with no baseline failure.

**Test procedure.** Execute steps 1–6 of `{{SKILLDIR:redevkit-test}}/SKILL.md` in the
**global scope** (map the active feature's scenarios and generate its missing tests, run the
whole suite, classify the failures, `baseline` included, record the code state, append the
run to `test-report.md` with **Run by** `redevkit-verify (step 1)` and Scope `global`). Skip
that file's memory phases, handoff and `--auto` continuation: this command does the memory
and the handoff once.

- `FAIL` → the verdict is `failed`, with the failure classes of that run. Skip steps 2–4
  (record them as `SKIPPED (test run FAIL)`) and go to step 5.
- `PASS` → continue. The run's **Not verified** scenarios and **Baseline failures** carry over
  to this report.

### 2. Converge

For each feature in scope, follow `{{SKILL:redevkit-converge}}`: compare the code with its
`spec.md`, `plan.md` (when present) and `tasks.md` (requirements, acceptance scenarios,
contracts, data model, tasks marked `[X]`). Each new gap becomes a task appended under
`## Phase N: Convergence` (`## Fase N: Convergência` in pt-BR) in the **active** feature's
`tasks.md`, also for a gap of an Unverified feature (the task cites that feature's spec): the
create and test commands work on the active feature only (append-only, same task grammar,
`@persona` chosen with `{{SKILL:redevkit-route}}`); a gap already covered by an open or blocked
task of the **active** feature's `tasks.md` is cited, not appended. A task that covers a gap
only in an Unverified feature's own `tasks.md` is carried into the active one, so the create
command can run it (`{{SKILL:redevkit-converge}}` step 3). Outcome `tasks_appended`
or `tasks_open` for any feature means gaps remain (verdict `gaps` at best); `converged` for
all means none.

### 3. Execute

Prove the behavior by running it, with the method in [execution](references/execution.md):
identify what changed, pick the method per change type, run the build and — when the Project
Type has a runtime — start the app in the background as `{{SKILL:redevkit-preview}}` describes
for `start`, walk the critical flows of each feature's `quickstart.md` (happy path and error
paths), and keep it running: step 4 audits it by its URL. For bug fixes, reproduce the
original scenario from `.redevkit/bugs/<slug>/assessment.md`. The test suite is not run again
here: step 1 is its evidence. Delegate browser flows when needed: {{DELEGATE:qa-automation-engineer}}.

### 4. Audit

Run the audits as [execution](references/execution.md) § Audits describes: Python detection
per `.redevkit/audits/README.md`; `verify_all.py` or `checklist.py` chosen by the Project Type
in `plan.md` (or `tech.md` for a lightweight spec), with `--url` of the app step 3 started;
`--no-runtime` only when the type has no runtime or the app did not start; always
`--no-tests` (step 1 is the test evidence). When the audits end, stop the app step 3 started
and confirm its port is free; stop it also when the run leaves steps 3–4 early (an error, a
gate, a timeout). No Python → `SKIPPED (no Python interpreter)` plus the project's own lint
and type-check commands.
Audit exit codes: `0` PASS, `1` FAIL, `2` usage error, `3` SKIPPED. Exit `3` is never a pass:
record `SKIPPED (<reason printed by the script>)`. One orchestrator run is the suite; give
the call a timeout above its duration or run it in the background, as the test procedure
does for the suite. Then triage the findings by file (same reference, step 6): only findings
in files the features in scope created or changed are **in scope**; findings in the rest of
the project are the **baseline**, and findings in third-party or generated code are out of
scope. Baseline and out-of-scope findings never become tasks or `failed`.

### 5. Report

Append a `## Run YYYY-MM-DD HH:MM — <verdict>` section (`## Execução …` in pt-BR) to
`specs/NNN-short-name/verification.md` of the active feature (create the file from the
template when missing; append-only, never edit a past run):

- Code state table, recorded as `{{SKILLDIR:redevkit-test}}/references/code-state.md`
  describes.
- Features in scope: the active feature and the Unverified features covered.
- Test evidence: the `test-report.md` run used, whether it ran in step 1 or was reused, its
  failure classes when it is `FAIL`, and its baseline failures.
- Convergence result per feature and the tasks appended.
- Execution evidence: commands with exit codes and observed results; critical flows walked;
  the app stop after the audits (port free).
- Audit table (`PASS`, `FAIL`, `SKIPPED (reason)`), runner and Project Type; in Notes, the
  findings counted as in scope, baseline and out of scope.
- **Not verified** list with reasons, including the open items of domain checklists
  (`checklists/<domain>.md`), the test run's Not verified scenarios and its baseline
  failures.
- Assumptions taken in this run.
- Verdict `converged+verified`, `gaps` or `failed` (rules in the reference), the Correction
  cycle counters and the Unverified line after step 6, and the next step. Tokens stay in
  English in every language. Date and time come from the system clock, never guessed.

The verify command does not edit application code. It writes test files and
`test-report.md` only through the test procedure of step 1.

### 6. Loop state and G5

Update the lines of `active.md` › Last results exactly as
`{{SKILLDIR:redevkit-test}}/references/loops.md` defines them: Failing scope (`global` when
the handoff is the debug command, otherwise `none`), Correction cycle (debug rounds and
rounds without convergence) and Unverified (`none` on `converged+verified`). Delete an
obsolete `- Verify pending:` line. When the Correction cycle reaches G5, follow `loops.md` §
G5: the chain stops, even in `--auto`.

## Gates that apply

| Gate | Where |
| --- | --- |
| G5 | Preconditions and step 6, the Correction cycle reached its limit |
| G4 | Steps 1 and 3, tests or flows that write to real external systems or delete data need confirmation |
| G3 | Step 1, a requirement can only be tested by violating the constitution; step 2, a CRITICAL constitution finding: stop and report |

## Artifacts

- `specs/NNN-short-name/verification.md` of the active feature (appended dated run with code
  state and verdict).
- `specs/NNN-short-name/test-report.md` and new test files, when step 1 ran the test
  procedure.
- The active feature's `tasks.md` with the appended `Phase N: Convergence` (when there are
  gaps).

## Memory phase 3

Save per `{{SKILL:redevkit-memanager}}`: `changelog.md` (verification event and verdict),
`active.md` › Last results (Test when step 1 ran the test procedure; Verify: date, verdict,
link, rewritten without the `invalidated by test FAIL` marker; Failing scope; Correction cycle; Unverified) and Known issues (failing tests or checks on
`failed`; on `converged+verified`, every `- Bug <slug>: open` of the features in scope becomes
`- Bug <slug>: closed (verify YYYY-MM-DD)`), `tech.md` when the test command was detected
or changed, `MEMORY.md`. Print `💾 Memory updated (files).`

## Evidence rule

Every line of the report comes from a command that ran and its observed output, or from the
reused `test-report.md` run it names. A skipped audit or flow is `SKIPPED (reason)`, never
`PASS`. `converged+verified` is allowed only when the test run is `PASS`, convergence found no
gaps in any feature in scope and every executed check passed (audit findings that are all out
of scope or baseline aside).

## Handoff

- G5 reached → no handoff; wait for the user's answer (`loops.md` § G5).
- `converged+verified` → `{{CMD:redevkit-deploy}}` (the user triggers it; this run stops), or
  `{{CMD:redevkit-plan}}` for the next feature.
- `gaps` → `{{CMD:redevkit-create}}` to implement the Convergence tasks, or
  `{{CMD:redevkit-enhance}}` when a gap needs a spec change; then `{{CMD:redevkit-test}}` and
  back to this command.
- `failed` → by what failed; the first that applies wins:
  - a `FAIL` test run whose failure class is `environment` → no command: name what must be
    fixed, then run `{{CMD:redevkit-verify}}` again (its step 1 never reuses an `environment`
    `FAIL`: the suite runs again);
  - a `FAIL` test run with `test-defect` left → no command: the question for the user is
    pending (a spec decision, or how to test a scenario still `MISSING`); once answered, run
    `{{CMD:redevkit-verify}}` again: its step 1 never reuses a `test-defect` `FAIL`, so the
    test procedure runs the whole suite again and corrects the test or follows the answer. This
    holds also when the defective test is outside the active feature's spec test set: never
    `{{CMD:redevkit-test}}` for it, whose spec scope does not run that test;
  - a `FAIL` test run with `not-implemented` → `{{CMD:redevkit-create}}` for the open tasks
    (only blocked `[!]` tasks → name them and what each needs);
  - anything else (a `product-defect`, a build failure, an application that does not start, a
    broken flow, a blocking audit) → `{{CMD:redevkit-debug}}` with the failing evidence
    (Failing scope `global`); the debug command hands back to this command, also when it
    judges the test wrong, and that handback counts as a debug round.
- `--auto`: `gaps` → continue with `{{CMD:redevkit-create}}` `--auto`; its chain runs the test
  command, whose `PASS` comes back here, and the Correction cycle bounds the loop. `failed` →
  continue with `{{CMD:redevkit-debug}}` `--auto`, or with `{{CMD:redevkit-create}}` `--auto`
  for `not-implemented` with open `[ ]` tasks; stop on `environment`, on `test-defect` and
  when only blocked tasks remain. `converged+verified` → stop before the deploy.
