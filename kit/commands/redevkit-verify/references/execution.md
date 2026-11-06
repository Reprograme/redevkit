# Verification by execution and audits

Steps 2 and 3 of redevkit-verify. Principle: code that exists is not code that works. Verify
by running it; never by inspection or assumption.

## Execution (step 2)

### 1. Identify what changed

Files and behavior changed since the last verification run (`git diff`, `git log` since the
previous run, `tasks.md` items marked `[X]` since then, the bug folder after a debug).

### 2. Choose the method per change

| Change type | Method |
| --- | --- |
| Bug fix | Reproduce the original scenario from `assessment.md` and confirm it no longer occurs |
| New feature | Run the `quickstart.md` scenarios and confirm the expected outcomes |
| Refactor | Run the existing tests and confirm nothing broke |
| API change | Call the endpoint and confirm status code and response shape, including error cases |
| UI change | Render the page in a browser (Playwright via `webapp-testing`) and check the console |
| Config change | Load the configuration and confirm the values applied |
| Build or infra | Run the build command and confirm success |

### 3. Execute

1. Build (or type check) with the command from `tech.md`.
2. Full test suite, same command as the test command uses.
3. When the Project Type has a runtime (`web`, `fullstack`, `api`, `mobile` web preview,
   `game` for the web): start the application in the background as the preview command's
   start procedure describes, wait for the HTTP health check, walk the critical flows of
   `quickstart.md` (happy path and at least one error path), then stop it.
4. Anything that cannot be automated goes to **Not verified**, with the reason.

### Checklist by Project Type

- **Web / fullstack:** build, lint, tests, dev server starts, changed pages render, no
  console errors.
- **API:** server starts, changed endpoints answer correctly, error cases return the right
  status codes, database queries run.
- **CLI / library:** the command runs, expected output matches, bad input is handled, help
  text is right; for libraries, the public API is exercised by tests.

## Audits (step 3)

1. Detect a Python interpreter as `.redevkit/audits/README.md` describes (`python`, then
   `py -3` on Windows, then `python3`, each validated by running `--version`).
2. Choose by Project Type:

   | Project Type | Audit | Runtime flag |
   | --- | --- | --- |
   | `web`, `fullstack`, `mobile`, `game` with the app running | `verify_all.py` with the app URL | none |
   | `web`, `fullstack`, `mobile`, `game` without a running app | `checklist.py` | `--no-runtime` |
   | `api` | `checklist.py` | `--no-runtime` unless the server is running |
   | `cli`, `library`, `desktop`, `other` | `checklist.py` | `--no-runtime` |

   Arguments other than `--no-runtime` follow the README.
3. No Python: every audit is `SKIPPED (no Python interpreter)`. Fall back to the project's
   own lint, type check and dependency audit commands from `tech.md`, and report them as
   such.
4. Report each audit as `PASS`, `FAIL` or `SKIPPED (reason)`. A tool that is missing is
   `SKIPPED`, never `PASS` and never `FAIL`.

Priority when reading failures: Security → Lint → Schema → Tests → UX → SEO →
Lighthouse/E2E.

## Fix policy

The verify command does not edit application code. Failures become either:

- **gaps** — non-critical audit findings and missing behavior: appended as tasks in
  `## Phase N: Convergence`, same grammar as the other tasks; or
- **failed** — build failure, failing test, application that does not start, broken critical
  flow, or a Security or Lint failure of error severity: handed to the debug command.

## Verdict

| Verdict | When |
| --- | --- |
| `converged+verified` | No convergence gaps, every executed step passed, no audit `FAIL` |
| `gaps` | Execution passed, but convergence or non-critical audits appended tasks |
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
