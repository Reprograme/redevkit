# Changelog

All notable changes to REDEVKIT are documented in this file. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.1] - 2026-11-09

### Added

- Memory size limits: `MEMORY.md` at most 256 lines (doctor error, was 200); other memory
  files consolidated above 256 lines (doctor warning); `changelog.md` at most 512 lines, its
  oldest entries rotated to `archive/changelog-YYYY-MM.md` (doctor warning above 512).
- Test reports record **Run by** (`redevkit-test` or `redevkit-verify (step 1)`) and **Scope**;
  verification reports record the test evidence used; `active.md` gains `- Plan approved:`,
  `- Debug:`, `- Correction cycle:` and `- Bug <slug>:` lines, in English in every language.
- `tech.md` records the Project Type, used by the verify for lightweight specs.

### Changed

- `redevkit-verify` starts with a test run on the current code: it reuses the latest
  feature-wide `test-report.md` run when the code state is the same (a `FAIL` gives `failed`),
  otherwise it runs the test procedure and appends the run; the suite no longer runs twice.
- Gate G5 is a correction cycle per feature (defined in `redevkit-verify` step 6): 2 failed
  verifies after a debug or 3 verifies without `converged+verified` stop the chain, also in
  `--auto`, with defined answers (revise the plan, continue, stop).
- The deploy reference has a single definition (`redevkit-test/references/code-state.md`):
  a pending debug blocks until the verify runs; otherwise the latest feature-wide test run
  must be `PASS` on the current code.
- Domain checklists are informational (one warning in implement, "Not verified" in verify).
- Audit orchestrators exit 3 (`SKIPPED`) when nothing was checked; Drizzle-only schemas are
  `SKIPPED` instead of `PASS`.

### Fixed

- `redevkit init --force` backs up every file it overwrites, also on a first install.
- Kit-wide review: an unbounded re-assessment loop inside debug; status sending implemented
  features back to plan; lightweight specs blocked in create and verify; the `redevkit-new`
  resync clearing the active feature; undefined "open bug"; skills that fixed bugs without a
  regression test or restarted production without confirmation; PowerShell writes without
  UTF-8; `git hash-object --stdin` missing from the Claude Code allowlist.

## [1.0.0] - 2026-11-06

First release. REDEVKIT merges the spec-driven process of Spec Kit with the personas,
quality rules, design gate, execution-based verification and memory of AG Kit, for Claude
Code and OpenAI Codex.

### Added

- 11 pipeline commands, rendered as skills for both targets: `redevkit-new`,
  `redevkit-brainstorm`, `redevkit-plan`, `redevkit-create`, `redevkit-enhance`,
  `redevkit-test`, `redevkit-debug`, `redevkit-verify`, `redevkit-preview`,
  `redevkit-deploy`, `redevkit-status`. Every command ends with a handoff.
- `--auto` chain new → plan → create/enhance → test (debug → verify on red) that always
  stops at gates G1–G7; deploy is user-triggered only.
- 18 internal phase skills (constitution, specify, clarify, tasks, analyze, checklist,
  implement, converge, orchestrate, route, bug and assess phases), hidden from the Claude
  Code menu and marked `[internal]` in Codex.
- 19 personas as native subagents (`.claude/agents/*.md`, `.codex/agents/*.toml`) with
  domain routing; `product-manager` merged into `product-owner`.
- 39 knowledge skills normalized from AG Kit, with former sub-skills as references.
- Project memory in `.redevkit/memory/` with the `redevkit-memanager` skill (bootstrap, recall,
  save, sync, search, prune, import, report), readable by any agent through `AGENTS.md`, and
  import of legacy memory from `memory-bank/`, AG Kit and Spec Kit.
- Constitution inside the memory with Test-First by default (`**TDD**: required`), semver
  amendments and a Sync Impact Report in `changelog.md`.
- Artifact templates in `pt-BR` and `en` (spec, plan, tasks, constitution, checklist,
  design, memory, assess and reports), with `overrides/` taking precedence.
- `DESIGN.md` gate for UI features, with the Purple Ban on by default.
- Execution-based verification: code state (HEAD, tree, fingerprints) recorded in test and
  verify reports and checked by the deploy.
- 20 optional Python audit scripts (17 audits and 3 orchestrators) in `.redevkit/audits/`;
  without Python they are reported as `SKIPPED`.
- `redevkit` CLI (Node.js ≥ 20): `init`, `update` (three-way merge with backup), `rollback`,
  `status`, `doctor`, `target add|remove`, `version`, `uninstall`.
- `AGENTS.md` managed block and `CLAUDE.md` pointer, with migration of an existing
  `CLAUDE.md` into `AGENTS.md` (diff, confirmation, backup).
- Managed runtime entries: `permissions.allow` in `.claude/settings.json` (read-only git,
  test runners, audits) and two keys in `.codex/config.toml`.
- Documentation in Brazilian Portuguese: README, method, command reference, migration guide
  and MCP setup.

### Security

- No hooks and no deny-list: safety relies on the runtime's permissions and sandbox, the
  rules in `AGENTS.md`, the pipeline gates and user-only deploy.
