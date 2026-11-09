---
name: redevkit-bug-fix
description: Write a failing regression test, then fix the bug's root cause.
---

# Bug: fix

Second step of `{{CMD:redevkit-debug}}`. Turn the assessment into a regression test that
fails, then fix the root cause, verify lightly and write `.redevkit/bugs/<slug>/fix.md`.

## Input

The calling command passes the slug (usually reported by `{{SKILL:redevkit-bug-assess}}` in
the same session) and the mode.

## Rules

- **Test first (D37)**: the regression test exists and fails before any source change. If
  `.redevkit/memory/constitution.md` waives test-first by amendment, record the waiver and
  still add the regression test after the fix.
- **Minimal change**: fix the root cause, one change at a time, inside the files the
  assessment lists. Log any scope expansion under Deviations. No unrelated refactors, no new
  dependencies the assessment did not call for.
- **Contract**: `assessment.md` is read-only here. Record disagreements in `fix.md`.
- **Evidence**: never claim a result without the command that ran and its observed output.
- **Gates**: a constitution violation stops for the user (G3). Destructive or irreversible
  actions — deleting files the assessment did not require, data-dropping migrations — need
  explicit confirmation (G4), even in auto mode. Never commit; commits happen only when the
  user asks.
- **Language**: write the artifact in {{LANG}}. Keep status and result tokens in English.

## Slug

1. Resolve in order: slug given by the caller → slug reported earlier in this session
   (confirmed by `.redevkit/bugs/<slug>/assessment.md`) → the only bug with
   `assessment.md` and without `fix.md` → ask (interactive) or stop listing the candidates
   (auto). Never guess.
2. Normalize it and check path safety per the slug rule in
   `{{SKILL:redevkit-assess-intake}}`.

## Questions

Ask only when the answer changes what gets built: proceeding on a `likely-valid` assessment
with open `[NEEDS CLARIFICATION]` items, expanding scope beyond the assessed files, or a G3
or G4 situation. Questions count toward the calling command's limit of 5. If you run as a
subagent, return the question to the orchestrator instead of asking.

{{ASK}}

## Preconditions

- `assessment.md` must exist; otherwise stop and send the caller back to
  `{{SKILL:redevkit-bug-assess}}`. Read it in full: remediation, files, regression test and
  risks are the contract.
- Verdict `invalid`: stop; there is nothing to fix.
- Verdict `likely-valid` with open questions: interactive, ask whether to reproduce first
  (Recommended) or proceed; auto, stop and report that reproduction is needed.
- If `fix.md` exists, never overwrite it: interactive, ask; auto, stop and report.

## Steps

1. **Restate the plan** in 3–6 bullets: test, change, files.
2. **Write the regression test** at the lowest level that shows the symptom, following
   `{{SKILL:tdd-workflow}}` and `{{SKILL:testing-patterns}}`.
3. **Run it and see it fail** for the reason in the assessment (the assertion or error
   matches the symptom). Keep the command and the failing output.
   - It passes: the test misses the bug. Adjust it. If it still cannot fail, stop editing,
     record the finding under Deviations, set status `not-applied` and continue to the
     bug test (see step 7).
   - The bug cannot be captured by an automated test (environment-only): record why and use
     the scripted reproduction from the assessment as the failing check.
4. **Fix the root cause.** For a fix in a specialist domain, pick the persona with
   `{{SKILL:redevkit-route}}` and delegate it with the assessment and the failing test;
   otherwise apply it yourself or delegate the investigation-heavy part:
   {{DELEGATE:debugger}}.
5. **Run the regression test again** and see it pass. Keep the output.
6. **Light verification** (D25): run the tests of the changed modules and the lint or
   type-check for changed files when the project has them (commands from
   `.redevkit/memory/tech.md` or the project scripts). Skip destructive or network suites
   without consent and record `SKIPPED (reason)`.
7. **If the fix does not hold** or the root cause is elsewhere, stop changing code, record
   it under Deviations, set status `partial` or `not-applied`, write `fix.md` (steps 8–9)
   and continue to `{{SKILL:redevkit-bug-test}}`: the calling debug continues to the verify
   command, and the next debug opens a new bug folder linked to this one. Never start a new
   assessment inside the same debug run.
8. **Record the code state**: `git rev-parse HEAD` and `git status --porcelain`.
9. **Write** `.redevkit/bugs/<slug>/fix.md`. Template: use
   `.redevkit/templates/overrides/reports/bug-fix.md` if it exists, otherwise
   `.redevkit/templates/reports/bug-fix.md`. Status: `applied`, `partial` or `not-applied`.

## Return

Report to the calling command: `Slug: <slug>` on its own line, the path of `fix.md`, the
status, the regression test (failing before, passing after), and the next phase:
`{{SKILL:redevkit-bug-test}}`.
