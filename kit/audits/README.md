# REDEVKIT audits

Optional, dependency-free Python audits installed in `.redevkit/audits/`. Skills and
commands run them to collect evidence for their reports. They never replace the project's
own build, test and lint commands; they add static checks on top of them.

Every script uses only the Python standard library (Playwright is an optional import),
runs on Python 3.9 or newer, writes UTF-8 to stdout, never uses `shell=True`, resolves
Node executables with `shutil.which` (for example `npm.cmd` on Windows) and starts
Python sub-processes with `sys.executable`. Output is line-buffered also when it goes to a
pipe, so every finished step is visible at once, and every external tool runs with a real
time limit and without access to the terminal (see
[External commands and time limits](#external-commands-and-time-limits)).

## Interpreter detection protocol

Every skill that runs an audit first finds a working Python interpreter. Do this once
per session and reuse the result.

1. Try the candidates in this order: `python`, then `py -3` (Windows only), then
   `python3`.
2. Validate each candidate by **executing** `<candidate> --version` with its output
   captured and a timeout of about 10 seconds. A candidate is valid only when the
   command exits 0 and prints `Python 3.x`. Never accept a candidate just because it
   exists on `PATH`: the Microsoft Store stub (`python.exe` or `python3.exe` under
   `WindowsApps`) prints nothing, exits non-zero (9009) or opens the Store, and can
   block when attached to a console, so a timeout counts as a failure.
3. Use the first candidate that succeeds for every audit in the session.
4. If no candidate succeeds, every audit is `SKIPPED (no Python)`. Say so in the
   report and fall back to the project's own build, test and lint commands recorded in
   `.redevkit/memory/tech.md`.

```bash
# POSIX shells (Git Bash included); `timeout` guards against a blocking stub
PY=""
for candidate in python "py -3" python3; do
  if timeout 10 $candidate --version 2>/dev/null </dev/null | grep -q "^Python 3"; then
    PY="$candidate"; break
  fi
done
```

On macOS without GNU `timeout`, drop the `timeout 10` prefix (there is no Store stub).

```powershell
# PowerShell: redirected output + timeout, so the Store stub cannot block
$PY = $null
foreach ($candidate in @('python', 'py -3', 'python3')) {
  $exe, $rest = $candidate -split ' '
  if (-not (Get-Command $exe -ErrorAction SilentlyContinue)) { continue }
  $out = Join-Path $env:TEMP 'redevkit-python-version.txt'
  $argList = @(@($rest) + '--version' | Where-Object { $_ })
  $p = Start-Process -FilePath $exe -ArgumentList $argList -NoNewWindow -PassThru `
    -RedirectStandardOutput $out -RedirectStandardError "$out.err"
  if (-not $p.WaitForExit(10000)) { $p.Kill(); continue }
  if ($p.ExitCode -eq 0 -and (Get-Content $out -Raw) -match '^Python 3') { $PY = $candidate; break }
}
```

## How to run

Run from the project root. `<PY>` is the interpreter chosen above.

```bash
<PY> .redevkit/audits/checklist.py . --no-runtime          # fast suite
<PY> .redevkit/audits/verify_all.py . --no-runtime         # full suite, no running app
<PY> .redevkit/audits/verify_all.py . --url http://localhost:3000 --report verification.json
<PY> .redevkit/audits/verify_all.py . --no-runtime --no-tests --exclude "prototypes/"
<PY> .redevkit/audits/security_scan.py . --output summary  # one audit
<PY> .redevkit/audits/test_runner.py . --timeout 600 --log test-output.log
<PY> .redevkit/audits/code_state.py .                        # code state of a test or verify run
```

Orchestrator options (identical in `checklist.py` and `verify_all.py`):

| Option | Effect |
| --- | --- |
| `project` | Project directory (default `.`) |
| `--url URL` | Running app URL for Lighthouse and Playwright; without it they are SKIPPED. It must be an `http://` or `https://` URL without quotes or white space, otherwise the orchestrator exits `2` |
| `--no-runtime` | Drop every URL-based runtime check (the only runtime flag) |
| `--no-tests` | Do not run the project's test suite: the Test Runner check is `SKIPPED (test suite not run (--no-tests); ...)`. Use it when the suite already ran for the same code |
| `--exclude PATTERN` | Exclude paths in every audit that scans files (repeatable); see [Excluding paths](#excluding-paths) |
| `--no-gitignore` | Audits that scan files do not read `.gitignore` |
| `--stop-on-fail` | Stop after the first failed check |
| `--report FILE` | Write a JSON report with commands, durations, output and status |

The orchestrators find the audits next to themselves (`Path(__file__).parent`), so they
work from any working directory. They forward `--exclude` and `--no-gitignore` only to
the audits that scan project files (every audit except `lint_runner.py`,
`test_runner.py`, `lighthouse_audit.py` and `playwright_runner.py`, which run external
tools with their own configuration). Before each check they print
`[RUN]  <check> (time limit Ns)`, so a long step is visible while it runs.

`test_runner.py` options:

| Option | Effect |
| --- | --- |
| `project` | Project directory (default `.`) |
| `--timeout SECONDS` | Time limit of the test command (default `300`). When it expires the whole process tree is killed and the result is a timeout (see [Exit codes](#exit-codes)) |
| `--log FILE` | Write the full combined output (stdout and stderr, in order) of the test command to `FILE`; the console shows only its last 40 lines |
| `--coverage` | Collect coverage when the tool for it is installed (Vitest with `@vitest/coverage-v8` or `@vitest/coverage-istanbul`, Jest, pytest with `pytest-cov`). Otherwise the suite runs without coverage and one line says `SKIPPED (coverage provider not installed)` or `SKIPPED (coverage not supported for this test command)` |

## Excluding paths

Every audit that scans project files uses one policy (`audit_common.py`). A path is
excluded by the **last** matching rule of, in order:

1. **Shared defaults.** Dependencies and vendored code (`node_modules/`, `vendor/`,
   `bower_components/`, `.venv/`, `venv/`, ...), build output (`dist/`, `build/`, `out/`,
   `.next/`, `.nuxt/`, `.svelte-kit/`, ...), tool caches, generated reports
   (`coverage/`, `htmlcov/`, `playwright-report/`, `test-results/`, `blob-report/`),
   agent folders (`.redevkit/`, `.claude/`, `.codex/`, `.agents/`), and minified or
   generated assets (`*.min.js`, `*.min.css`, `*.map`). Some audits add their own
   folders (SEO: tests, docs, examples, `errors/`, e-mail templates; GEO: also
   `public/`, `components/`, `layouts/`, `partials/`; UX: `ui/`; mobile: `ios/`,
   `android/`; i18n: tests and specs).
2. **The project's `.gitignore` files**: the root one, nested ones (each relative to
   its own folder) and `.git/info/exclude`. Global git excludes are not read.
   `--no-gitignore` turns this off.
3. **Your patterns**: the file `.redevkit/audit-ignore` (one pattern per line, `#`
   comments), then every `--exclude PATTERN` on the command line.

Patterns use `.gitignore` syntax: `prototypes/` (a folder at any depth),
`/prototypes/` (only at the project root), `SPECs/Funil*/` (a slash in the middle
anchors the pattern to the root), `*.generated.html`, `docs/**`, `a/**/b`, and `!vendor/`
to include again something an earlier rule excluded. Matching is by path segment
relative to the project root and ignores case: `build/` never matches `app-builder/`,
and a project that itself lives inside a `build/` folder is still scanned.

```text
# .redevkit/audit-ignore
SPECs/Funil*/
app/Views/errors/
```

```bash
<PY> .redevkit/audits/accessibility_checker.py . --exclude "SPECs/Funil*/" --exclude legacy/
<PY> .redevkit/audits/checklist.py . --no-runtime --exclude "SPECs/Funil*/"
```

Limits: no global gitignore, no `core.ignorecase=false` (matching always ignores case),
a file cannot be included again inside an excluded folder (as in git), and a pattern
with a character class that cannot be compiled (for example the reversed range in
`*.[a-Z]`) is ignored.
`bundle_analyzer.py` measures build output, so it applies only your patterns, never the
defaults or `.gitignore`.

## Server-rendered views (PHP)

The accessibility, SEO, GEO and UX audits also read `.php` and `.phtml` views. A PHP file
counts as a view only when markup remains after its PHP blocks are removed, so
controllers, models and config files are ignored. Every `<?php ... ?>` and `<?= ... ?>`
block is replaced by a dynamic-value marker before the checks run: `alt="<?= $alt ?>"`
is a non-empty value, and `<img src="<?= $url ?>">` is one tag. Document-level checks
run only on files that contain the element (`<html lang>`, the skip link on `<body>`,
`<title>` and meta tags on `<head>`), so partial views do not trigger them. Error pages
(`errors/`, `error_404.php`) and e-mail templates are not SEO or GEO pages; GEO counts
a PHP view as a page only when it renders an `<h1>` and is not a layout or partial.

## Code state

`code_state.py` is not an audit: it prints the **code state** that the test and verify
reports record, and compares it with a recorded one. It is read-only.

```bash
<PY> .redevkit/audits/code_state.py .                                  # Commit, Branch, Working tree, Changed files, Tree fingerprint
<PY> .redevkit/audits/code_state.py . --json                           # the same as one JSON object
<PY> .redevkit/audits/code_state.py . --expect sha256:<fingerprint>    # Compare: SAME (exit 0) or DIFFERENT (exit 1)
```

The **Tree fingerprint** is a SHA-256 over the sorted list of `<file sha256>  <path>` lines,
so it changes when any file is added, removed, renamed or edited, whether git tracks it or
not. The two fingerprints the kit used before (of `git status` and of `git diff`) did not
change when an untracked file was edited, which made a verify reuse a stale test run.

| | |
| --- | --- |
| Files hashed in a git repository | Every tracked file, plus every untracked file that git does not ignore and that is not dependency, build or report output (the shared defaults of [Excluding paths](#excluding-paths)) |
| Files hashed without git | Every file that the shared defaults and the project's `.gitignore` files do not exclude |
| Never hashed | `.redevkit/`, `specs/`, `.claude/`, `.agents/`, `.codex/` and `.git/` at the project root: reports and memory are written after a run and must not make the code look changed |
| Independent of | The shell, the commit history and git being installed. A commit made after the run does not change it |
| Line endings | Hashed as they are on disk: a CRLF checkout of the same code is a different state |

`HEAD`, `Branch` and `Working tree` are context for the reader; only the fingerprint decides
whether two states are the same. Exit codes: `0` computed (with `--expect`: same), `1` with
`--expect`: different, `2` usage error. It never prints `SKIPPED`, and it is the only script
here whose exit `1` is not a failure.

## External commands and time limits

Every external tool (`npm`, `tsc`, `lighthouse`, the project's test command, and each
audit an orchestrator starts) runs through `run_external` in `audit_common.py`:

- **Never interactive.** The command gets no terminal input (its stdin is the null
  device) and the environment `CI=1` (an existing `CI` value is kept), `NO_COLOR=1` and
  `FORCE_COLOR=0`. A test script such as `"test": "vitest"` runs once instead of entering
  watch mode, nothing can wait for an answer, and the output carries no colour codes.
- **A real time limit.** The command runs in its own process group. When the limit
  expires the whole process tree is killed (`taskkill /F /T` on Windows, where `npm.cmd`
  is a `cmd.exe` that starts `node`; the process group and every descendant elsewhere),
  and the output printed until then is kept. No wait on an output pipe is unbounded.
- **Nested limits.** An orchestrator gives each check the worst case of its audit plus
  60 seconds, so the audit reports its own timeout before the orchestrator has to stop it.

| Step | Limit |
| --- | --- |
| `test_runner.py`: the test command | 300 s, or `--timeout SECONDS` |
| `lint_runner.py`: each linter (at most 4) | 120 s |
| `type_coverage.py`: `tsc` | 180 s for each `tsconfig.json`, 240 s for all of them |
| `security_scan.py`: `npm audit` | 90 s |
| `lighthouse_audit.py`: Lighthouse | 180 s, or `--timeout` |
| Orchestrator check: Test Runner | 360 s |
| Orchestrator check: Lint | 540 s |
| Orchestrator check: Lighthouse | 240 s |
| Orchestrator check: Playwright | 120 s |
| Orchestrator check: any other audit | 300 s |

A full suite therefore needs more than the default time limit of most agent shell
tools: give the call a limit that fits (the test command alone may use 300 seconds),
or run it in the background and read its output, which arrives line by line.

What a timeout looks like:

- `test_runner.py` prints `[TIMEOUT] Test command timed out after Ns ...`, exits `1`,
  and its JSON has `"status": "timeout"`, `"timed_out": true` and a `"reason"`. The last
  lines the command printed are shown, and `--log FILE` keeps all of them.
- `lint_runner.py` prints `[TIMEOUT] <linter> - timeout after 120s ...`, exits `1`, and
  the linter's JSON entry has `"timed_out": true`.
- A `tsc` or `npm audit` that times out is a skipped sub-check (`SKIPPED (...)`).
- A check stopped by an orchestrator is an `error` with the reason
  `timed out after Ns`; the report keeps the output the audit printed so far. When the
  audit hit its own limit, the check is `failed` and its reason quotes the audit's
  `[TIMEOUT]` line.

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | PASS: the audit ran and found nothing at or above its failure threshold |
| `1` | FAIL: blocking findings; also a timeout of the test command or of a linter (it prints a `[TIMEOUT]` line) |
| `2` | Usage error or missing input path |
| `3` | SKIPPED: nothing was checked (the audit could not run or does not apply); it printed `SKIPPED (<reason>)` |

The orchestrators (`checklist.py`, `verify_all.py`) aggregate their checks:

| Code | Meaning |
| --- | --- |
| `0` | At least one check ran (PASS) and none failed; skipped checks are listed as not verified |
| `1` | Any check failed or errored |
| `2` | Usage error (bad option, bad `--url`, missing project directory) |
| `3` | SKIPPED: every check was skipped, nothing was verified; prints `SKIPPED (all N check(s) skipped; nothing was verified)` |

A skipped `required` check (Security Scan, Lint Check, Lighthouse with `--url`) is
marked `[SKIPPED] (required)` in the summary and named on a `Required check(s) SKIPPED`
line. It does not fail the suite on its own, but a run where everything skipped is `3`,
never `0`. The JSON report carries `status` (`passed`, `failed`, `skipped`), `exit_code`
and `success` (true only for exit `0`); each entry of `results` has its own `status`
(`passed`, `failed`, `skipped`, or `error` for a check that timed out or could not start),
`reason`, `stdout` and `stderr`.

## SKIPPED semantics

- A skipped audit is reported as `SKIPPED (<reason>)`, **never** as `PASS`. Examples:
  `SKIPPED (no Python)`, `SKIPPED (npm not found on PATH)`,
  `SKIPPED (no Prisma or Drizzle schema files found)`,
  `SKIPPED (Drizzle schemas found, not validated)`,
  `SKIPPED (Lighthouse CLI not found on PATH)`.
- An audit skips when its external tool is missing, cannot start or times out (where
  noted below), or when the project has nothing for it to check.
- A partial skip (for example `npm audit` inside `security_scan.py`) keeps the overall
  result of the checks that did run and prints one `SKIPPED (<reason>)` line per skipped
  sub-check. The orchestrators copy those lines into the summary and the JSON report.
- A SKIPPED check does not fail a suite, but the summary counts it and says the suite
  passed with checks "SKIPPED (not verified)". When every check skipped, the suite itself
  is SKIPPED (exit `3`), not PASS. Reports and verify artifacts must list every SKIPPED
  check with its reason.

## What each audit checks

| Script | Checks | Skips when |
| --- | --- | --- |
| `security_scan.py` | Lock files, `npm audit`, hard-coded secrets, dangerous code (`eval`/`exec` builtins, `shell=True`, XSS sinks, SQL built from variables), risky config | No source, configuration or dependency file to scan; `npm audit` alone is skipped when npm is missing, fails or times out |
| `dependency_analyzer.py` | Unbounded or remote dependency versions, missing or duplicate lock files (a workspace package may use a parent's lock file; a manifest without dependencies needs none), unpinned Python requirements (offline) | No dependency manifest |
| `lint_runner.py` | `npm run lint` or project-local `eslint`, project-local `tsc --noEmit`, `ruff`, `mypy`; a linter that exceeds 120 s fails with `[TIMEOUT]` | Each missing linter; all of them missing |
| `type_coverage.py` | Explicit `any`, `@ts-ignore`, project-local `tsc`, Python annotation ratio | No TS or Python files; `tsc` missing or timed out (sub-check) |
| `schema_validator.py` | Prisma naming, ids, `createdAt`, missing `@@index` (advisory). Drizzle files are only listed as "not validated" | No Prisma or Drizzle schema; Drizzle schemas only (nothing validated) |
| `test_runner.py` | `npm test`, project-local vitest or jest, pytest or unittest with the project's `.venv`/`venv` interpreter when it exists, else `sys.executable` (see [Test Runner verdict](#test-runner-verdict)) | No test command (the `npm init` placeholder script counts as none), runner or declared framework not installed, no tests found, or exit 0 without any test result in the output |
| `ux_audit.py` | UX laws, typography, color, motion and effect heuristics, also on PHP views | No frontend source files or PHP views |
| `accessibility_checker.py` | Input and button labels, `<html lang>`, skip link (when the page has a `<nav>` or `<header>`), keyboard handlers, positive `tabIndex` (comments ignored), also on PHP views | No HTML, JSX, TSX or PHP view files |
| `seo_checker.py` | `<title>`, meta description, Open Graph (files with a `<head>`), single H1, image alt, also on PHP views | No page files |
| `geo_checker.py` | AI-citation readiness of public pages: headings, JSON-LD, author, dates, FAQ | No public pages |
| `bundle_analyzer.py` | Size of built JS and CSS assets (raw and gzip) | No build output, or no JS/CSS asset in it; build first |
| `react_performance_checker.py` | Possible await waterfalls, barrel imports, static imports of large components, `useEffect` fetching, memoization, `<img>` in Next.js projects (advisory warnings) | Not a React project |
| `mobile_audit.py` | Touch targets, gestures, haptics, performance and platform rules for React Native and Flutter | No mobile source files |
| `i18n_checker.py` | Missing or extra locale keys (nested `locales/en/common.json` and flat `locales/pt-BR.json` layouts), hard-coded UI strings | No i18n setup or locale files |
| `api_validator.py` | OpenAPI completeness (files named `openapi.*`, `swagger.*`, `*.openapi.*`); error handling, status codes and validation in route code | No API files |
| `lighthouse_audit.py` | Performance, accessibility, best practices and SEO scores against thresholds (needs `--url`) | Lighthouse CLI missing |
| `playwright_runner.py` | Smoke test of a URL: status, title, page errors, basic accessibility (needs `--url`) | Playwright or its Chromium missing |
| `checklist.py` | Fast suite: security, lint, types, schema, tests, UX, accessibility, SEO, runtime | - |
| `verify_all.py` | Full suite: the fast suite plus dependencies, GEO, bundle, React, mobile, i18n, API | - |
| `code_state.py` | Content fingerprint of the project's code for the test and verify reports (see [Code state](#code-state)); not an audit, not run by the orchestrators | - |
| `validation_runner.py` | Shared runner imported by the two orchestrators (not run directly) | - |
| `audit_common.py` | Shared path exclusion, PHP view reading and the external command runner (`run_external`) imported by the audits (not run directly) | - |

Every audit that scans files accepts `--exclude PATTERN` (repeatable) and
`--no-gitignore`, walks the project once and applies the policy of
[Excluding paths](#excluding-paths): by path segment, never by substring.

### Test Runner verdict

`test_runner.py` decides from the exit code of the test command and from its output:

| Result | When |
| --- | --- |
| PASS (`0`) | Exit 0 and the output shows that tests ran: a summary of unittest, pytest, Jest, Vitest, `node --test`, Mocha or a generic `N passed` with at least one test, or, for a format it cannot count, any sign of executed tests (`12 specs`, `ok 1`, a check mark, `PASS file`). The JSON then has `"counts_parsed": false` and zero counts |
| SKIPPED (`3`) | No test command; `npm` or the declared framework is not installed (`vitest is not installed in node_modules/.bin (run the package install first)`); the summary says zero tests ran (`node --test` without test files, `Ran 0 tests`); Vitest or Jest found no test file; pytest or unittest exited 5; or the command exited 0 and printed no test result at all (`"test": "echo ok"`). Run the project's own test command and judge its output |
| FAIL (`1`) | Any other non-zero exit code (exit 5 of a command that is not pytest or unittest included) and a timeout |

Details:

- Python: when the project root has no `test*.py` and `tests/` (or `test/`) is not a
  package, unittest starts there (`discover -s tests`); from the root it would find
  nothing and failing tests would look like "no tests found".
- Node: `node_modules/.bin` is also looked up in the parent folders (workspaces).
- The console shows the last 40 lines of the output (failures and the summary are at the
  end); `--log FILE` keeps all of it.
- The JSON at the end of the output has `status` (`passed`, `failed`, `skipped`,
  `timeout`), `timed_out`, `exit_code`, `duration_seconds`, `tests_run`, `tests_passed`,
  `tests_failed`, `counts_parsed`, `coverage`, `reason` (unless passed) and `log` (with
  `--log`).

## Tests

The regression tests live in `test-audits/` of the
[REDEVKIT repository](https://github.com/Reprograme/redevkit), one module per fixed bug
(`test_<bug-id>_*.py`) with fixtures in `test-audits/fixtures/<bug-id>/`:

```bash
python -m unittest discover -s test-audits -v
```
