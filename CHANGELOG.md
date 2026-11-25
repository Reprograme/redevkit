# Changelog

All notable changes to REDEVKIT are documented in this file. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.3.0] - 2026-11-25

### Fixed

- **`test_runner.py` no longer skips test suites it does not know.** It knew only Node and
  Python, so a PHP project with PHPUnit ended as `SKIPPED (no test framework detected)`,
  labelled `Type: node` when the front end's `package.json` had no test script. The runner
  is now agnostic of the suite: `--cmd "COMMAND"` runs the project's declared test command
  (`tech.md` › Test, which `redevkit-test` passes) with the same time limit, log and
  verdict, and a `{paths}` word takes the spec test files. Without `--cmd`, detection also
  covers PHP (Pest, PHPUnit, `composer test`), Go, Rust, .NET, Ruby (RSpec, `rails test`)
  and Maven, and a manifest without tests lets the next stack try.
- Counts of PHPUnit, Pest, RSpec, minitest, cargo (summed over the test binaries, so trailing
  doc tests with 0 tests no longer read as "no tests"), Maven Surefire and `dotnet test`;
  `dotnet` runs with English output (it printed the summary in the OS language); PHPUnit's
  `No tests executed!` (exit 0) is SKIPPED.
- **Test runner verdicts.** A recognized summary with failed tests is `FAIL` even when the
  command exits 0 (a wrapper that loses the exit code); a run where every test was skipped is
  `SKIPPED` (exit 3) for every parser that counts skips; unittest discovery runs the root and
  every conventional `tests/`/`test/` folder together instead of only the first one found;
  `--timeout` rejects `nan`, `inf` and overflowing values with a usage error.
- **Code state fingerprint.** A specs folder spelled `SPECs/` or `Specs/` on a
  case-insensitive volume is excluded like `specs/` (writing the test report no longer
  invalidates the run it records); files inside Git submodules count, so a change in a
  submodule changes the fingerprint.
- **Pipeline rules.** A test the debug command sends back as wrong from a global failure goes
  back to the verify and counts as a debug round, so the dispute ends in a fix, a question or
  G5; the verify never reuses a `FAIL` with the `environment` class or one followed by a debug
  handback; only a `global` verdict is reused as it stands (a `spec (full suite)` `PASS` with
  failures outside the spec is judged again); a gap of an Unverified feature covered only by
  that feature's open task is carried into the active feature as a runnable task; the app the
  verify starts stays up through the audits and is stopped afterwards; the test verdict no
  longer contradicts itself about failures outside the spec. The `orchestrator` persona
  describes the main session's role and is never delegated as a subagent.
- **CLI.** Rollback of a first `init` keeps preexisting files identical to the kit's; `init`
  with an unreadable manifest stops instead of reinstalling with default language and
  targets; `update`, `init` and `target` refuse to downgrade an installation newer than the
  CLI unless `--allow-downgrade`; an `update` with nothing to apply creates no backup;
  `uninstall` only touches `.codex/config.toml` when the kit managed entries there; an inline
  `features = { … }` table in `.codex/config.toml` receives the managed key instead of
  dropping every entry; `doctor` handles feature numbers with 4+ digits, reports a manifest
  with `files: null` as invalid (keeping its `--json` output) and requires Python 3.9+ (also
  in the audit README snippets).
- **E2E on Windows** starts `.cmd` shims (npm-installed agents) through `cmd.exe` with safe
  quoting and records spawn errors in the step instead of crashing.
- **Second audit (B01–B21).**
  - *Installation integrity:* a manifest whose `targets` is missing, empty, unknown or
    duplicated, or whose `config`/`context` fields have the wrong shape, is invalid and no
    command writes; installs prepare and validate every change before the first write;
    `uninstall` (and its `--dry-run`) stops on a malformed `AGENTS.md` block before removing
    anything; `rollback` checks every backup it uses before writing, undoes the latest
    operation by default, undoes older operations as a chain (refusing a broken chain) and
    checks that every file of the restored manifest exists; the writing commands hold
    `.redevkit/redevkit.lock` (a concurrent command waits up to 15 s, then fails without
    changes); backup ids are unique even within one millisecond, and `rollback --backup`
    takes an unambiguous id prefix (an ambiguous one is refused, listing the matches).
  - *Test runner:* unittest discovery also starts at the root when a package below it holds
    tests, and runs each start in its own process; every unittest, pytest and jest/vitest
    summary in the output counts (a later green run no longer hides an earlier failure);
    pytest is detected from real declarations only (a comment or `flake8-pytest-style` no
    longer skips a unittest suite).
  - *Code state:* files of nested git repositories count, a folder that cannot be listed
    makes the fingerprint `n/a` instead of being skipped, and the executable bit counts (a
    project without executable files keeps its fingerprint).
  - *Pipeline rules:* the verify never reuses a `FAIL` with the `test-defect` class, and the
    answer to a spec question is recorded so it is not asked again; a test `FAIL` after a
    verify invalidates that verify for the deploy; a fully green `spec (full suite)` run
    counts as the first green whole-suite run for the baseline rule; `deploy --rollback`
    uses the latest report that changed the environment (never an `aborted` one); an
    automatable scenario still without a test is a `test-defect`; the verify's fix policy and
    templates match its handoff.
  - *Audit README:* the PowerShell Python detection works in Windows PowerShell 5.1.
  - *Found by the real E2E (round r11):* every test run, the verify's included, keeps the
    template's `Tree fingerprint` row (never a prose line); the `AGENTS.md` block forbids
    piping text with accents into another program (`@'…'@ | python -` turned them into `?`);
    the harness allows the equivalent spellings of the legacy-memory move.
  - *E2E:* a step timeout is recorded as a failure, kills the process tree and bounds the
    output drain; every required step must exit 0 (a later successful retry of the same step
    recovers it; `--check` without the round's `steps.json` is INCONCLUSIVE, exit 3, never
    PASS); scenario R requires the 18 specialists and checks that `orchestrator` is
    not delegated; Ctrl+C in the runner kills the running agent's tree.

### Removed

- The Windows 1.0.0 distribution (PowerShell build, overlay, Pester-style suites, its docs)
  no longer lives in this folder; unused helpers (`readIfExists`, `copyFileInside`, `mkdirp`),
  the unused `yesNo` message and the targets' `label` export.

## [1.2.0] - 2026-11-15

The test and verify commands split into a spec scope and a global scope.

### Changed

- **`redevkit-test` tests only the active spec** (spec scope): the scenario-mapped tests
  (including the ones it generates), the test files of its tasks and the regression tests of
  its bugs; tests requested for behavior outside the spec are left to the verify. It takes no feature, file or scenario argument any more. A `PASS` hands off to
  `redevkit-verify` or to a new `redevkit-plan`, never to the deploy. A `product-defect` loops
  test → debug → test, at most 5 debug rounds before G5.
- **`redevkit-verify` runs the whole suite** (global scope) before convergence, execution and
  audits, and covers the active feature plus every feature on the new `- Unverified:` line. A
  `failed` verdict loops verify → debug → verify; G5 now fires after 3 debug rounds (was 2
  failed verifies after a debug) or 3 rounds without convergence (`gaps`, or `failed` sent to
  create). Gaps of an Unverified feature become Convergence tasks of the active feature.
- **The deploy requires a `converged+verified` verify** on the current code, with no
  Unverified feature; a test run is never its reference.
- **`redevkit-debug` hands back to the loop that sent the failure** (`- Failing scope:` in
  `active.md`); called outside a loop, it asks whether to go to the test or the verify and
  recommends one from the context.
- Before the project's first fully green whole-suite run, failing tests in files the features
  did not touch, whose failure does not point at code they changed, are classified `baseline`
  (pre-existing) and do not fail the run. In scope `spec (full suite)`, failures outside the
  spec test set are listed as Outside the spec and do not fail the test run.
- A debug that sends a failure back as a wrong test counts as a debug round, and a test that
  disagrees asks the user instead of sending it to debug again.
- `active.md` › Last results: new lines `- Failing scope:`, `- Test cycle:` and
  `- Unverified:`; `- Correction cycle:` counts debug rounds. The `- Verify pending:` line is
  removed (an old one is deleted on the next save).
- Single definition of both loops and of G5 in
  `kit/commands/redevkit-test/references/loops.md`.

### Added

- `test_runner.py --paths FILE [FILE ...]`, and `node --test` scripts without positional
  arguments take test files.
- E2E scenario F (global loop: a regression only the whole suite sees).

## [1.1.0] - 2026-11-12

### Fixed

- Pipeline stalls between create, test and verify:
  - **Code state** is now a content fingerprint (`kit/audits/code_state.py`, `Tree fingerprint`
    in the reports). The two `git status`/`git diff` fingerprints did not see edits to
    untracked files, so in a repository without commits, or for the new files of a feature,
    the verify reused a stale `FAIL` (or `PASS`) run; they also differed between shells and
    did not exist without git. Reports written by older versions are never treated as the
    same code state.
  - **Audit runners no longer hang**: every external command runs with no stdin, `CI=1`, its
    own process group and a timeout that kills the whole process tree (the old timeout only
    killed the `npm.cmd` shell on Windows); output is line-buffered; the test runner reports
    a timeout as such and has `--timeout` and `--log`.
  - **Test runner verdicts**: zero tests is `SKIPPED`, not `PASS`; tests under `tests/` are
    found; a missing runner or coverage provider no longer turns into `FAIL`; counts are
    parsed for node:test, unittest, pytest, vitest and jest.
- CLI: a CRLF checkout no longer marks every managed file as modified (hashes ignore line
  endings); `doctor` fails when a pipeline file is missing.
- Memory saves edit files in place and keep their frontmatter: a long `--auto` chain could
  rewrite `MEMORY.md` without it, which `doctor` reports as an error.

### Added

- **Failure classes** in `redevkit-test` (`environment`, `test-defect`, `not-implemented`,
  `product-defect`): the handoff of a red test follows the class instead of always going to
  the debug command; the test command corrects its own wrong tests and environment problems.
- **`- Verify pending:`** in `active.md`: set by a debug and by a verify that ends in `gaps`
  or `failed`, cleared only by `converged+verified`. While it is set, a green test hands off
  to the verify (also in `--auto`) and the deploy is `BLOCKED`. It replaces the comparison of
  dates between debug, test and verify runs.
- **Blocked tasks** (`- [!]` with a `BLOCKED` note): a task that spent its retry budget is no
  longer left as an open `[ ]` that every create run retries. `redevkit-create
  --retry-blocked` tries it again; a blocked task stops the `--auto` chain.
- **New-code gate** in `redevkit-verify`: only audit findings in files the feature created or
  changed become tasks or `failed`; findings in the rest of the project are reported as
  baseline.
- `redevkit update --restore` re-adds managed files that were deleted locally; `init --force`
  does the same.

### Changed

- `redevkit-test` has six steps (classification is step 4); the verify command runs steps
  1–6 as its step 1.
- Re-planning an approved feature sets `- Plan approved: no` until G2 approves it again.

## [1.0.3] - 2026-11-11

### Changed

- Documentation only: both READMEs list the npm commands to check the published version,
  update, run a specific version and remove the CLI (`redevkit version --check`,
  `npm install -g redevkit@latest`, `npx redevkit@<version>`, `npm uninstall -g redevkit`).
  No change to the CLI or the kit.

## [1.0.2] - 2026-11-11

### Added

- First public release on npm and GitHub. `README.md` is now in English, with the full
  Brazilian Portuguese version in `README.pt-BR.md`; `package.json` declares the repository,
  homepage and issue tracker.

- Audits share one exclusion policy (`kit/audits/audit_common.py`): common defaults
  (dependency and vendor folders, build output, generated reports such as
  `playwright-report/`, minified files), the project's `.gitignore`, and user patterns from
  `.redevkit/audit-ignore` or `--exclude PATTERN`; `--no-gitignore` turns the second off.
  `checklist.py` and `verify_all.py` forward both options.
- `checklist.py` and `verify_all.py` accept `--no-tests`; `redevkit-verify` passes it, so the
  audit step no longer runs the test suite a second time.
- The UX, accessibility, SEO and GEO audits read server-rendered `.php`/`.phtml` views.
- `redevkit-verify` triages audit findings: third-party and generated code is out of scope
  and becomes neither a task nor `failed`.

### Fixed

- `rollback` removed every managed file the rolled-back run had not touched; it now removes
  only the files that run created. The first `init` backs up a user `settings.json` or
  `config.toml` it rewrites, and `rollback` uses the installed language.
- `doctor` runs `.cmd` shims in paths with spaces and no longer crashes on a link with a
  malformed `%` escape; usage errors exit with 2; Ctrl+C at a prompt exits with 130; the
  Codex config merge no longer reports managed dotted keys as user values.
- Audit scripts: a crash in `accessibility_checker.py` on any `onClick` handler, false
  positives (`regex.exec(`, `model.eval()`, `<Header>` read as `<Head>`, labelled submit
  inputs, purple detection by substring), crashes on BOM or non-UTF-8 files and on odd CSS
  values, and wrong results for empty test runs and build folders without assets.
- Kit content: `redevkit-create` defines the "no open task" state; status and deploy compare
  with the latest feature-wide test run; wrong `tech.md` and `plan.md` section names;
  `systematic-debugging` no longer asks for the full suite inside a debug.

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
