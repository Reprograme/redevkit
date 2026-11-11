# REDEVKIT audits

Optional, dependency-free Python audits installed in `.redevkit/audits/`. Skills and
commands run them to collect evidence (D05, K12). They never replace the project's own
build, test and lint commands; they add static checks on top of them.

Every script uses only the Python standard library (Playwright is an optional import),
runs on Python 3.9 or newer, writes UTF-8 to stdout, never uses `shell=True`, resolves
Node executables with `shutil.which` (for example `npm.cmd` on Windows) and starts
Python sub-processes with `sys.executable`.

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
```

Orchestrator options (identical in `checklist.py` and `verify_all.py`):

| Option | Effect |
| --- | --- |
| `project` | Project directory (default `.`) |
| `--url URL` | Running app URL for Lighthouse and Playwright; without it they are SKIPPED |
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
tools with their own configuration).

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
and a file cannot be included again inside an excluded folder (as in git).
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

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | PASS: the audit ran and found nothing at or above its failure threshold |
| `1` | FAIL: blocking findings |
| `2` | Usage error or missing input path |
| `3` | SKIPPED: nothing was checked (the audit could not run or does not apply); it printed `SKIPPED (<reason>)` |

The orchestrators (`checklist.py`, `verify_all.py`) aggregate their checks:

| Code | Meaning |
| --- | --- |
| `0` | At least one check ran (PASS) and none failed; skipped checks are listed as not verified |
| `1` | Any check failed or errored |
| `2` | Usage error (bad option, missing project directory) |
| `3` | SKIPPED: every check was skipped, nothing was verified; prints `SKIPPED (all N check(s) skipped; nothing was verified)` |

A skipped `required` check (Security Scan, Lint Check, Lighthouse with `--url`) is
marked `[SKIPPED] (required)` in the summary and named on a `Required check(s) SKIPPED`
line. It does not fail the suite on its own, but a run where everything skipped is `3`,
never `0`. The JSON report carries `status` (`passed`, `failed`, `skipped`), `exit_code`
and `success` (true only for exit `0`).

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
| `security_scan.py` | Lock files, `npm audit`, hard-coded secrets, dangerous code (`eval`/`exec` builtins, `shell=True`, XSS sinks, SQL built from variables), risky config | `npm audit` alone is skipped when npm is missing or fails |
| `dependency_analyzer.py` | Unbounded or remote dependency versions, missing or duplicate lock files (a workspace package may use a parent's lock file; a manifest without dependencies needs none), unpinned Python requirements (offline) | No dependency manifest |
| `lint_runner.py` | `npm run lint` or project-local `eslint`, project-local `tsc --noEmit`, `ruff`, `mypy` | Each missing linter; all of them missing |
| `type_coverage.py` | Explicit `any`, `@ts-ignore`, project-local `tsc`, Python annotation ratio | No TS or Python files; `tsc` missing or timed out (sub-check) |
| `schema_validator.py` | Prisma naming, ids, `createdAt`, missing `@@index` (advisory). Drizzle files are only listed as "not validated" | No Prisma or Drizzle schema; Drizzle schemas only (nothing validated) |
| `test_runner.py` | `npm test`, project-local vitest or jest, pytest or unittest via `sys.executable` | No test command (the `npm init` placeholder script counts as none), runner missing, no tests found (also "Ran 0 tests" with exit 0) |
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
| `validation_runner.py` | Shared runner imported by the two orchestrators (not run directly) | - |
| `audit_common.py` | Shared path exclusion and PHP view reading imported by the audits (not run directly) | - |

Every audit that scans files accepts `--exclude PATTERN` (repeatable) and
`--no-gitignore`, walks the project once and applies the policy of
[Excluding paths](#excluding-paths): by path segment, never by substring.

## Tests

The regression tests live in `test-audits/` of the REDEVKIT repository, one module per
fixed bug (S1-S5, S7-S13, P4) with fixtures in `test-audits/fixtures/<bug-id>/`:

```bash
python -m unittest discover -s test-audits -v
```
