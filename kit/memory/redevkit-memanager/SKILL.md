---
name: redevkit-memanager
description: Recall, save, sync, search and prune .redevkit/memory. Use for 'remember this', 'update memory' or memory questions.
short-description: Project memory - recall, save, sync, search
---

# REDEVKIT memory manager

**Input:** {{ARGS}}

`.redevkit/memory/` is the project memory: the single source of truth for decisions,
conventions, state and feedback about this project. Any agent that reads `AGENTS.md` can read
and write it (Claude Code, Codex, DeepSeek or another). Write memory content in the project
language `{{LANG}}`; answer the user in the user's language.

## Route the input

| Input or caller | Operation |
| --- | --- |
| Start of any command (phase 1) | **recall** |
| End of a modifying command (phase 3) | **save** (state) |
| "remember this", "lembre disso", "anote isso", "save to memory" | **save** (one fact) |
| "update memory", "atualize a memória", "UMB" | **sync** |
| "what do we know about X?", "o que sabemos sobre X?", "search memory" | **search** |
| `{{CMD:redevkit-new}}` on a project without `.redevkit/memory/` | **bootstrap**, then **import** if legacy memory exists |
| `{{CMD:redevkit-status}}`, "memory report" | **report** |
| Empty input from the user | **report**, then offer **sync** |

**prune** runs inside save and sync.

## Memory structure

| File | `type` | Sections |
| --- | --- | --- |
| `MEMORY.md` | `index` | Index, at most 256 lines: Core (fixed list, one status line per core file), User, Feedback, Project, Reference |
| `constitution.md` | `constitution` | MUST and SHOULD principles (Test-First by default), governance, semver version line, ratification, amendments. Owned by `{{SKILL:redevkit-constitution}}` |
| `project.md` | `project` | Scope · Core objective · Success criteria · Out of scope (current negative decisions) · Problem · Audience · What "working well" looks like · Expected experience · Domain |
| `system.md` | `system` | Overall architecture · Design decisions · **Invariants** (never pruned) · Patterns in use · Code conventions · Component relationships |
| `tech.md` | `tech` | Stack · Dependencies · Dev environment (build, test and dev commands, preview port) · Technical constraints |
| `active.md` | `active` | **Active feature** (`specs/NNN-name`, phase) · Where we are · Recent events · What works · What's left · Next steps · Known issues · Last results (test, verify, debug, verify pending, correction cycle) · Workflow preferences (branch per feature: `always`, `never` or `ask`) |
| `changelog.md` | `changelog` | Keep a Changelog (Unreleased + versions) · Consolidated history · Architecture decisions (short ADR) · Constitution amendments (Sync Impact Report). At most 512 lines: older entries rotate to `archive/` |
| `user.md` | `user` | Environment and tools · Communication style · Recorded feedback |
| `topics/<topic>.md` | `user`, `feedback`, `project` or `reference` | Free topics |
| `archive/<origin>-<YYYY-MM-DD>/` | none | Legacy originals, kept verbatim |
| `archive/changelog-<YYYY-MM>.md` | none | Entries rotated out of `changelog.md` (see Prune) |

Section headings come from the templates in the project language (for example `## Invariants`
in `en`, `## Invariantes` in `pt-BR`). Never rename or delete a template section.

## Frontmatter contract

Every file outside `archive/` starts with exactly these keys:

```yaml
---
type: project
created: 2026-11-06
updated: 2026-11-06
---
```

- `type`: core files use the value in the table above; topics use `user`, `feedback`,
  `project` or `reference`.
- `created`: ISO date (`YYYY-MM-DD`) of creation; never changes.
- `updated`: ISO date of the last write; set it on every write.
- The constitution also keeps its own version line in the body.

## Index format

- One entry per line: `- [type] summary → file.md`, summary at most 150 characters, target
  relative to `.redevkit/memory/` (`project.md`, `topics/payments.md`).
- **Core:** one fixed line per core file. Rewrite it in place to keep its status current;
  never add or remove Core lines.
- **User, Feedback, Project, Reference:** one line per fact or group of facts, in the section
  of its type. Entries are pointers; details live in the target file.
- At most 256 lines. Every target must exist.

## Asking the user

Ask only for confirmation-required writes, the pending-interview round and the legacy choice
(G7). Follow the shared question protocol: only what changes scope or architecture, one
question at a time, at most 3 options with the recommended one first and marked
"(Recommended)", at most 5 questions per command (shared with the calling command).

{{ASK}}

In `--auto` or non-interactive runs, confirmation-required writes are not applied: record them
as proposals in `active.md` › Next steps and list them in the report. G7 always stops the chain.

## Write policy

| Automatic (phase 3, no question) | Needs confirmation |
| --- | --- |
| `active.md`, `changelog.md`, `MEMORY.md` | Constitution creation or amendment (G1, through `{{SKILL:redevkit-constitution}}`) |
| `tech.md` and `system.md` when a pattern or dependency appears | Adding, changing or removing an **invariant** |
| `project.md` when the visible scope changes | **Any deletion** of an entry or file (G4) |
| `user.md` (preferences and feedback) | |

- Pruning only consolidates: moving content elsewhere without losing it is automatic; dropping
  content is a deletion.
- An explicit user request to save, change or remove a specific fact is the confirmation for
  that fact. For an invariant, restate the exact rule before writing it. Constitution changes
  always go through `{{SKILL:redevkit-constitution}}`, an internal phase: to the user, suggest
  `{{CMD:redevkit-new}}` (option "Amend the constitution"), never the phase itself.

Canonical lines, rendered in the user's language:

- After recall: `📖 Memory loaded. Last entry: YYYY-MM-DD.` The date is the newest event in
  `active.md` › Recent events, else its `updated` value, else `n/a`.
- After any write: `💾 Memory updated (files).` List exactly the files written, for example
  `💾 Memory updated (active.md, changelog.md, MEMORY.md).`

## Lifecycle

- **Phase 1 (recall):** at the start of every command, before any change.
- **Phase 2:** the command's own work. Keep track of what changed and why.
- **Phase 3 (save):** at the end of every command that modified something, per the write
  policy.

Exceptions:

- **Anti-recursion:** writes to `.redevkit/memory/` belong to this protocol and never start a
  new phase 1 or phase 3. The lifecycle runs once per command; a one-fact save skips the full
  phase 1.
- **Bootstrap:** creating the memory files for the first time skips phase 1.
- **Read-only commands** (`{{CMD:redevkit-status}}`, `{{CMD:redevkit-preview}} status`) run
  phase 1 only and never write.

**Inconsistency.** When memory contradicts the repository (a pending item already done, a test
command that no longer exists, a missing feature path), report it as soon as you see it, in
phase 1 or during the work, and reconcile it in phase 3. The repository wins for facts it
shows. Never silently rewrite a contradicted invariant or constitution principle: report it
(G3 for the constitution) and ask.

**Pending interview.** A field that depends on the user and has no answer gets a marker in the
project language: `<PENDING INTERVIEW — reason>` (`en`) or `<PENDENTE DE ENTREVISTA — motivo>`
(`pt-BR`). Never leave a template fill-in (`[FIELD]`) and never delete the section. The first
modifying command of each session that finds markers runs one short round before its own work:
one question at a time, each with a recommendation, starting with the markers that change
scope or architecture. These questions share the calling command's budget of 5 questions;
leave room for the command's own questions. Unanswered markers stay and are not asked again in the same
session. In `--auto`, the markers stay.

## Operations

### Bootstrap

Called by `{{CMD:redevkit-new}}` when `.redevkit/memory/` does not exist. If it already exists,
do nothing here: the new command offers amend, resync or exit.

1. Resolve each template (T10): `.redevkit/templates/overrides/<name>` if it exists, otherwise
   `.redevkit/templates/<name>`, where `<name>` is `memory/project.md`, `memory/system.md` and
   so on. The installed templates are already in `{{LANG}}`.
2. Create `.redevkit/memory/` with `project.md`, `system.md`, `tech.md`, `active.md`,
   `changelog.md` and `user.md`; set `created` and `updated` to today. Create `topics/` only
   with its first topic. Do not create `constitution.md`: `{{SKILL:redevkit-constitution}}`
   creates it (G1).
3. Fill only what is explicit in the repository or in the user's answers; every other field
   gets the pending marker. Never fill by guessing.
4. `changelog.md` baseline: the version the project already declares (package manifest, git
   tag); use `0.1.0` only when there is none.
5. `active.md` › Active feature: none yet.
6. Once the constitution exists, write `MEMORY.md` from `memory/MEMORY.md` with every Core line
   filled.
7. Emit the 💾 line.

### Recall

1. If `.redevkit/memory/MEMORY.md` does not exist, say in one line that the project has no
   memory yet and recommend `{{CMD:redevkit-new}}`. Create nothing.
2. Read `MEMORY.md`{{#claude}} (already in context through the `@.redevkit/memory/MEMORY.md` import){{/claude}},
   `active.md` and the Invariants section of `system.md`.
3. Read `constitution.md` before plan, create, enhance, debug and deploy work; `tech.md` when
   the task touches stack, setup or commands; any other file when an index entry is relevant.
4. Apply what you read silently. Recite memory only when asked.
5. Check for pending markers (interview round above) and for inconsistencies.
6. Emit the 📖 line.

### Save

**State, at phase 3.** Write only what the command changed:

- `active.md`: a new event at the top of Recent events (`- YYYY-MM-DD — what — why`), Active
  feature and phase, What works, What's left, Next steps, Known issues, and Last results:
  rewrite in place the template line the command owns (`Test` with its Run by field,
  `Verify`, `Debug`, `Verify pending`, `Correction cycle`), keeping the format of
  `memory/active.md`. Dates and times come from the system clock.
- `changelog.md`: deliveries under Unreleased. The changelog mirrors the version the project
  declares; when the project bumps its version, move the Unreleased items under the new one.
- `system.md`, `tech.md`, `project.md`, `user.md`: only when the command revealed a pattern,
  dependency, command, scope change or preference. Review `project.md` whenever visible
  capabilities change: feature lists go stale silently.
- `MEMORY.md`: refresh the Core lines whose status changed; add index lines for new facts.
- Change memory files in place with the file-editing tool; never regenerate a whole file from
  memory. Every file keeps its frontmatter, `MEMORY.md` included: after a write, its first
  line is still `---`.
- Set `updated` in every file written, run **prune** on them, emit the 💾 line.

**One fact** ("remember this"):

1. Classify it and pick the destination with [classification](references/classification.md).
2. Refuse it if it is on the never-write list, and say why.
3. Read only the destination file. If an equivalent entry exists, update it instead of adding
   a duplicate.
4. Write it, add or update its index line, set `updated`.
5. Emit the 💾 line.

If `.redevkit/memory/` does not exist, write nothing: recommend `{{CMD:redevkit-new}}` and
repeat the fact so the user can save it afterwards.

### Sync

1. Read the index and every core file (full phase 1).
2. Check them against the repository: active feature path and its task progress, commands in
   `tech.md` against the project manifests, the latest version in `changelog.md` against the
   declared version, index targets, Core status lines, pending markers.
3. Reconcile what the write policy allows automatically; ask about the rest.
4. Run **prune** on every file and the self-check in
   [doctor-contract](references/doctor-contract.md).
5. Emit the 💾 line, then list what was reconciled and what still needs the user.

### Search

1. Search `.redevkit/memory/` case-insensitively for the term and its obvious synonyms in both
   languages. Skip `archive/` unless nothing else matches or the user asks.
2. Answer with the matches as `file › section: line`, newest first, and offer to open a file.
3. Read-only: no 💾 line.

### Prune

Runs on every write (files written) and on every sync (all files).

| Condition | Action |
| --- | --- |
| File over 100 lines with 3 or more sections | Add a section index (its `##` headings) right under the title; update it with the sections; remove it when the file drops below 100 lines |
| File over 256 lines (except `MEMORY.md`, `changelog.md` and `archive/`) | Consolidate, as below |
| `MEMORY.md` near 256 lines | Merge related entries and move detail into topic files |
| `changelog.md` over 512 lines | Rotate, as below. It is never consolidated |

Consolidation per file (automatic, nothing is lost):

- `active.md`: summarize old events by theme, with dates, into `changelog.md` › Consolidated
  history; keep the recent ones.
- `system.md`, `tech.md`: patterns and dependencies that no longer bind the code move to
  `changelog.md` › Architecture decisions.
- `project.md`, `user.md`, topics: rewrite more concisely and merge duplicates.

Rotation of `changelog.md` (automatic, nothing is lost):

1. Target: `archive/changelog-YYYY-MM.md`, with the year and month of the rotation. If that
   file exists, append to it; never rewrite what it already holds. Archive files have no
   frontmatter.
2. Move whole entries, oldest first by date, until `changelog.md` has at most 512 lines:
   released versions (`## [X.Y.Z] - date` with their subsections), Consolidated history
   items, Architecture decisions and Constitution amendments. Never split an entry. Never
   move Unreleased, the most recent version or the most recent constitution amendment.
3. In the archive file, start a block `## Rotated on YYYY-MM-DD from changelog.md` and keep
   each entry under the same section heading it had.
4. Under the title of `changelog.md`, keep one line per archive file:
   `Archived: archive/changelog-YYYY-MM.md — <what moved: versions, dates>`.
5. If nothing movable is left and the file is still over 512 lines, stop and report it; the
   doctor keeps warning.

Never pruned: invariants and current negative decisions (for example "pagination dropped:
lists are small by design"). Negative decisions live in `system.md` › Design decisions
(technical) or `project.md` › Out of scope (product), never only in the changelog, which no
phase reads. Any deletion needs confirmation.

### Import

`{{CMD:redevkit-new}}` runs it after bootstrap when it finds memory from another system. The
user chooses at gate G7: import and archive (Recommended), import and keep the originals, or
do not import. Nothing is deleted. Mapping, archive path and steps:
[legacy-import](references/legacy-import.md).

### Report

Called by `{{CMD:redevkit-status}}`. Read-only, facts only:

- Last entry date (as in the 📖 line) and constitution version.
- Active feature, its phase, and whether its path exists.
- From `active.md` › Last results, as written: Test (with Run by), Verify and Debug with
  their dates, Verify pending with its reason, the Correction cycle counters, and a pending
  G5 when one is recorded.
- Pending markers, counted per file.
- Index size (lines out of 256), files over 100 or 256 lines, `changelog.md` over 512, and any
  [doctor-contract](references/doctor-contract.md) problem seen.

Write "unknown" for anything memory does not say. Never invent state.

## Never write

Secrets and credentials (tokens, passwords, keys, connection strings), ephemeral logs, code
snippets, API surface (signatures, function names), absolute local paths, anything the code
already shows, conversation transcripts. Memory holds decisions, reasons and invariants the
code cannot show: if a fact disappears when only the code is read, it belongs here.

## Native memory

- The kit never disables or edits native memory (Claude auto memory; Codex memories when the
  user turns them on). It stays a personal recall layer.
- Facts about this project (decisions, conventions, state, feedback on the project) MUST be
  written to `.redevkit/memory`, even when native memory also captured them.
- On conflict, `.redevkit/memory` wins: it is the only memory every agent can read (Claude,
  Codex, DeepSeek or another).

## Git

Everything in `.redevkit/memory/` is versioned, `user.md` included, so keep private data out
of it. Never add memory to `.gitignore`; if it is ignored, report it. Commit only when the
user asks.

## Handoff

When another command called this skill, return control to it without a handoff. When the user
invoked it, end with `## Handoff` naming the command that continues the work recorded in
`active.md` (for example `{{CMD:redevkit-create}}` for a feature being implemented,
`{{CMD:redevkit-plan}}` when no feature is active) and why.

## References

| Need | Read |
| --- | --- |
| Which type, file and section receive a fact | [classification](references/classification.md) |
| Importing memory from another system (G7) | [legacy-import](references/legacy-import.md) |
| What `redevkit doctor` checks | [doctor-contract](references/doctor-contract.md) |
