---
name: redevkit-specify
description: Create specs/NNN-name/spec.md, run its quality loop and set it active.
---

# redevkit-specify

Internal phase. Writes WHAT the feature must do and WHY, never HOW. Called by
`{{CMD:redevkit-plan}}` (step specify) and by `{{CMD:redevkit-enhance}}` (light spec when no
feature matches).

Write the spec in the project language ({{LANG}}). Answer the user in their language.

## Input (from the calling command)

- The feature description the user gave to the command. If it is empty, stop and ask the
  caller for it; never invent a feature.
- Mode: `full` (default) or `light` (enhance: only the stories and requirements the change
  touches).
- `--auto` flag, if the command runs in auto mode.
- Optional: an assessment brief from `.redevkit/assessments/<slug>/decision.md` (after a
  `go` in `{{CMD:redevkit-brainstorm}}`).

One invocation creates at most one feature. If `.redevkit/memory/active.md` already points to
a feature with the same intent, update that spec instead of creating a new one.

## Steps

1. **Short name.** Derive 2-4 meaningful words from the description, in action-noun form
   (`user-auth`, `fix-payment-timeout`, `analytics-dashboard`). Lowercase ASCII kebab-case:
   transliterate accents (`autenticação` → `autenticacao`), keep acronyms (`oauth2-api`),
   at most 40 characters.
2. **Next number (D53).** List the directories in `specs/` whose names start with three or
   more digits and a hyphen. `NNN` = highest number + 1, zero-padded to 3 digits (`001` when
   `specs/` is empty or missing; after `999`, continue with `1000`). Use the highest number,
   not the count, so gaps are never reused.
3. **Collision check.** Re-list `specs/` right before creating the directory. If any
   `specs/NNN-*` already exists, take the next free number. If duplicates already exist
   (for example two `specs/004-*` after merging branches), report them and offer to
   renumber the most recently created one to the next free number: rename the directory,
   update its references (`spec.md` header, `plan.md`, `tasks.md`, `active.md`) and leave
   the branch name unchanged. Renaming needs the user's confirmation.
4. **Create** `specs/NNN-short-name/`.
5. **Resolve the template.** Use `.redevkit/templates/overrides/spec.md` if it exists,
   otherwise `.redevkit/templates/spec.md`. Use it as the structure of
   `specs/NNN-short-name/spec.md`.
6. **Load constraints.** Read `.redevkit/memory/constitution.md`, `project.md` (scope, out of
   scope, audience) and `system.md` (invariants). The spec must not contradict them; a
   conflict with a MUST principle is gate G3: stop and report it to the caller.
7. **Write the spec.**
   1. Extract actors, actions, data and constraints from the description.
   2. Write prioritized user stories (P1 first), each independently testable, with
      Given/When/Then acceptance scenarios. If no user flow can be determined, stop and
      tell the caller what is missing.
   3. Write testable functional requirements `FR-001...`; key entities when data is
      involved; edge cases.
   4. Write measurable, technology-agnostic success criteria `SC-001...` (time, rate,
      count, satisfaction; no frameworks, databases or APIs).
   5. For unclear aspects, make informed guesses from context and common practice and
      record each one under Assumptions. Insert `[NEEDS CLARIFICATION: specific question]`
      only when the choice changes scope, security or UX, has several reasonable readings
      and no reasonable default. **At most 3 markers**, prioritized scope > security and
      privacy > UX > technical detail.
   6. Fill the Input line with the user's description, quoted. Leave the Clarifications
      and Enhancements sections empty (keep them; enhance appends to the latter).
   7. Remove optional sections that do not apply (do not leave "N/A"); keep section order
      and headings; replace every fill-in field (`[FIELD]`, `<FIELD>`).
8. **Quality loop.** Create `specs/NNN-short-name/checklists/requirements.md` and run the loop
   in [requirements-checklist](references/requirements-checklist.md): up to 3 iterations,
   fixing the spec after each one (`light` mode: one iteration, see below).
9. **Resolve markers now.** If `[NEEDS CLARIFICATION]` markers remain, follow
   `{{SKILL:redevkit-clarify}}` in `markers` mode (only those markers, one question at a
   time). Then re-run the quality loop once. Questions asked here count toward the calling
   command's limit of 5.
10. **Set the active feature.** Update the Active feature section of
    `.redevkit/memory/active.md` with the path `specs/NNN-short-name`, the phase `specify` and
    `- Plan approved: no`, following `{{SKILL:redevkit-memanager}}`. A new active feature also
    resets the Verify pending and Correction cycle lines (rule in `{{CMD:redevkit-verify}}`
    step 6).
11. **Offer the branch** as described below.

## Branch offer (D38)

Only inside a git repository (`git rev-parse --is-inside-work-tree` succeeds); otherwise skip
it and never run `git init`. Read the branch-per-feature line (`Branch per feature` /
`Branch por feature`) in the Workflow preferences section of `.redevkit/memory/active.md`. Its value is one of three English tokens, written the same
in every project language: `always` creates `NNN-short-name` without asking, `never` skips,
`ask` (or no value yet) asks with these options: create the branch and remember `always`
(Recommended); not for this feature (save `ask`); `never` for this project.

{{ASK}}

Save the chosen token. Create the branch with `git switch -c NNN-short-name`; if it already
exists, report it and do not switch. Never commit.

## Light mode

`light` (D55, used by `{{CMD:redevkit-enhance}}`) changes these steps:

- Step 7: fill only the stories, requirements, success criteria and assumptions the change
  touches; drop the other optional sections.
- Step 8: exactly one quality iteration of `checklists/requirements.md` (check every item,
  fix the spec once, record what stays open); no loop.
- Step 9: resolve markers as usual, but do not re-run the quality iteration afterwards.
- Step 11: skip the branch offer unless the caller asks for it.

The other steps run as in `full`. No `plan.md` is written; later phases take the technical
context from `.redevkit/memory/tech.md` and `system.md`.

## Writing rules

- Focus on users and value; no tech stack, APIs or code structure in the spec.
- Every requirement must pass "testable and unambiguous".
- Reasonable defaults need no question: data retention, standard performance expectations,
  user-friendly error handling, the project's usual integration patterns.

## Report to the caller

- Feature directory and spec path; number and short name.
- Quality checklist result (`n/16` passing, open items).
- Clarifications resolved, assumptions recorded, markers left (should be 0).
- Branch: created, skipped (reason) or not a git repository.
