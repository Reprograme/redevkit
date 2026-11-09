---
name: redevkit-constitution
description: Create or amend the project constitution (Test-First default, semver, G1).
---

# redevkit-constitution

Internal phase. Writes the project's laws to `.redevkit/memory/constitution.md` and records
every change in `.redevkit/memory/changelog.md`. Called by `{{CMD:redevkit-new}}` (create,
or amend when the memory already exists).

Write the constitution in the project language ({{LANG}}). Answer the user in their
language.

## Input (from the calling command)

- Mode: `create` or `amend`.
- Project facts: `.redevkit/memory/project.md` (scope, audience, out of scope) and, for an
  existing project, `tech.md` and `system.md`.
- Domain constraints proposed by the caller from the domain skills it loaded through
  `{{SKILL:redevkit-route}}`, for example an engine choice or a 60 FPS target from
  `game-development`, an accessibility target from `frontend-design`. Each comes as a
  candidate principle or technical constraint with its rationale.
- Principles or amendments the user asked for.

## Scope guard

This phase changes only `.redevkit/memory/constitution.md` and appends to
`.redevkit/memory/changelog.md`. It never edits templates, specs or code. When the input also
asks for feature work, do not do it: return it to the caller as a deferred intent.

## Steps

### 1. Resolve the template

Use `.redevkit/templates/overrides/constitution.md` if it exists, otherwise
`.redevkit/templates/constitution.md`. Never write back to a template.

### 2. Load the current constitution

In `amend` mode (or if the file exists), read
`.redevkit/memory/constitution.md`: keep every value and amendment that still applies,
including its `created` date and ratification date.

### 3. Collect principles

- **Test-First is a default MUST principle (D37)** with the line `**TDD**: required`.
  Remove it, or switch it to `**TDD**: waived`, only through an explicit amendment the
  user asked for, with the reason recorded.
- Add the domain principles and technical constraints the caller proposed, phrased as
  declarative MUST or SHOULD rules with a rationale. Never invent constraints the facts do
  not support.
- Respect the number of principles the user asks for; the template's slots are a guide.
- For a project with UI, keep the template's design rule: `DESIGN.md` is the visual source
  of truth and the Purple Ban is on by default unless the brand says otherwise.
- If a value is unknown (for example the ratification date of an imported constitution),
  write `TODO(<FIELD>): <why>` and list it as deferred.

### 4. Version (semver)

- `create`: `1.0.0`, ratified today.
- MAJOR: a principle removed or redefined incompatibly (waiving TDD is MAJOR).
- MINOR: a principle or section added, or guidance materially expanded.
- PATCH: wording, clarification, typo.
- If the bump type is unclear, state your reasoning in the confirmation.

### 5. Draft

Write the full document from the template: replace every fill-in field; keep the heading
levels; principles are short, testable and use MUST or SHOULD; the Governance section keeps
the amendment procedure, versioning policy and compliance review. Update the frontmatter
(`type: constitution`, `created` = first ratification, `updated` = today) and the version
line in the body.

### 6. Validate

Check: no unexplained fill-in field; the version line matches the bump; dates are ISO
`YYYY-MM-DD`; Test-First present (or its recorded waiver).

### 7. Confirm (gate G1)

Show the version, the bump rationale, the list of principles (or, for an amendment, what
changes) and the deferred TODOs. Ask: approve (Recommended), edit (the user says what to
change, then repeat this step), or cancel. This gate always stops, even with `--auto`.

{{ASK}}

### 8. Write

Overwrite `.redevkit/memory/constitution.md` only after approval.

### 9. Sync Impact Report (T8)

This section is the only definition of the report format; templates point here. Add it to
`.redevkit/memory/changelog.md` at the top of the Constitution amendments section (newest
first; `## Constitution amendments` or `## Emendas da constituição`, whichever the file uses;
create it if missing), with the labels in {{LANG}}. It is a permanent record, never an HTML
comment in the constitution:

```markdown
### v1.1.0 - 2026-11-12 (MINOR)

- Version: 1.0.0 → 1.1.0
- Rationale: <why>
- Principles: added <name>; changed <old → new>; removed <name>
- Sections: added <name>; removed <name>
- Templates to review: `.redevkit/templates/plan.md` (Constitution Check) - pending;
  `.redevkit/templates/tasks.md` (TDD sections) - no change
- Active artifacts to review: `specs/003-checkout/plan.md` (Constitution Check)
- Deferred: TODO(<FIELD>) ...
```

For templates, check `spec.md`, `plan.md`, `tasks.md` and `checklist.md` in
`.redevkit/templates/` and in `overrides/`. List which ones depend on a changed principle;
do not edit them. For `create`, write the entry as `(ratified)` with the initial principle
list.

## Report to the caller

- New version, bump rationale, path written.
- Principles (MUST and SHOULD), with the ones derived from the domain marked.
- Templates and artifacts flagged in the Sync Impact Report.
- Deferred TODOs, and the deferred non-governance intents as next actions.
- The index line for `.redevkit/memory/MEMORY.md` (the command's memory save writes it), for
  example `- [project] Constitution v1.0.0 - Test-First required → constitution.md`.
