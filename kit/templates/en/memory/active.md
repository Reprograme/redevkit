---
type: active
created: "YYYY-MM-DD"
updated: "YYYY-MM-DD"
---

# Active context

## Active feature

- Feature: [specs/NNN-name or none]
- Phase: [specify | plan approved | implementation | test | debug | verify | deploy]
- Plan approved: [YYYY-MM-DD | no]
- Branch: [branch name or none]

## Where we are

[One to three sentences on the current state of the work.]

## Recent events

<!-- Newest first. Format: - YYYY-MM-DD — what happened — why. Above 256 lines, old events are
     summarized into changelog.md › Consolidated history. -->

- [YYYY-MM-DD] — [what happened] — [why]

## What works

- [Feature or part of the system that works and was verified.]

## What's left

- [What still needs to be built, in priority order.]

## Next steps

- [What comes next. This is a plan, not a fact.]

## Known issues

- Bug [slug]: [open | closed (verify YYYY-MM-DD)] — [.redevkit/bugs/slug/]
- [Limitation or technical debt not yet resolved.]

## Last results

- Test: [PASS | FAIL] — [YYYY-MM-DD HH:MM] — [run by redevkit-test | redevkit-verify (step 1)] — [command] — [report path]
- Verify: [converged+verified | gaps | failed] — [YYYY-MM-DD HH:MM] — [report path]
- Debug: [specs/NNN-name] — [bug slug] — [YYYY-MM-DD HH:MM] — [verified | partial | failed] — [.redevkit/bugs/slug/]
- Correction cycle: [specs/NNN-name] — failed after debug [N]/2 · rounds without convergence [N]/3 [· G5 reached YYYY-MM-DD HH:MM, waiting for the user]

## Workflow preferences

- Branch per feature: [always | never | ask]
- [Other workflow preference, for example commit only when asked.]
