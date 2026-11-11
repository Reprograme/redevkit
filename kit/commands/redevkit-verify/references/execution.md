# Verification by execution and audits

Steps 3 and 4 of redevkit-verify. The test suite is not part of this reference: step 1 of
redevkit-verify runs it through the test procedure (or reuses a run on the same code). Principle: code that exists is not code that works. Verify
by running it; never by inspection or assumption.

## Execution (step 3)

### 1. Identify what changed

Files and behavior changed since the last verification run (`git diff`, `git log` since the
previous run, `tasks.md` items marked `[X]` since then, the bug folder after a debug).

### 2. Choose the method per change

| Change type | Method |
| --- | --- |
| Bug fix | Reproduce the original scenario from `assessment.md` and confirm it no longer occurs |
| New feature | Run the `quickstart.md` scenarios and confirm the expected outcomes |
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
   `quickstart.md` (happy path and at least one error path), then stop it.
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
   | `web`, `fullstack`, `mobile`, `game` with the app running | `verify_all.py` with the app URL | none |
   | `web`, `fullstack`, `mobile`, `game` without a running app | `checklist.py` | `--no-runtime` |
   | `api` | `checklist.py` | `--no-runtime` unless the server is running |
   | `cli`, `library`, `desktop`, `other` | `checklist.py` | `--no-runtime` |

   Always add `--no-tests`: step 1 already ran or reused the test suite, so the orchestrator
   reports its Test Runner check as `SKIPPED` instead of running the suite again. Other
   arguments follow the README.
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
6. Triage every finding by its file before the fix policy below. Code the project does not
   own is out of scope: installed dependencies, vendored or third-party libraries, framework
   core files kept in the repository, generated, minified or build output, and files the
   project's `.gitignore` ignores. Out-of-scope findings become neither tasks nor `failed`:
   keep the audit's real result in the table and list them in its Notes as
   `out of scope (third-party/generated): <paths>`. An audit whose findings are all out of
   scope does not count as an audit `FAIL` for the verdict. The audits already skip
   dependency folders, build output, generated reports, minified files and what `.gitignore`
   ignores; for any other out-of-scope path (prototypes, framework stock pages), suggest
   that the user add a gitignore-style pattern to `.redevkit/audit-ignore` (one per line),
   which every audit reads, or pass `--exclude PATTERN` for a single run. Never create or
   edit that file without the user's approval.

Priority when reading failures: Security → Lint → Schema → Tests → UX → SEO →
Lighthouse/E2E.

## Fix policy

The verify command does not edit application code. Failures (for audits, in-scope findings
only: Audits step 6) become either:

- **gaps** — non-critical audit findings and missing behavior: appended as tasks to this
  run's `## Phase N: Convergence` (the one step 2 appended, otherwise a new one), same
  grammar as the other tasks; or
- **failed** — a `FAIL` test run (step 1), build failure, application that does not start,
  broken critical flow, or a Security or Lint failure of error severity: handed to the debug
  command.

## Verdict

| Verdict | When |
| --- | --- |
| `converged+verified` | Test run `PASS`, no convergence gaps, every executed step passed, no audit `FAIL` with in-scope findings |
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
