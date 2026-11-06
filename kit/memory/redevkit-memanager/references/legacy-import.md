# Importing legacy memory

How **import** brings memory from another system into `.redevkit/memory/`. Part of
[redevkit-memanager](../SKILL.md). `{{CMD:redevkit-new}}` detects the legacy memory and runs
this after **bootstrap** has created the core files. This is the only reference that names
legacy memory paths.

## Sources detected

| Origin | Path | `<origin>` label |
| --- | --- | --- |
| Memory Bank | `memory-bank/` (`projectBrief.md`, `productContext.md`, `systemPatterns.md`, `techContext.md`, `activeContext.md`, `progress.md`, `changeLog.md`) | `memory-bank` |
| AG Kit | `.agents/memory/` (`MEMORY.md` plus topic files) | `agents-memory` |
| Spec Kit | `.specify/memory/constitution.md` | `specify-memory` |

## Gate G7: the choice

Show the user the mapping below for the sources found, with how many files each holds, then
ask one question with three options, the recommended one first:

1. **Import and archive (Recommended):** import, then move the originals to
   `.redevkit/memory/archive/<origin>-<YYYY-MM-DD>/`.
2. **Import and keep the originals:** import and leave the originals where they are, no
   longer maintained.
3. **Do not import:** touch nothing.

G7 is a gate: the chain stops here even with `--auto`. Nothing is ever deleted: archiving
moves files with their content intact.

## Mapping

| Origin | Destination |
| --- | --- |
| `memory-bank/projectBrief.md` + `productContext.md` | `project.md` |
| `memory-bank/systemPatterns.md` | `system.md`; its user preferences and feedback go to `user.md` |
| `memory-bank/techContext.md` | `tech.md` |
| `memory-bank/activeContext.md` + `progress.md` | `active.md` |
| `memory-bank/changeLog.md` | `changelog.md` |
| `.agents/memory/MEMORY.md` + topic files (AG Kit) | `MEMORY.md` (merge) + `topics/` or the matching core file |
| `.specify/memory/constitution.md` (Spec Kit) | `constitution.md`, keeping its version. If one already exists, ask which prevails |

Section-level detail (source headings may be in another language; match them by meaning):

| Source section | Destination section |
| --- | --- |
| Memory Bank: Scope, Core objective, Success criteria, Out of scope | `project.md` › same sections |
| Memory Bank: Problem, Users / audience, What "working well" looks like, Expected experience | `project.md` › Problem, Audience, What "working well" looks like, Expected experience |
| Memory Bank: Overall architecture, Design decisions, Invariants, Patterns in use, Code conventions, Component relationships | `system.md` › same sections |
| Memory Bank: User preferences and feedback (environment, communication style, recorded feedback) | `user.md` › Environment and tools, Communication style, Recorded feedback |
| Memory Bank: Stack, Dependencies, Dev environment, Technical constraints | `tech.md` › same sections |
| Memory Bank: Where we are, Recent events | `active.md` › Where we are, Recent events |
| Memory Bank: What works, What's left, Next steps, Known issues, Current status | `active.md` › What works, What's left, Next steps, Known issues, Where we are |
| Memory Bank: versions, Unreleased (`[Não versionado]`), Consolidated history, Architecture decisions | `changelog.md` › same sections |
| AG Kit `user-preferences.md` | `user.md` |
| AG Kit `feedback-history.md` | `user.md` › Recorded feedback |
| AG Kit `project-conventions.md` | `system.md` › Code conventions (workflow habits such as branches go to `active.md` › Workflow preferences) |
| AG Kit `tech-decisions.md` | `system.md` › Design decisions; long reasoning to `changelog.md` › Architecture decisions |
| AG Kit other topic files | `topics/<topic>.md`, keeping their `type` |
| AG Kit `MEMORY.md` entries | Merged into the index section of their type, targets rewritten to the new files |

## Steps

1. Read every source file in full before writing anything.
2. For each mapping row, merge the source into the destination section. Keep facts, dates and
   reasons; drop template leftovers. Rewrite into the project language `{{LANG}}` when the
   source uses another one, keeping quoted user feedback as written.
3. Apply the never-write list while importing: skip secrets, ephemeral logs, code snippets,
   API surface, absolute local paths and anything the code shows. Count what was skipped and
   why; never echo a secret.
4. Skip entries about the previous tool itself rather than about the project (its supported
   runtimes, its own install steps) and list them in the report.
5. Invariants carried over verbatim are covered by the G7 choice; list them in the report.
   Rewording an invariant still needs confirmation.
6. Keep pending markers from the source (`<PENDENTE DE ENTREVISTA — motivo>` or
   `<PENDING INTERVIEW — reason>`), rewritten in the project language.
7. Constitution: hand the Spec Kit constitution to `{{SKILL:redevkit-constitution}}` as the
   starting point, keeping its version line and amendment history. If `constitution.md`
   already exists, ask which prevails: keep the current one (Recommended), take the legacy
   one, or merge them. Either way, the constitution phase confirms the result (G1).
8. Apply the chosen option:
   - **Import and archive:** move each source directory's memory files to
     `.redevkit/memory/archive/<origin>-<YYYY-MM-DD>/`, keeping their relative paths. Move
     only the memory files: the rest of `.specify/` or `.agents/` stays untouched. If the
     archive folder already exists, add a suffix (`-2`). Do not stage or commit.
   - **Import and keep the originals:** leave every source file untouched. Record in
     `changelog.md` that the originals were kept and are no longer maintained; on conflict,
     `.redevkit/memory` wins.
   - **Do not import:** touch nothing. Record the choice in `active.md` › Workflow preferences
     (`- Legacy memory at <path> not imported (YYYY-MM-DD)`) so later runs do not ask again
     unless the user brings it up.
9. Set `updated` on every file written, refresh the Core lines of `MEMORY.md`, and add a
   `changelog.md` › Unreleased entry describing the import.
10. Report: sources, option chosen, files written, entries imported, items skipped with
    reasons, archive path. Emit the 💾 line.
