# Memory doctor contract

What `redevkit doctor` checks in `.redevkit/memory/`, so the agent keeps memory valid. Part of
[redevkit-memanager](../SKILL.md). Run these checks yourself during **sync** and fix what fails
in phase 3, following the write policy (deletions need confirmation).

## Checks

| Check | Rule | Fix |
| --- | --- | --- |
| Core files | `MEMORY.md`, `constitution.md`, `project.md`, `system.md`, `tech.md`, `active.md`, `changelog.md` and `user.md` exist | Recreate the missing file from its template with pending markers; a missing constitution goes through `{{SKILL:redevkit-constitution}}` (G1) |
| Frontmatter | Every `.md` under `.redevkit/memory/` except `archive/` starts with `---`, has `type`, `created` and `updated`, and closes with `---` | Add the missing keys. Unknown `created`: the earliest date known (git history), else today |
| Dates | `created` and `updated` are valid `YYYY-MM-DD` dates and `updated` is not before `created` | Correct the dates |
| Type values | Core files: `MEMORY.md` → `index`, `constitution.md` → `constitution`, `project.md` → `project`, `system.md` → `system`, `tech.md` → `tech`, `active.md` → `active`, `changelog.md` → `changelog`, `user.md` → `user`. `topics/*.md`: `user`, `feedback`, `project` or `reference` | Set the right value |
| Index size | `MEMORY.md` has at most 200 lines | Merge entries, move detail into topics (**prune**) |
| Index links | Every entry target (`→ file.md`) exists, relative to `.redevkit/memory/` | Correct the path; if the target is gone, ask before removing the line |
| Invariants | `system.md` has the heading `## Invariants` when `lang` in `.redevkit/manifest.json` is `en`, or `## Invariantes` when it is `pt-BR` | Restore the heading; an empty section is valid |
| Active feature | When `active.md` › Active feature names `specs/NNN-name`, that directory exists | Point to the real feature, or set none, and report it |
| Secrets | No basic secret pattern in any file, `archive/` included | Report at once, propose the redaction (a deletion, so ask) and recommend rotating the secret: git history keeps it |

Basic secret patterns, at least: private key blocks (`-----BEGIN ... PRIVATE KEY-----`), cloud
access key IDs (`AKIA` + 16 characters), provider tokens (`ghp_`, `github_pat_`, `sk-`,
`xoxb-`), long JWT-like strings (`eyJ...`), credentials in URLs (`://user:password@host`), and
assignments such as `password=`, `secret:`, `api_key=` or `token=` followed by a value.

## Formats the doctor parses

- Index entry: `- [type] summary → target.md`, where `type` is `user`, `feedback`, `project`
  or `reference` and the target is the last token after `→`.
- Active feature, in `active.md` › Active feature: a line `- Feature: specs/NNN-name`. No
  active feature: `- Feature: none` (`en`) or `- Feature: nenhuma` (`pt-BR`). The doctor takes
  the first `specs/NNN-...` path in that section.
- Frontmatter: one `key: value` per line; dates may be quoted.

## Not checked by the doctor

This skill enforces these, and `{{CMD:redevkit-status}}` reports some of them:

- Pending interview markers (counted by **report**).
- File size thresholds (100 and 256 lines) and section indexes.
- Index summaries over 150 characters.
- Never-write items other than secrets (logs, code, absolute paths, transcripts).
- Section names other than the Invariants heading.
