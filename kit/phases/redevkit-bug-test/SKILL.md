---
name: redevkit-bug-test
description: Re-run a fixed bug's reproduction and suite; record verified, partial or failed.
---

# Bug: test

Third step of `{{CMD:redevkit-debug}}`. Prove by execution that the fix removes the bug and
breaks nothing, then write `.redevkit/bugs/<slug>/test.md` with the result `verified`,
`partial` or `failed`. Never change source code here.

## Input

The calling command passes the slug (usually reported by `{{SKILL:redevkit-bug-fix}}` in
the same session) and the mode.

## Rules

- **Evidence**: every check records the command, its exit code and an output excerpt. A
  check that did not run is `SKIPPED (reason)`, never `PASS`.
- **No over-claiming**: never mark `verified` when the original reproduction was not
  actually exercised; downgrade to `partial` and say why.
- **Writes** go only to `.redevkit/bugs/<slug>/`.
- **Language**: write the artifact in {{LANG}}. Keep result tokens (`verified`, `partial`,
  `failed`, `PASS`, `FAIL`, `SKIPPED`) in English.

## Slug

1. Resolve in order: slug given by the caller → slug reported earlier in this session
   (confirmed by `.redevkit/bugs/<slug>/fix.md`) → the only bug with `fix.md` and without
   `test.md` → ask (interactive) or stop listing the candidates (auto). Never guess.
2. Normalize as in `{{SKILL:redevkit-bug-assess}}` and refuse symlinked or escaping paths.

## Questions

Ask only for consent to run a destructive, network-dependent or expensive check. Without
consent (or in auto mode), skip it and record `SKIPPED (reason)`. Questions count toward
the calling command's limit of 5. If you run as a subagent, return the question to the
orchestrator instead of asking.

{{ASK}}

## Preconditions

- `assessment.md` and `fix.md` must exist; otherwise stop and send the caller back to the
  missing phase. Read both: the symptom and reproduction come from the assessment, the
  changes and the regression test from the fix.
- If `test.md` exists, never overwrite it: interactive, ask; auto, stop and report.

## Steps

1. **Plan the checks.** To prove the bug is gone: the original reproduction and the
   regression test. To prove nothing broke: the relevant suite (tests of the changed
   modules and of the feature; the full suite when the project has no narrower command) and
   lint or type-check when configured. Take commands from `.redevkit/memory/tech.md` or the
   project scripts.
2. **Run each check.** Record command, exit code and a short excerpt (final summary lines
   or the failing assertion).
3. **Judge the result**:
   - `verified`: the original reproduction no longer fails, the regression test passes and
     the relevant suite is green;
   - `partial`: the symptom is gone but a check is inconclusive or skipped, or an unrelated
     regression appeared;
   - `failed`: the symptom still reproduces, or the fix breaks the suite.
4. **Record the code state**: `git rev-parse HEAD` and `git status --porcelain`.
5. **Write** `.redevkit/bugs/<slug>/test.md`. Template: use
   `.redevkit/templates/overrides/reports/bug-test.md` if it exists, otherwise
   `.redevkit/templates/reports/bug-test.md`.

## Return

Report to the calling command: `Slug: <slug>` on its own line, the path of `test.md` and the
result. By result:

- `verified` or `partial` → the calling command continues to `{{CMD:redevkit-verify}}`
  (mandatory after debug); a `partial` names what remains unproven.
- `failed` → a new `{{SKILL:redevkit-bug-assess}}` with the evidence in `test.md`, in a new
  directory linked to this one. Two failed debug → verify cycles in a row stop for the user
  (G5).

The calling command records open or closed bugs in `.redevkit/memory/active.md`.
