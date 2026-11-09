---
name: redevkit-test
description: Map spec scenarios to tests, generate missing ones, run the full suite and append a test report.
short-description: Generate missing tests and run the suite
argument-hint: "[--auto] [feature, file or scenario]"
---

# redevkit-test

**Input:** {{ARGS}}

Flags: `--auto` continues to the debug command when the run is `FAIL`. Optional scope: a
feature (`specs/NNN-short-name`), a file or a scenario; default is the active feature. Write
artifacts in {{LANG}}; answer the user in the user's language.

## Purpose

Prove the feature against its spec (D26, D37): map every acceptance scenario to a test,
generate the tests that are missing, run the complete suite and append a dated run with the
code state (HEAD, tree state, fingerprints) to `test-report.md`; the deploy compares with it.
This command does not change application code. Steps 1–5 are also step 1 of
`{{CMD:redevkit-verify}}`, which runs them without this file's memory phases, handoff and
`--auto` continuation.

## Preconditions

- Memory initialized. If not, suggest `{{CMD:redevkit-new}}` and stop.
- An active feature (or the one given) with `spec.md`. With no feature at all, run the suite
  only, report in the answer and in `active.md` › Last results, and suggest
  `{{CMD:redevkit-plan}}`; `--auto` never continues from here.
- Templates resolve per T10: `.redevkit/templates/overrides/reports/test-report.md` if it
  exists, otherwise `.redevkit/templates/reports/test-report.md`.

## Memory phase 1

Recall per `{{SKILL:redevkit-memanager}}`: `MEMORY.md`, `active.md` (active feature, latest
results), the invariants in `system.md`, and `tech.md` (test command, frameworks). Print
`📖 Memory loaded. Last entry: YYYY-MM-DD.`

## Questions

Ask only what changes scope or architecture, one question at a time, at most 3 options with
the recommended one first and marked "(Recommended)", at most 5 questions in this run. Record
every assumption in the report (Assumptions section). Personas never ask: they return the question to you. In
`--auto` or non-interactive runs, adopt the recommendation and record it as an assumption,
except at gates.

{{ASK}}

## Steps

### 1. Map scenarios to tests

Read the acceptance scenarios of `spec.md` (user stories, `## Clarifications` /
`## Esclarecimentos`, `## Enhancements` / `## Melhorias`) and `quickstart.md`. Map unit and integration coverage:
{{DELEGATE:test-engineer}}. Map end-to-end flows (browser, Playwright) with
`{{SKILL:webapp-testing}}`: {{DELEGATE:qa-automation-engineer}}. Build the table scenario →
test file and name → `covered` or `missing`.

### 2. Generate the missing tests

Following `{{SKILL:testing-patterns}}` and `{{SKILL:tdd-workflow}}`: use the project's test
framework and existing patterns, test behavior not implementation, Arrange-Act-Assert,
descriptive names, mock external services. Do not touch application code and never weaken an
existing test to make it pass. A scenario that cannot be automated is listed as such, with the
reason.

### 3. Run the full suite

1. Detect a Python interpreter as `.redevkit/audits/README.md` describes (try `python`, then
   `py -3` on Windows, then `python3`; each validated by running `--version`).
2. Python found → run `.redevkit/audits/test_runner.py` with the arguments the README gives
   (exit `3` means SKIPPED, never PASS: fall back to the project command). No Python, or the runner cannot drive this project → run the project test command from
   `tech.md` › Development environment. If `tech.md` has none, detect it (`package.json`
   `scripts.test`, `pytest`, `go test ./...`, `cargo test`, `dotnet test`, …) and record it.
3. Include the end-to-end tests when the project has them. Collect coverage when the tool
   provides it.
4. Capture for each command: the command line, exit code, duration, passed/failed/skipped
   counts and the message of each failing test.

### 4. Record the code state

Right after the suite, record HEAD, branch, working tree, changed files and the two
fingerprints exactly as [code-state](references/code-state.md) describes.

### 5. Append the report

Append a `## Run YYYY-MM-DD HH:MM — PASS|FAIL` section (`## Execução AAAA-MM-DD HH:MM — PASS|FAIL`
in pt-BR) to `specs/NNN-short-name/test-report.md` (create the file from the template when
missing; the file is append-only, never edit a past run): **Run by** (`redevkit-test`, or
`redevkit-verify (step 1)` inside the verify command; literal values, in English in every
language), **Scope** (`feature`, or the file or scenario given; only feature-wide runs are reused by verify or accepted by deploy), Code state
table, commands executed, results,
acceptance-scenario coverage (`PASS`, `FAIL`, `SKIPPED (reason)`, `MISSING`), tests generated,
verdict and next step. Tokens stay in English in every language.

Verdict: **PASS** only when every command exited 0, no test failed and every acceptance
scenario that can be automated maps to a passing test. Anything else is **FAIL**, including a
suite that could not run or an automatable scenario left `MISSING`.

A scenario that cannot be automated in this environment (human visual review, a reference
device, real OS or browser events the harness cannot produce) is `SKIPPED (reason)` and is
listed under **Not verified** in the report. It does not make the run FAIL (D26: red means a
failing test, and debug cannot fix a missing human check), but it is never counted as
`PASS`: the handoff names the manual checks left and suggests `{{CMD:redevkit-verify}}`.

## Gates that apply

| Gate | Where |
| --- | --- |
| G4 | Tests that hit real external services, real databases or delete data need confirmation |
| G3 | A requirement can only be tested by violating the constitution: stop and report |

## Artifacts

- New test files.
- `specs/NNN-short-name/test-report.md` (appended dated run with the code state).

## Memory phase 3

Save per `{{SKILL:redevkit-memanager}}`: `active.md` › Last results › Test (date, verdict, run
by, command, link to the run) and Known issues (failing tests on `FAIL`); `tech.md` when the
test command was detected or changed; `MEMORY.md`. Print `💾 Memory updated (files).`

## Evidence rule

The verdict comes only from commands that ran and their exit codes and counts, copied into the
report. A step that did not run is `SKIPPED (reason)`, never `PASS`. Never write `PASS` when
any test failed, errored or was not executed because the runner crashed.

## Handoff

- `PASS` (green) → `{{CMD:redevkit-deploy}}` (user-triggered only); suggest
  `{{CMD:redevkit-verify}}` first for the full verification. A verify run right after this one,
  on the same code, reuses this run instead of running the tests again.
- `FAIL` (red) → `{{CMD:redevkit-debug}}` with the failing tests and the report run.
- `--auto`: `PASS` → stop and suggest `{{CMD:redevkit-verify}}` and then
  `{{CMD:redevkit-deploy}}`; `FAIL` → continue with `{{CMD:redevkit-debug}}` `--auto`.
