---
name: redevkit-debug
description: Fix a failure - reproduce, root cause, regression test first, fix, bug record; then verify.
short-description: Fix a bug with a regression test
argument-hint: "[--auto] <symptom, error or failing test>"
---

# redevkit-debug

**Input:** {{ARGS}}

Flags: `--auto` continues to the verify command. The rest of the input describes the symptom
(error message, failing test, unexpected behavior). With no input, take the failing tests of
the latest `FAIL` run in the active feature's `test-report.md`. Write artifacts in {{LANG}};
answer the user in the user's language.

## Purpose

Investigate and fix one problem with evidence (D26): reproduce it, find the root cause, write
a regression test that fails, fix, confirm. Every step leaves a file in
`.redevkit/bugs/<slug>/`. The hand-off to the verify command is mandatory.

## Preconditions

- Memory initialized. If not, suggest `{{CMD:redevkit-new}}` and stop.
- A symptom: the input, or a `FAIL` run in `test-report.md`. If neither exists, ask for the
  error, the steps to reproduce and the expected vs actual behavior.
- G5 check: if the Correction cycle line names the active feature and says G5 was reached,
  present the G5 question before starting (answers at a precondition: `{{CMD:redevkit-verify}}`
  step 6).
- Templates resolve per T10: `.redevkit/templates/overrides/reports/<name>` if it exists,
  otherwise `.redevkit/templates/reports/<name>` (`bug-assessment.md`, `bug-fix.md`,
  `bug-test.md`).

## Memory phase 1

Recall per `{{SKILL:redevkit-memanager}}`: `MEMORY.md`, `active.md` (Known issues, Last
results), the invariants in `system.md`, `tech.md` (build and test commands). Read
`.redevkit/memory/constitution.md`. Print `📖 Memory loaded. Last entry: YYYY-MM-DD.`

## Questions

Ask before assuming, but only what changes the investigation: one question at a time, at most
3 options with the recommended one first and marked "(Recommended)", at most 5 questions in
this run. Record every assumption in `assessment.md`. Personas never ask the user: they return
the question to you. In `--auto` or non-interactive runs, adopt the recommendation and record
it as an assumption, except at gates.

{{ASK}}

## Steps

### 1. Slug

Short name of the symptom, following the slug rule of `{{SKILL:redevkit-assess-intake}}`. An
**open bug** is one listed as `- Bug <slug>: open` in `active.md` › Known issues. When an open
bug matches the symptom:

- its folder lacks `fix.md` or `test.md` (an interrupted debug) → ask to continue it
  (Recommended) or open a new one; continuing resumes at the first missing file
  (`assessment.md` → step 2, `fix.md` → step 3, `test.md` → step 4) and never rewrites an
  existing one;
- its `test.md` exists (any result) → open a new bug linked to it (**Related bug** in
  `assessment.md`); the old folder is never rewritten.

### 2. Assess

Follow `{{SKILL:redevkit-bug-assess}}` with the debugging persona and
`{{SKILL:systematic-debugging}}`: {{DELEGATE:debugger}}.

- Gather: error message, reproduction steps, expected vs actual, recent changes
  (`git log`, `git diff`, read-only).
- Reproduce with a command and record its output.
- List hypotheses ordered by likelihood; test each one; eliminate with evidence.
- Root cause explained (why, not only what).
- `assessment.md` links to the feature (`specs/NNN-short-name/spec.md`) and to the
  `test-report.md` run that exposed the problem.

Cannot reproduce: record what was tried and ask for more information; do not guess a fix. In
`--auto` or a non-interactive run, stop the chain here with the question pending: no fix, no
handoff to verify. Memory: only `- Bug <slug>: open` in Known issues, no `- Debug:` line
(nothing was changed, so nothing is pending for the verify).

Verdict `invalid` (expected behavior, misuse, duplicate): stop. Write no `- Debug:` or
`- Bug` line, report the reason and suggest `{{CMD:redevkit-status}}`; no handoff to verify.

### 3. Fix

Follow `{{SKILL:redevkit-bug-fix}}`:

1. Write the regression test first; run it; record that it fails for the root cause.
2. Apply the smallest fix that addresses the root cause. When the fix belongs to another
   domain, choose its persona with `{{SKILL:redevkit-route}}`.
3. Run the regression test; record that it passes.
4. Add prevention (validation, guard, test) when the root cause can recur.

A fix that would violate the constitution stops the run (G3). A destructive or irreversible
step (data migration, deleting data or files) needs explicit confirmation (G4).

### 4. Confirm

Follow `{{SKILL:redevkit-bug-test}}`: run the regression test, the related tests and the
original reproduction. `test.md` records the result: `verified`, `partial` or `failed`.

### 5. Light verification (D25)

On the changed files, with evidence: build or type check, touched tests, lint. This is not the
full verification: the verify command runs the full test procedure and the rest next.

## Gates that apply

| Gate | Where |
| --- | --- |
| G3 | Step 3, the fix would violate the constitution |
| G4 | Step 3, destructive or irreversible actions |
| G5 | Preconditions, G5 reached and not answered yet |

## Artifacts

- `.redevkit/bugs/<slug>/assessment.md`, `fix.md`, `test.md`.
- The regression test and the fix in the code.

## Memory phase 3

Save per `{{SKILL:redevkit-memanager}}`: `active.md` › Last results › Debug (active feature, bug
slug, date and time, `test.md` result, link to the bug folder; the verify command uses it to know that it
follows a debug) and Known issues (`- Bug <slug>: open — .redevkit/bugs/<slug>/`; only a `converged+verified`
verify of that feature closes it; a bug debugged with no active feature is closed by the user
through `{{SKILL:redevkit-memanager}}`), `changelog.md`
(Unreleased › Fixed, only when `test.md` says `verified`), `system.md` when the root cause
reveals a pattern (a new invariant only after confirmation), `MEMORY.md`. Print
`💾 Memory updated (files).`

## Evidence rule

The reproduction, the failing regression test, the passing test after the fix and the light
verification each show the command and its observed output. No hypothesis is called the root
cause without a test that confirms it.

## Handoff

- Cannot reproduce or `invalid` (step 2) → no handoff; the run ends with the question or the
  reason.
- Otherwise always → `{{CMD:redevkit-verify}}` (mandatory after a debug, whatever `test.md` says): it
  runs the test procedure on the fixed code, then the full verification, and decides whether
  the code can go to deploy.
- `--auto`: continue with `{{CMD:redevkit-verify}}` `--auto`.
