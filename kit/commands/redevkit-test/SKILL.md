---
name: redevkit-test
description: Map spec scenarios to tests, generate missing ones, run the spec tests and append a test report.
short-description: Test the active spec (generate and run)
argument-hint: "[--auto]"
---

# redevkit-test

**Input:** {{ARGS}}

Flags: `--auto` follows the handoff on its own: to the verify command on `PASS`, and on `FAIL`
to the command its failure class names. There is no other argument: this command always
tests the active feature (`active.md` › Active feature), normally the newest spec. Write
artifacts in {{LANG}}; answer the user in the user's language.

## Purpose

Prove the active feature against its spec (D26, D37) in the **spec scope**: map every
acceptance scenario to a test, generate the tests that are missing, run the tests of this
feature only, classify what failed and append a dated run with the code state to
`test-report.md`. A red run loops test → debug → test, at most 5 debug rounds before G5. A
green run proves the feature, not the project: the whole suite, the convergence and the audits
are the verify command's job (global scope), and only a verify opens the way to the deploy.
The two loops are defined in [loops](references/loops.md). This command does not change
application code. Steps 1–6 are also step 1 of `{{CMD:redevkit-verify}}`, which runs them in
the global scope, without this file's memory phases, handoff and `--auto` continuation.

## Preconditions

- Memory initialized. If not, suggest `{{CMD:redevkit-new}}` and stop.
- An active feature with `spec.md`. With no feature at all, run the whole suite only, report
  in the answer and in `active.md` › Last results, and suggest `{{CMD:redevkit-plan}}`;
  `--auto` never continues from here.
- G5 not pending: if the Test cycle line names the active feature and says G5 was reached,
  present the G5 question again before anything else ([loops](references/loops.md) § G5).
- Open work: when `tasks.md` still has open `[ ]` or blocked `[!]` tasks, say so in one line
  (count and IDs) and continue. The tests still run; a failure inside the scope of such a
  task is `not-implemented` (step 4), never a bug.
- Templates resolve per T10: `.redevkit/templates/overrides/reports/test-report.md` if it
  exists, otherwise `.redevkit/templates/reports/test-report.md`.

## Memory phase 1

Recall per `{{SKILL:redevkit-memanager}}`: `MEMORY.md`, `active.md` (active feature, latest
results, Failing scope, Test cycle), the invariants in `system.md`, and `tech.md` (test
command, frameworks). Print `📖 Memory loaded. Last entry: YYYY-MM-DD.`

## Questions

Ask only what changes scope or architecture, one question at a time, at most 3 options with
the recommended one first and marked "(Recommended)", at most 5 questions in this run. Record
every assumption in the report (Assumptions section). Personas never ask: they return the question to you. In
`--auto` or non-interactive runs, adopt the recommendation and record it as an assumption,
except at gates.

{{ASK}}

## Steps

Steps 1–6 take a **scope**: `spec` in this command, `global` when the verify command runs
them. Where a step differs, it says so.

### 1. Map scenarios to tests

Read the acceptance scenarios of `spec.md` (user stories, `## Clarifications` /
`## Esclarecimentos`, `## Enhancements` / `## Melhorias`) and `quickstart.md`. Map unit and integration coverage:
{{DELEGATE:test-engineer}}. Map end-to-end flows (browser, Playwright) with
`{{SKILL:webapp-testing}}`: {{DELEGATE:qa-automation-engineer}}. Build the table scenario →
test file and name → `covered` or `missing`. Both scopes map the active feature only.

### 2. Generate the missing tests

Following `{{SKILL:testing-patterns}}` and `{{SKILL:tdd-workflow}}`: use the project's test
framework and existing patterns, test behavior not implementation, Arrange-Act-Assert,
descriptive names, mock external services. Do not touch application code and never change an
assertion that matches the spec to make a test pass. A scenario that cannot be automated is
listed as such, with the reason.

### 3. Run the tests

**What runs.** Scope `spec`: the **spec test set**, the union of the test files of the step 1
table (the ones step 2 generated or corrected included), the test files among the paths of
`tasks.md` tasks, and the regression tests named in the `fix.md` of this feature's bugs (bug
folders whose `assessment.md` links this feature). Tests the user asks for that cover behavior
outside this spec are generated and listed under **Outside the spec**, but they are not in the
set and never decide this run's verdict: the verify runs them with the whole suite.
An empty set runs the whole suite. Scope `global`: the whole suite, end-to-end tests included.

Every run is non-interactive and bounded:

- Never start watch mode or a command that waits for input. Use the one-shot form
  (`vitest run`, `jest --ci`, `CI=1` in the environment); the audit runner already does.
- A suite can take minutes: give the shell call a timeout above the expected duration (the
  Claude Code Bash tool accepts up to 600000 ms), or run it in the background and wait for it
  to finish. Never leave a suite running while you go on.
- Keep the full output in `.redevkit/tmp/test-output.log` (create the folder when missing; git
  ignores it) and read the failing tests from the end of it.

1. Detect a Python interpreter as `.redevkit/audits/README.md` describes (try `python`, then
   `py -3` on Windows, then `python3`; each validated by running `--version`).
2. Python found → run
   `<PY> .redevkit/audits/test_runner.py . --log .redevkit/tmp/test-output.log` from the
   project root; in scope `spec` add `--paths` followed by the spec test set. Add `--coverage`
   to collect coverage, `--timeout SECONDS` when the suite needs more than 300 seconds. Exit
   `3` means SKIPPED, never PASS: fall back to the project command. A `[TIMEOUT]` line is an
   `environment` failure (step 4): do not run the same command again unchanged. The runner
   prints `Scope: paths (N)`, or `Scope: full suite (reason)` when the test command cannot
   take files: then the report's Scope is `spec (full suite)`.
3. No Python, or the runner cannot drive this project → run the project test command from
   `tech.md` › Dev environment, with the spec test set as file arguments when the command
   takes them (otherwise the whole suite, Scope `spec (full suite)`). If `tech.md` has none,
   detect it (`package.json` `scripts.test`, `pytest`, `go test ./...`, `cargo test`,
   `dotnet test`, …) and record it.
4. Collect coverage when the tool provides it. Capture for each command: the command line,
   exit code, duration, passed/failed/skipped counts and the message of each failing test.

### 4. Classify the failures

A red run has more than one cause, and each cause has its own owner. Give every failure
exactly one class; the first row that fits wins:

| Class | When | What happens |
| --- | --- | --- |
| `environment` | The suite could not run or finish: missing dependency or tool, runner crash before any test, `[TIMEOUT]`, port in use, no test framework | Not a bug. Fix it now when that needs no application code (install per `tech.md`, a one-shot flag, a longer `--timeout`, freeing a port this run took) and run once more; otherwise report what is needed |
| `baseline` | Scope `global` only, while the project has never had a fully green whole-suite run (no run of any `specs/*/test-report.md` with Scope `global`, or kit 1.1's `feature`, that is `PASS` with no baseline failure): a test in a file that neither the active feature nor an Unverified feature created or changed (the in-scope files of `{{SKILLDIR:redevkit-verify}}/references/execution.md` § Audits step 6), whose failure does not point at code those features changed (the stack trace or the module under test is outside their in-scope files) | Pre-existing, not this feature's. Listed under **Baseline failures** and in Not verified; never a task, never debugged, never makes the run FAIL. After the first fully green whole-suite run every red test is a regression and this class no longer applies |
| `test-defect` | The test is wrong: it contradicts the spec, or fails by its own error (syntax, test helper import, fixture, selector) while the behavior it targets is right | Correct the test code only: {{DELEGATE:test-engineer}}. Cite the spec scenario or the error as evidence, list it under Tests corrected and run once more |
| `not-implemented` | The behavior belongs to an open `[ ]` or blocked `[!]` task of `tasks.md` | Not a bug: it goes to the create command |
| `product-defect` | The test matches the spec and the code behaves differently | It goes to the debug command (the loop) |

Limits: one extra run for environment fixes and one for test corrections; what is still red
after that keeps its class. When the debug command sent a failure back as a wrong test (its
handoff names the test and the evidence) and you still judge it a `product-defect`, the spec
is unclear: it stays `test-defect` and you ask the user; never send it to the debug command
again.

**Outside the spec.** A test outside the spec test set is not this run's: the tests generated
on request for behavior outside the spec, and, in scope `spec (full suite)` (the whole suite
ran only because the test command cannot select files), every other test of the suite. A
failure there is not this run's.
List it under **Outside the spec** (in Not verified) without a class; it never makes the run
FAIL. The verify command judges the whole suite. A test whose correction needs a spec decision (spec and test
disagree and the spec is unclear) stays `test-defect`: stop and ask the user. Record the class
of each failure and the classes that remain in the report (**Failure class**).

### 5. Record the code state

Right after the last run, record the code state exactly as
[code-state](references/code-state.md) describes (`code_state.py`: HEAD, branch, working tree,
changed files and the Tree fingerprint).

### 6. Append the report

Append a `## Run YYYY-MM-DD HH:MM — PASS|FAIL` section (`## Execução AAAA-MM-DD HH:MM — PASS|FAIL`
in pt-BR; date and time read from the system clock, never guessed) to
`specs/NNN-short-name/test-report.md` (create the file from the template when
missing; the file is append-only, never edit a past run): **Run by** (`redevkit-test`, or
`redevkit-verify (step 1)` inside the verify command; literal values, in English in every
language), **Scope** (`spec`, `spec (full suite)` or `global`), the spec test set in scope
`spec`, Code state table, commands executed, results with the class of each failure,
baseline failures (scope `global`), acceptance-scenario coverage (`PASS`, `FAIL`,
`SKIPPED (reason)`, `MISSING`), tests generated and corrected, verdict and next step. Tokens
stay in English in every language.

Verdict: **PASS** only when every command exited 0 (in scope `global`, or failed only by
`baseline` failures), no other test failed and every acceptance scenario that can be
automated maps to a passing test. Anything else is **FAIL**, including a suite that could not
run or an automatable scenario left `MISSING`; a `FAIL` run always names its failure classes,
and the handoff follows them.

A scenario that cannot be automated in this environment (human visual review, a reference
device, real OS or browser events the harness cannot produce) is `SKIPPED (reason)` and is
listed under **Not verified** in the report. It does not make the run FAIL (D26: red means a
failing test, and debug cannot fix a missing human check), but it is never counted as
`PASS`: the handoff names the manual checks left.

## Gates that apply

| Gate | Where |
| --- | --- |
| G5 | Preconditions and Handoff: the Test cycle reached 5 debug rounds ([loops](references/loops.md)) |
| G4 | Tests that hit real external services, real databases or delete data need confirmation |
| G3 | A requirement can only be tested by violating the constitution: stop and report |

## Artifacts

- New and corrected test files.
- `specs/NNN-short-name/test-report.md` (appended dated run with the scope and the code state).

## Memory phase 3

Save per `{{SKILL:redevkit-memanager}}`: `active.md` › Last results › Test (date, verdict,
scope, failure classes on `FAIL`, run by, command, link to the run), Failing scope and Test
cycle as [loops](references/loops.md) defines (`PASS` resets the debug rounds), and Known
issues (failing tests on `FAIL`); `tech.md` when the test command was detected or changed;
`MEMORY.md`. Print `💾 Memory updated (files).`

## Evidence rule

The verdict comes only from commands that ran and their exit codes and counts, copied into the
report. A step that did not run is `SKIPPED (reason)`, never `PASS`. Never write `PASS` when
a test that is not `baseline` failed, errored or was not executed because the runner crashed.

## Handoff

- `PASS` → `{{CMD:redevkit-verify}}` (Recommended): it runs the whole suite, the convergence
  and the audits, and it is the only way to the deploy. Or `{{CMD:redevkit-plan}}` for the
  next feature: this one then goes to the Unverified list and the next verify covers it.
  Name the manual checks left, if any. Never the deploy.
- `FAIL`, by failure class; the first that applies wins:
  - `environment` → no command: name what must be fixed, then run `{{CMD:redevkit-test}}`
    again. Never send an environment failure to the debug command.
  - `test-defect` left → no command: the question about the spec is pending for the user.
  - `not-implemented` → `{{CMD:redevkit-create}}` for the open tasks. When only blocked `[!]`
    tasks cover it, name them and what each needs; the user resolves that or revises the
    plan with `{{CMD:redevkit-plan}}`.
  - `product-defect` → `{{CMD:redevkit-debug}}` with the failing tests and the report run
    (Failing scope `spec`), unless the Test cycle has 5 debug rounds: then G5
    ([loops](references/loops.md) § G5) and no handoff until the user answers.
- `--auto`: `PASS` → continue with `{{CMD:redevkit-verify}}` `--auto`. `FAIL`: `environment` or
  `test-defect` left → stop; `not-implemented` with open `[ ]` tasks → continue with
  `{{CMD:redevkit-create}}` `--auto` (only blocked tasks → stop); `product-defect` → continue
  with `{{CMD:redevkit-debug}}` `--auto`; G5 → stop.
