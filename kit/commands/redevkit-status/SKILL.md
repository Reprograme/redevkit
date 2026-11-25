---
name: redevkit-status
description: Show project facts only - memory, active feature, task progress, last test and verify, bugs, git.
short-description: Show project status (facts only)
argument-hint: "[feature]"
---

# redevkit-status

**Input:** {{ARGS}}

Optional: a feature (`specs/NNN-short-name`) to report instead of the active one. Answer the
user in the user's language.

## Purpose

Report where the project is, using facts read from files and read-only commands (D55, K12).
Read-only: it writes nothing, runs nothing that changes state and never invents running
agents, progress percentages or results it did not read.

## Preconditions

None. Without `.redevkit/memory/`, report "memory not initialized" and hand off to
`{{CMD:redevkit-new}}`.

## Memory phase 1

Recall per `{{SKILL:redevkit-memanager}}` and use its `report` operation for the factual
memory summary (core files, last entry date, pending markers). Print
`📖 Memory loaded. Last entry: YYYY-MM-DD.`

## Questions

None. The status never asks; when a fact cannot be read it reports `unknown (reason)`.

## Steps

Collect each fact from its source; show the source when it is not obvious.

| Fact | Source |
| --- | --- |
| Last memory entry | `updated` in the frontmatter of the memory files (latest date) |
| Active feature and phase | `.redevkit/memory/active.md` line `- Feature: specs/NNN-short-name` (or `none` / `nenhuma`); check that the path exists |
| Task progress per phase | `tasks.md`: per `## Phase N:` heading (`## Fase N:` in pt-BR artifacts), count `- [X]`/`- [x]` over all task lines; list blocked `- [!]` tasks with their `BLOCKED` note |
| Plan approval | `active.md` › Active feature › `- Plan approved:` (date, or `no`) |
| Last test | Latest dated run in `test-report.md`: date, verdict, failure classes on `FAIL`, failing count, run by, scope (`spec`, `spec (full suite)` or `global`) |
| Last verify | Latest dated run in `verification.md`: date, verdict; `invalidated` when a `test-report.md` run after the test run it used is `FAIL` (`active.md` › `- Verify:` carries the marker; rule in `{{SKILLDIR:redevkit-test}}/references/code-state.md` § Deploy reference run) |
| Last debug and loops | `active.md` › Last results › Debug, Failing scope, Test cycle and Correction cycle (counters, G5 reached), as `{{SKILLDIR:redevkit-test}}/references/loops.md` defines them |
| Unverified features | `active.md` › Last results › `- Unverified:` (they block the deploy until a verify covers them) |
| Code changed since last test and since last verify | Compare the Tree fingerprint of the latest test run and of the latest verify run with the current code per `{{SKILLDIR:redevkit-test}}/references/code-state.md` § Compare (read-only script); `unknown (reason)` when it cannot be computed |
| Open bugs | `active.md` › Known issues lines `- Bug <slug>: open` (a fact; they close at the next `converged+verified` verify); also list `.redevkit/bugs/<slug>/` folders without `test.md` as interrupted debugs |
| Pending assessments | `.redevkit/assessments/<slug>/` without `decision.md`, or with `needs-clarification` |
| Pending interview markers | Count of `<PENDING INTERVIEW` / `<PENDENTE DE ENTREVISTA` per file in `.redevkit/memory/` |
| Latest deploy | Newest file in `.redevkit/deploys/`: date, environment, verdict |
| Branch | `git branch --show-current` |
| Uncommitted changes | `git status --porcelain` (count of paths) |

Not a git repository → Branch and Uncommitted changes are `unknown (not a git repository)`.
Preview state is not checked here; `{{CMD:redevkit-preview}}` `status` does that.

Present the result as one short table, then a list of inconsistencies found (for example the
memory names a feature path that does not exist, or `active.md` says tests pass while
the latest run is `FAIL`). Do not fix them: suggest the `sync` operation of
`{{SKILL:redevkit-memanager}}`.

## Gates that apply

None. The status changes nothing.

## Artifacts

None.

## Memory phase 3

None: read-only command, nothing is saved.

## Evidence rule

Every line comes from a file that was read or a read-only command that ran. Unknown values are
shown as `unknown (reason)`. Never report agents as running or tasks as in progress unless a
file says so; never estimate percentages that were not counted.

## Handoff

Suggest one next command from the facts, with the reason. The first row that matches wins:

| Fact | Next |
| --- | --- |
| No memory | `{{CMD:redevkit-new}}` |
| G5 reached, not answered | Answer the G5 question (`{{CMD:redevkit-test}}` presents it again for the Test cycle, `{{CMD:redevkit-verify}}` for the Correction cycle) |
| No active feature, pending assessment | `{{CMD:redevkit-brainstorm}}` |
| No active feature | `{{CMD:redevkit-plan}}` |
| Plan not approved | `{{CMD:redevkit-plan}}` |
| Open `[ ]` tasks that can run (any phase, including Enhancement and Convergence) | `{{CMD:redevkit-create}}` |
| Only blocked `[!]` tasks and their dependents remain | Resolve what each blocked task needs, then `{{CMD:redevkit-create}}` `--retry-blocked`; or `{{CMD:redevkit-plan}}` |
| Latest test on the current code is `FAIL` with `test-defect` left (also after a `failed` verify) | Answer the question it names (a spec decision, or how to test a scenario still `MISSING`), then the command that runs that test again: `{{CMD:redevkit-verify}}` when the run's Scope is `global` (its step 1 never reuses a `test-defect` `FAIL`), otherwise `{{CMD:redevkit-test}}` |
| Latest verify is `failed` and the code did not change after it | The next step that run recorded (usually `{{CMD:redevkit-debug}}`) |
| Latest test on the current code is `FAIL` | By its failure class: `environment` → fix it, then `{{CMD:redevkit-test}}`; `not-implemented` → `{{CMD:redevkit-create}}`; `product-defect` → `{{CMD:redevkit-debug}}` |
| Failing scope `spec` or `global` and the code changed after that run (a debug ran) | `{{CMD:redevkit-test}}` for `spec`, `{{CMD:redevkit-verify}}` for `global` |
| No test on the current code | `{{CMD:redevkit-test}}` |
| `converged+verified` on the current code, not `invalidated`, and no Unverified feature | `{{CMD:redevkit-deploy}}` (user-triggered), or `{{CMD:redevkit-plan}}` for the next feature |
| Test `PASS` on the current code | `{{CMD:redevkit-verify}}` (the only way to the deploy), or `{{CMD:redevkit-plan}}` for the next feature |
