# Changelog

All notable changes to REDEVKIT are documented in this file. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-11-08

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
- `redevkit-verify` starts with a test run on the current code: it reuses the latest
  `test-report.md` run when the code state is the same, otherwise it runs the test procedure
  and appends the run. A correction cycle in `active.md` (defined in `redevkit-verify` step 6)
  stops the debug → verify and gaps → create → verify loops at gate G5.
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
