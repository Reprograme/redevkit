---
name: redevkit-deploy
description: Deploy only after a passing test on the current code, with rollback plan, confirmation and smoke test.
short-description: Deploy with gates, rollback plan and smoke test
argument-hint: "[staging|production|<environment>] [--check | --rollback]"
invocation: user-only
---

# redevkit-deploy

**Input:** {{ARGS}}

Arguments: the environment (asked when missing); `--check` runs the preconditions and the
pre-flight only; `--rollback` executes the rollback plan of the latest deploy report for that
environment. Write artifacts in {{LANG}}; answer the user in the user's language.

## Purpose

Put the tested code into an environment (D27) with a written deploy plan, a rollback plan,
explicit confirmation and a smoke test, leaving a report in `.redevkit/deploys/`. Only the
user starts this command (D28): it is never invoked by the model, never part of an `--auto`
chain and never triggered by another command's handoff.

## Preconditions

1. **Invoked by the user** in this turn. If you reached this file any other way, stop.
2. Memory initialized. If not, suggest `{{CMD:redevkit-new}}` and stop.
3. **Green evidence on the current code.** Reference run: the latest `PASS` run in the
   active feature's `test-report.md`; when a debug happened after it (or the latest test run
   is `FAIL`), the latest `converged+verified` run in `verification.md` after that debug.
   Recompute HEAD, working tree and both fingerprints and compare them row by row as
   `{{SKILLDIR:redevkit-test}}/references/code-state.md` describes.
   - Every row equal → precondition status `OK`.
   - No reference run, a reference that is not green, any row different, or `n/a` →
     `BLOCKED`: refuse and require a new `{{CMD:redevkit-test}}`. The only way past is
     `OVERRIDDEN`: the user states a reason, recorded in their words in the report; the run
     still stops at G6.
4. **Verify suggested.** If no verification run is newer than the test run used as evidence,
   ask: run `{{CMD:redevkit-verify}}` first (Recommended) or deploy now. Record the choice.
5. Templates resolve per T10: `.redevkit/templates/overrides/reports/deploy.md` if it exists,
   otherwise `.redevkit/templates/reports/deploy.md`.

## Memory phase 1

Recall per `{{SKILL:redevkit-memanager}}`: `MEMORY.md`, `active.md` (latest results), the
invariants in `system.md`, `tech.md` (deploy platform, environments, build command). Read
`.redevkit/memory/constitution.md`. Print `📖 Memory loaded. Last entry: YYYY-MM-DD.`

## Questions

Ask one question at a time, at most 3 options with the recommended one first and marked
"(Recommended)", at most 5 questions in this run besides the confirmations. Deploy decisions
are never assumed: in a non-interactive run, stop at the first confirmation and report what
is pending. Personas never ask: they return the question to you.

{{ASK}}

## Steps

### 1. Environment and platform

- Environment from the input; otherwise ask: staging (Recommended when one exists),
  production, or another named environment.
- Platform from `tech.md` › Deploy, else from files: `vercel.json`, `netlify.toml`,
  `fly.toml`, `railway.json`/`railway.toml`, `render.yaml`, `Procfile`, `Dockerfile`,
  `docker-compose.yml`, Kubernetes manifests, a deploy workflow in CI.

### 2. Plan the deploy and the rollback

Prepare the plan with the devops persona using `{{SKILL:deployment-procedures}}` and
`{{SKILL:server-management}}`: {{DELEGATE:devops-engineer}}. It returns, without executing:

- **Pre-flight:** build, type check, lint, no hard-coded secrets, environment variables
  documented, dependency audit. Run the read-only checks now and record the results.
- **Deploy plan:** ordered commands, version or commit, migrations, expected duration,
  health and smoke checks.
- **Rollback plan:** previous version or artifact id, the exact rollback commands, data and
  migration rollback, how to confirm the rollback worked.

`--check` ends here: show the Preconditions table, the pre-flight results and both plans in
the answer and stop. No report is written, because nothing was deployed.

### 3. Write the report draft

Write `.redevkit/deploys/YYYY-MM-DD-<environment>.md` from the template (if that file already
exists, add `-2`, `-3`, … before `.md`; never overwrite a report): Preconditions table
(reference run, HEAD, working tree, both fingerprints, `OK`/`BLOCKED`/`OVERRIDDEN`, verify
suggested, override reason), deploy plan, rollback plan. Never write secrets.

### 4. Confirm (G6)

Show the plan and the rollback plan and ask for confirmation: deploy now, or cancel.

- **Production** needs an explicit confirmation that names the environment ("deploy to
  production"); a generic "yes" is not enough. Quote it, with the time, in the report's
  Production confirmation section.
- Irreversible steps inside the plan (data migrations that drop or rewrite data) are listed
  separately and confirmed again (G4).
- Cancelled, or no confirmation possible (non-interactive run) → outcome `aborted`; stop.

### 5. Execute

Run the deploy commands in order, capturing each exit code and the relevant output. A failed
step stops the sequence: report it and offer the rollback plan; run the rollback only after
confirmation (G4).

### 6. Smoke test

After the deploy: HTTP check of the public URL (or the platform's health command) and the
critical flows from `quickstart.md` that are safe to run against that environment. A failed
smoke test → offer the rollback (confirmation required).

### 7. Finalize the report

Execution log, smoke-test table, URLs and the outcome: `succeeded`, `failed`, `rolled-back`
or `aborted`. Tokens stay in English in every language.

### Rollback mode

`--rollback`: read the latest report for the environment, show its rollback plan, confirm
(G6, and G4 for data), execute, smoke test, and write a new report for today whose outcome is
`rolled-back` (or `failed`).

## Gates that apply

| Gate | Where |
| --- | --- |
| G6 | The whole command (user-triggered only) and step 4 confirmation |
| G4 | Irreversible steps, executing a rollback, data migrations |
| G3 | The plan would violate the constitution: stop |

## Artifacts

`.redevkit/deploys/YYYY-MM-DD-<environment>.md`.

## Memory phase 3

Save per `{{SKILL:redevkit-memanager}}`: `changelog.md` (deployed version, environment,
date, verdict), `active.md` (latest deploy, next steps), `tech.md` (platform and
environments when learned), `MEMORY.md`. Never write secrets, tokens or credentials. Print
`💾 Memory updated (files).`

## Evidence rule

`succeeded` is claimed only after the deploy commands exited successfully and the smoke test
observed a healthy response; quote the status codes. The Preconditions table shows reference
and current values side by side. A skipped check is `SKIPPED (reason)`, never `PASS`.

## Handoff

- `succeeded` → `{{CMD:redevkit-status}}` to review, or `{{CMD:redevkit-plan}}` for the next
  feature.
- `failed` or `rolled-back` → `{{CMD:redevkit-debug}}` with the failing step and its output.
- `BLOCKED` → `{{CMD:redevkit-test}}` (then `{{CMD:redevkit-verify}}`).
- `aborted` → nothing changed; run `{{CMD:redevkit-deploy}}` again when ready.
- Never chained by `--auto`.
