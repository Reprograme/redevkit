# Verification by execution and audits

Steps 3 and 4 of redevkit-verify. The test suite is not part of this reference: step 1 of
redevkit-verify runs the whole suite through the test procedure in the global scope (or
reuses a run on the same code, under the rules of its step 1). The **features in scope** are the active feature and every
feature on the `- Unverified:` line of `active.md`. Principle: code that exists is not code that works. Verify
by running it; never by inspection or assumption.

## Execution (step 3)

### 1. Identify what changed

Files and behavior changed since the last verification run (`git diff`, `git log` since the
previous run, `tasks.md` items of the features in scope marked `[X]` since then, the bug
folders after a debug).

### 2. Choose the method per change

| Change type | Method |
| --- | --- |
| Bug fix | Reproduce the original scenario from `assessment.md` and confirm it no longer occurs |
| New feature | Run the `quickstart.md` scenarios of each feature in scope and confirm the expected outcomes |
| Refactor | Covered by the step 1 test run; walk the affected flows and confirm nothing broke |
| API change | Call the endpoint and confirm status code and response shape, including error cases |
| UI change | Render the page in a browser (Playwright via `webapp-testing`) and check the console |
| Config change | Load the configuration and confirm the values applied |
| Build or infra | Run the build command and confirm success |

### 3. Execute

1. Build (or type check) with the command from `tech.md`.
2. When the Project Type has a runtime (`web`, `fullstack`, `api`, `mobile` web preview,
   `game` for the web): start the application in the background as the preview command's
   start procedure describes, wait for the HTTP health check, walk the critical flows of
   `quickstart.md` of each feature in scope (happy path and at least one error path), and
   keep it running until the audits of step 4 end: they take its URL.
3. Anything that cannot be automated goes to **Not verified**, with the reason.

### Checklist by Project Type

- **Web / fullstack:** build, lint, dev server starts, changed pages render, no
  console errors.
- **API:** server starts, changed endpoints answer correctly, error cases return the right
  status codes, database queries run.
- **CLI / library:** the command runs, expected output matches, bad input is handled, help
  text is right; for libraries, the public API is exercised by tests.

## Audits (step 4)

1. Detect a Python interpreter as `.redevkit/audits/README.md` describes (`python`, then
   `py -3` on Windows, then `python3`, each validated by running `--version`).
2. Choose by Project Type (from `plan.md`, or `tech.md` for a lightweight spec):

   | Project Type | Audit | Runtime flag |
   | --- | --- | --- |
   | `web`, `fullstack`, `mobile`, `game` with the app running (the one step 3 started) | `verify_all.py` with the app URL | none |
   | `web`, `fullstack`, `mobile`, `game` whose app did not start in step 3 | `checklist.py` | `--no-runtime` |
   | `api` | `checklist.py` | `--url` of the server step 3 started; `--no-runtime` when it did not start |
   | `cli`, `library`, `desktop`, `other` | `checklist.py` | `--no-runtime` |

   Always add `--no-tests`: step 1 already ran or reused the test suite, so the orchestrator
   reports its Test Runner check as `SKIPPED` instead of running the suite again. Other
   arguments follow the README. An orchestrator run can take minutes: give the call a timeout
   above that, or run it in the background and wait for it.
3. One orchestrator run is the audit suite. `checklist.py` runs security, lint, types,
   schema, UX, accessibility, SEO and (with `--url`) the runtime checks;
   `verify_all.py` adds dependencies, GEO, bundle, React, mobile, i18n and API. Never run an
   audit again on its own when the orchestrator already ran it. Run a single audit (the
   knowledge skills give its command) only when the chosen orchestrator does not include it
   and the feature touches its domain, or to re-check one finding.
4. No Python: every audit is `SKIPPED (no Python interpreter)`. Fall back to the project's
   own lint, type check and dependency audit commands from `tech.md`, and report them as
   such.
5. Report each audit as `PASS`, `FAIL` or `SKIPPED (reason)`. A tool that is missing is
   `SKIPPED`, never `PASS` and never `FAIL`.
6. Triage every finding by its file before the fix policy below. The verification judges
   the code the features in scope wrote, not the debt the project already had:

   | Bucket | Files | Effect |
   | --- | --- | --- |
   | In scope | Files the features in scope created or changed: the paths of their `tasks.md` tasks, the files changed by their bug fixes (`fix.md` of their bugs), the tests listed as generated or corrected in their `test-report.md` and, in a git repository, the files `git status` and `git diff` show as changed | The fix policy below applies |
   | Baseline | Any other file the project owns | Never a task, never `failed`. Notes: `baseline (pre-existing): N findings in M files` |
   | Out of scope | Code the project does not own: installed dependencies, vendored or third-party libraries, framework core files kept in the repository, generated, minified or build output, and files the project's `.gitignore` ignores | Never a task, never `failed`. Notes: `out of scope (third-party/generated): <paths>` |

   Keep the audit's real result (`PASS`, `FAIL`) in the table. An audit whose findings are
   all baseline or out of scope does not count as an audit `FAIL` for the verdict. A baseline
   finding of high or critical severity from the Security Scan is also listed under **Not
   verified** as a pre-existing risk, with the suggestion to treat it in its own feature
   (`redevkit-enhance`); it still does not block this verification. An in-scope finding that an open
   `[ ]` or blocked `[!]` Convergence task already covers is cited with that task ID, not
   appended again. The audits already skip
   dependency folders, build output, generated reports, minified files and what `.gitignore`
   ignores; for any other out-of-scope path (prototypes, framework stock pages), suggest
   that the user add a gitignore-style pattern to `.redevkit/audit-ignore` (one per line),
   which every audit reads, or pass `--exclude PATTERN` for a single run. Never create or
   edit that file without the user's approval.
7. When the orchestrator run ends (pass, fail, timeout or error), stop the application step 3
   started, as the preview command's stop procedure describes, and confirm its port is free.
   The same applies whenever the verification leaves steps 3–4 early (a failure, a gate, an
   interruption): an application the verify started never outlives the run. Record the stop
   in the execution evidence.

Priority when reading failures: Security → Lint → Schema → Tests → UX → SEO →
Lighthouse/E2E.

## Fix policy

The verify command does not edit application code. Failures (for audits, in-scope findings
only: Audits step 6; baseline and out-of-scope findings never count) become either:

- **gaps** — non-critical audit findings and missing behavior: appended as tasks to this
  run's `## Phase N: Convergence` in the active feature's `tasks.md` (the one step 2
  appended, otherwise a new one; a finding in an Unverified feature's file cites that
  feature), same grammar as the other tasks; or
- **failed** — a `FAIL` test run (step 1), build failure, application that does not start,
  broken critical flow, or a Security or Lint failure of error severity. The handoff follows
  the cause, as the verify command's Handoff lists it (the first that applies wins): a test
  run that failed by `environment` → no command, fixed outside the code, then the verify
  again; by `test-defect` → no command, the question for the user is pending, then the verify
  again (its test procedure corrects the test or follows the answer); by `not-implemented` →
  the create command; everything else (a `product-defect`, build, start, flow or blocking
  audit) → the debug command, which hands back to the verify (global loop, G5 after 3 debug
  rounds).
  Test failures classified `baseline` (pre-existing, before the project's first fully green
  whole-suite run) never count as failed.

## Verdict

| Verdict | When |
| --- | --- |
| `converged+verified` | Test run `PASS`, no convergence gaps, every executed step passed, no audit `FAIL` with in-scope findings (baseline and out-of-scope findings do not count) |
| `gaps` | Test run `PASS` and execution passed, but convergence or non-critical audits appended tasks |
| `failed` | Any condition listed under **failed** above |

`SKIPPED` items never upgrade a verdict; they are listed so the user sees what was not
checked.

## Anti-patterns

| Anti-pattern | Instead |
| --- | --- |
| "It should work" | Run it and show the output |
| Only the happy path | Run at least one error path per critical flow |
| Compiling counts as working | Exercise runtime behavior |
| Skipping "trivial" changes | Verify everything that changed |
