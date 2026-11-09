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
<PY> .redevkit/audits/security_scan.py . --output summary  # one audit
```

Orchestrator options (identical in `checklist.py` and `verify_all.py`):

| Option | Effect |
| --- | --- |
| `project` | Project directory (default `.`) |
| `--url URL` | Running app URL for Lighthouse and Playwright; without it they are SKIPPED |
| `--no-runtime` | Drop every URL-based runtime check (the only runtime flag) |
| `--stop-on-fail` | Stop after the first failed check |
| `--report FILE` | Write a JSON report with commands, durations, output and status |

The orchestrators find the audits next to themselves (`Path(__file__).parent`), so they
work from any working directory.

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
| `security_scan.py` | Lock files, `npm audit`, hard-coded secrets, dangerous code (eval, `shell=True`, XSS sinks, SQL built from variables), risky config | `npm audit` alone is skipped when npm is missing or fails |
| `dependency_analyzer.py` | Unbounded or remote dependency versions, missing or duplicate lock files, unpinned Python requirements (offline) | No dependency manifest |
| `lint_runner.py` | `npm run lint` or project-local `eslint`, project-local `tsc --noEmit`, `ruff`, `mypy` | Each missing linter; all of them missing |
| `type_coverage.py` | Explicit `any`, `@ts-ignore`, project-local `tsc`, Python annotation ratio | No TS or Python files; `tsc` missing or timed out (sub-check) |
| `schema_validator.py` | Prisma naming, ids, `createdAt`, missing `@@index` (advisory). Drizzle files are only listed as "not validated" | No Prisma or Drizzle schema; Drizzle schemas only (nothing validated) |
| `test_runner.py` | `npm test`, project-local vitest or jest, pytest or unittest via `sys.executable` | No test command, runner missing, no tests found |
| `ux_audit.py` | UX laws, typography, color, motion and effect heuristics | No frontend source files |
| `accessibility_checker.py` | Input and button labels, `<html lang>`, skip link, keyboard handlers, positive `tabIndex` (comments ignored) | No HTML, JSX or TSX files |
| `seo_checker.py` | `<title>`, meta description, Open Graph, single H1, image alt | No page files |
| `geo_checker.py` | AI-citation readiness of public pages: headings, JSON-LD, author, dates, FAQ | No public pages |
| `bundle_analyzer.py` | Size of built JS and CSS assets (raw and gzip) | No build output; build first |
| `react_performance_checker.py` | Possible await waterfalls, barrel imports, static imports of large components, `useEffect` fetching, memoization, `<img>` (advisory warnings) | Not a React project |
| `mobile_audit.py` | Touch targets, gestures, haptics, performance and platform rules for React Native and Flutter | No mobile source files |
| `i18n_checker.py` | Missing or extra locale keys (nested `locales/en/common.json` and flat `locales/pt-BR.json` layouts), hard-coded UI strings | No i18n setup or locale files |
| `api_validator.py` | OpenAPI completeness; error handling, status codes and validation in route code | No API files |
| `lighthouse_audit.py` | Performance, accessibility, best practices and SEO scores against thresholds (needs `--url`) | Lighthouse CLI missing |
| `playwright_runner.py` | Smoke test of a URL: status, title, page errors, basic accessibility (needs `--url`) | Playwright or its Chromium missing |
| `checklist.py` | Fast suite: security, lint, types, schema, tests, UX, accessibility, SEO, runtime | - |
| `verify_all.py` | Full suite: the fast suite plus dependencies, GEO, bundle, React, mobile, i18n, API | - |
| `validation_runner.py` | Shared runner imported by the two orchestrators (not run directly) | - |

All audits walk the project once, prune `node_modules`, build output and agent folders
(`.redevkit`, `.claude`, `.codex`, `.agents`) by path segment, and never by substring.

## Tests

The regression tests live in `test-audits/` of the REDEVKIT repository, one module per
fixed bug (S1-S5, S7-S10, P4) with fixtures in `test-audits/fixtures/<bug-id>/`:

```bash
python -m unittest discover -s test-audits -v
```
