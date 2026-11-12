#!/usr/bin/env python3
"""
Test Runner - Unified test execution and coverage reporting.
Runs the project's tests based on project type.

Usage:
    python test_runner.py <project_path> [--coverage] [--timeout SECONDS] [--log FILE]

Supports:
    - Node.js: npm test, jest, vitest (project-local binaries only, no downloads)
    - Python: pytest, unittest (the project's .venv/venv interpreter when it exists,
      otherwise the current interpreter)

Executables are resolved with shutil.which (npm resolves to npm.cmd on
Windows). The test command runs through audit_common.run_external: it cannot
read the terminal (no watch mode, no prompt) and the whole process tree is
killed when the time limit expires.

Verdict (the exit code follows the 0/1/2/3 contract of the audits):

* PASS (0): the command exited 0 and its output shows that tests ran: a
  recognised summary (unittest, pytest, jest, vitest, node:test, mocha, or a
  generic "N passed") with at least one test, or, for a format the runner does
  not parse, any evidence of executed tests ("12 specs", "ok 1", a check mark,
  "PASS file"); see ``has_test_evidence``.
* SKIPPED (3): no test command, runner or declared framework not installed,
  the summary says zero tests ran, the runner reported that it found no test
  file, or the command exited 0 without any test result in its output (for
  example ``"test": "echo ok"``). Nothing was verified: never PASS.
* FAIL (1): any other non-zero exit code, and a timeout. A timeout prints a
  ``[TIMEOUT]`` line and the JSON carries ``"status": "timeout"`` and
  ``"timed_out": true``.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

sys.dont_write_bytecode = True  # importing the shared helper must not leave __pycache__ behind
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_common import run_external, strip_ansi  # noqa: E402

EXIT_PASS, EXIT_FAIL, EXIT_USAGE, EXIT_SKIPPED = 0, 1, 2, 3
TIMEOUT_SECONDS = 300  # default of --timeout
TAIL_LINES = 40  # lines of test output shown (the end: failures and the summary are there)
NO_TESTS_EXIT_CODES = {5}  # pytest "no tests collected", unittest "NO TESTS RAN" (3.12+)
PYTHON_FRAMEWORKS = {"pytest", "unittest"}  # the only commands whose exit 5 means "no tests"
NPM_PLACEHOLDER = "no test specified"  # `npm init` default: echo "Error: no test specified" && exit 1
VITEST_COVERAGE_PROVIDERS = ("@vitest/coverage-v8", "@vitest/coverage-istanbul")
COVERAGE_PROVIDER_MISSING = "coverage provider not installed"
COVERAGE_UNSUPPORTED = "coverage not supported for this test command"
NO_TEST_RESULT = "the test command exited 0 but its output shows no test result"


def utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)  # type: ignore[union-attr]
        except (AttributeError, ValueError, OSError):
            pass


def which(name: str) -> Optional[str]:
    """Resolve an executable on PATH (``npm`` -> ``npm.cmd`` on Windows)."""
    return shutil.which(name)


def local_bin(project_path: Path, name: str) -> Optional[str]:
    """node_modules/.bin executable of the project or of a parent folder (workspaces hoist
    dependencies, and npm itself looks there); never downloads with npx."""
    for parent in (project_path, *project_path.parents):
        folder = parent / "node_modules" / ".bin"
        if folder.is_dir():
            found = shutil.which(name, path=str(folder))
            if found:
                return found
    return None


def node_package_installed(project_path: Path, package: str) -> bool:
    """True when ``node_modules/<package>`` exists in the project or in a parent folder."""
    return any(
        (parent / "node_modules" / package / "package.json").is_file()
        for parent in (project_path, *project_path.parents)
    )


def project_python(project_path: Path) -> str:
    """Interpreter of the project's virtual environment (``.venv`` or ``venv``), else the current one."""
    for name in (".venv", "venv"):
        for relative in (("Scripts", "python.exe"), ("bin", "python"), ("bin", "python3")):
            candidate = project_path / name / relative[0] / relative[1]
            if candidate.is_file():
                return str(candidate)
    return sys.executable


def python_module_available(module: str, python: Optional[str] = None) -> bool:
    """True when ``module`` can be imported by ``python`` (default: the current interpreter)."""
    if python and os.path.normcase(python) != os.path.normcase(sys.executable):
        probe = f"import importlib.util, sys; sys.exit(0 if importlib.util.find_spec({module!r}) else 1)"
        try:
            done = run_external([python, "-c", probe], timeout=30)
        except OSError:
            return False
        return done.returncode == 0 and not done.timed_out
    try:
        return importlib.util.find_spec(module) is not None
    except (ImportError, ValueError):
        return False


def _python_project(project_path: Path) -> bool:
    markers = ("pyproject.toml", "requirements.txt", "setup.py", "setup.cfg", "pytest.ini", "tox.ini")
    return any((project_path / name).exists() for name in markers)


def _pytest_configured(project_path: Path) -> bool:
    if (project_path / "pytest.ini").exists() or (project_path / "conftest.py").exists():
        return True
    for name in ("pyproject.toml", "requirements.txt", "requirements-dev.txt", "setup.cfg", "tox.ini"):
        path = project_path / name
        try:
            if path.is_file() and "pytest" in path.read_text("utf-8", errors="ignore"):
                return True
        except OSError:
            continue
    return False


def _unittest_discover_args(project_path: Path) -> List[str]:
    """Start directory for ``unittest discover``.

    From the project root unittest only finds ``test*.py`` in the root and in packages
    below it, so the usual ``tests/test_x.py`` without ``tests/__init__.py`` is invisible
    ("no tests found" although tests exist, even failing ones). When the root has no test
    file, start in the first of ``tests``/``test`` that is not a package and holds one.
    """
    if any(project_path.glob("test*.py")):
        return []
    for name in ("tests", "test"):
        folder = project_path / name
        if folder.is_dir() and not (folder / "__init__.py").exists() and any(folder.glob("test*.py")):
            return ["-s", name]
    return []


def detect_test_framework(project_path: Path) -> Dict[str, Any]:
    """Detect the test command. ``cmd`` is None and ``skip_reason`` set when it cannot run.

    ``coverage_cmd`` is None when coverage cannot be collected; ``coverage_skip_reason``
    then says why.
    """
    result: Dict[str, Any] = {
        "type": "unknown",
        "framework": None,
        "cmd": None,
        "coverage_cmd": None,
        "coverage_skip_reason": COVERAGE_UNSUPPORTED,
        "skip_reason": "no test framework detected",
    }

    package_json = project_path / "package.json"
    if package_json.exists():
        result["type"] = "node"
        try:
            pkg = json.loads(package_json.read_text(encoding="utf-8-sig"))  # npm accepts a BOM
        except (OSError, ValueError) as exc:  # ValueError: invalid JSON or invalid UTF-8
            pkg = {}
            result["skip_reason"] = f"package.json could not be read: {exc}"
        scripts = pkg.get("scripts", {}) if isinstance(pkg, dict) else {}
        deps: Dict[str, Any] = {}
        if isinstance(pkg, dict):
            for section in ("dependencies", "devDependencies"):
                if isinstance(pkg.get(section), dict):
                    deps.update(pkg[section])

        coverage_cmd = None
        coverage_skip_reason = COVERAGE_UNSUPPORTED
        framework = None
        binary = None
        if "vitest" in deps:
            framework = "vitest"
            binary = local_bin(project_path, "vitest")
            if binary and any(node_package_installed(project_path, name) for name in VITEST_COVERAGE_PROVIDERS):
                coverage_cmd = [binary, "run", "--coverage"]
            else:
                # Without its provider ``vitest --coverage`` fails before running any test.
                coverage_skip_reason = COVERAGE_PROVIDER_MISSING
        elif "jest" in deps:
            framework = "jest"
            binary = local_bin(project_path, "jest")
            coverage_cmd = [binary, "--coverage"] if binary else None

        test_script = scripts.get("test") if isinstance(scripts, dict) else None
        placeholder = isinstance(test_script, str) and NPM_PLACEHOLDER in test_script
        has_script = not placeholder and isinstance(scripts, dict) and "test" in scripts
        if placeholder and not framework:
            # Not a test command: fall through to the Python detection, else SKIPPED.
            result["skip_reason"] = "package.json test script is the npm placeholder (no test specified)"
        elif framework and not binary:
            # The declared framework is not installed: `npm test` could only fail with
            # "command not found". Nothing can be verified until the dependencies are installed.
            result["framework"] = framework
            result["skip_reason"] = f"{framework} is not installed in node_modules/.bin (run the package install first)"
            return result
        elif has_script:
            npm = which("npm")
            result["framework"] = framework or "npm test"
            if npm:
                result["cmd"] = [npm, "test"]
                result["coverage_cmd"] = coverage_cmd
                result["coverage_skip_reason"] = coverage_skip_reason
                result["skip_reason"] = None
            else:
                result["skip_reason"] = "npm not found on PATH"
            return result
        elif framework:
            result["framework"] = framework
            result["cmd"] = [binary, "run"] if framework == "vitest" else [binary]
            result["coverage_cmd"] = coverage_cmd
            result["coverage_skip_reason"] = coverage_skip_reason
            result["skip_reason"] = None
            return result

    if _python_project(project_path):
        result["type"] = "python"
        python = project_python(project_path)
        if python_module_available("pytest", python):
            result["framework"] = "pytest"
            result["cmd"] = [python, "-m", "pytest", "-v"]
            if python_module_available("pytest_cov", python):
                result["coverage_cmd"] = [python, "-m", "pytest", "--cov", "--cov-report=term-missing"]
            else:
                result["coverage_skip_reason"] = COVERAGE_PROVIDER_MISSING
            result["skip_reason"] = None
        elif _pytest_configured(project_path):
            result["framework"] = "pytest"
            result["skip_reason"] = f"pytest is not installed for {python}"
        else:
            result["framework"] = "unittest"
            result["cmd"] = [python, "-m", "unittest", "discover", "-v", *_unittest_discover_args(project_path)]
            result["skip_reason"] = None
    return result


# --------------------------------------------------------------------------
# Reading the test output
# --------------------------------------------------------------------------

_UNITTEST_RAN = re.compile(r"^Ran (\d+) tests? in ", re.MULTILINE)
_UNITTEST_RESULT = re.compile(r"^(?:OK|FAILED)(?: \(([^)\n]*)\))?[ \t]*$", re.MULTILINE)
# Vitest and Jest print a file/suite summary ("Test Files  3 passed", "Test Suites: 3 passed")
# before the test summary ("Tests  22 passed (22)", "Tests: 20 passed, 22 total"): count tests.
_TESTS_LINE = re.compile(r"^[ \t]*Tests:?[ \t]+(\S[^\n]*)$", re.MULTILINE)
# node --test summary: "ℹ tests 2" (spec reporter) or "# tests 2" (TAP reporter).
_NODE_TEST = re.compile(r"^[ \t]*[^\sA-Za-z0-9]{1,2}[ \t]+(tests|pass|fail|cancelled)[ \t]+(\d+)[ \t]*$", re.MULTILINE)
_PYTEST_SUMMARY = re.compile(
    r"^(?:=+ )?((?:\d+ [a-z]+(?:, )?)+) in \d+(?:\.\d+)?s(?: \([\d:]+\))?(?: =+)?[ \t]*$", re.MULTILINE
)
_PYTEST_NOTHING = re.compile(r"^(?:=+ )?no tests ran in \d", re.MULTILINE)
_MOCHA = re.compile(r"^[ \t]*(\d+) (passing|failing)\b", re.MULTILINE)
_GENERIC = re.compile(r"\b(\d+)\s+(?:tests?\s+)?(passed|failed)\b")  # case-sensitive: "test_2 PASSED" is a test name
_NO_TEST_FILES = re.compile(r"No test files found|No tests found, exiting with code", re.IGNORECASE)
_NPM_ECHO = re.compile(r"^> [^\n]*$", re.MULTILINE)  # npm prints the script it runs: not a test result
_TEST_EVIDENCE = (
    re.compile(r"\b[1-9]\d*\s+(?:\w+\s+){0,2}(?:pass|passed|passing|succeeded|successful)\b", re.IGNORECASE),
    re.compile(r"\b[1-9]\d*\s+(?:tests?|specs?|examples?|assertions?|scenarios?|test cases?)\b", re.IGNORECASE),
    re.compile(r"\b(?:passed|total|tests):\s*[1-9]\d*\b", re.IGNORECASE),  # dotnet, uvu, PHPUnit
    re.compile(r"\bExecuted\s+[1-9]\d*\s+of\b"),                 # karma
    re.compile(r"^ok\s+\d+\b", re.MULTILINE),                    # TAP: "ok 1 - adds"
    re.compile(r"^ok\s+\S+\s+\(?\d[\d.]*m?s\)?", re.MULTILINE),  # go test: "ok  pkg  0.012s"
    re.compile(r"^[ \t]*(?:---[ \t]+)?PASS\b", re.MULTILINE),    # jest "PASS src/a.test.js", go "--- PASS:"
    re.compile(r"^[ \t]*[✓✔√][ \t]+\S", re.MULTILINE),  # check marks of spec reporters
)


def _last(pattern: "re.Pattern[str]", text: str) -> Optional["re.Match[str]"]:
    found = None
    for found in pattern.finditer(text):
        pass
    return found


def _count(word: str, text: str) -> int:
    match = re.search(r"(\d+)\s+" + word + r"\b", text)
    return int(match.group(1)) if match else 0


def _parse_counts(output: str, result: Dict[str, Any]) -> bool:
    """Fill ``tests_run``/``tests_passed``/``tests_failed`` from the runner's summary.

    Returns True when a summary was recognised (then ``tests_run`` 0 really means "no test
    ran"), False when the format is unknown (the counts stay 0).
    """
    output = strip_ansi(output)
    passed = failed = run = 0

    ran = _last(_UNITTEST_RAN, output)
    if ran:  # unittest
        run = int(ran.group(1))
        outcome = _last(_UNITTEST_RESULT, output)
        details = dict(re.findall(r"([a-z ]+)=(\d+)", outcome.group(1))) if outcome and outcome.group(1) else {}
        numbers = {key.strip(): int(value) for key, value in details.items()}
        failed = numbers.get("failures", 0) + numbers.get("errors", 0) + numbers.get("unexpected successes", 0)
        passed = max(run - failed - numbers.get("skipped", 0) - numbers.get("expected failures", 0), 0)
    else:
        tests_lines = [m.group(1) for m in _TESTS_LINE.finditer(output) if re.search(r"\d+\s+(?:passed|failed|total|skipped|todo)\b", m.group(1))]
        node = {m.group(1): int(m.group(2)) for m in _NODE_TEST.finditer(output)}
        pytest_summary = _last(_PYTEST_SUMMARY, output)
        mocha = {m.group(2): int(m.group(1)) for m in _MOCHA.finditer(output)}
        if tests_lines:  # jest, vitest
            details = tests_lines[-1]
            passed, failed = _count("passed", details), _count("failed", details)
            total = re.search(r"(\d+)\s+total\b", details)
            run = int(total.group(1)) if total else passed + failed
        elif "tests" in node:  # node --test (spec and TAP reporters)
            run, passed = node["tests"], node.get("pass", 0)
            failed = node.get("fail", 0) + node.get("cancelled", 0)
        elif pytest_summary:
            details = pytest_summary.group(1)
            passed = _count("passed", details)
            failed = _count("failed", details) + _count("errors?", details)
            run = passed + failed
        elif _PYTEST_NOTHING.search(output):
            pass  # recognised: zero tests
        elif "passing" in mocha:
            passed, failed = mocha["passing"], mocha.get("failing", 0)
            run = passed + failed
        else:
            generic = {m.group(2): int(m.group(1)) for m in _GENERIC.finditer(output)}  # the last one wins
            if not generic:
                return False
            passed, failed = generic.get("passed", 0), generic.get("failed", 0)
            run = passed + failed

    result["tests_run"], result["tests_passed"], result["tests_failed"] = run, passed, failed
    return True


def has_test_evidence(output: str) -> bool:
    """True when the output of an unrecognised runner still shows that tests were executed."""
    text = _NPM_ECHO.sub("", strip_ansi(output))
    return any(pattern.search(text) for pattern in _TEST_EVIDENCE)


def run_tests(cmd: List[str], cwd: Path, timeout: Optional[float] = None,
              framework: Optional[str] = None) -> Dict[str, Any]:
    """Run tests and return results. ``status`` is passed, failed, skipped or timeout.

    ``output`` is the full combined stdout and stderr, in the order the runner wrote it;
    ``error`` is the reason of a skipped, failed or timed-out run.
    """
    limit = TIMEOUT_SECONDS if timeout is None else timeout
    result: Dict[str, Any] = {
        "status": "failed",
        "output": "",
        "error": "",
        "exit_code": None,
        "timed_out": False,
        "counts_parsed": False,
        "duration_seconds": 0.0,
        "tests_run": 0,
        "tests_passed": 0,
        "tests_failed": 0,
    }
    started = time.monotonic()
    try:
        proc = run_external(cmd, cwd=cwd, timeout=limit, merge_stderr=True)
    except FileNotFoundError:
        result["status"] = "skipped"
        result["error"] = f"command not found: {cmd[0]}"
        return result
    except OSError as exc:
        result["status"] = "skipped"
        result["error"] = f"could not start {cmd[0]}: {exc}"
        return result
    result["duration_seconds"] = round(time.monotonic() - started, 1)

    combined = (proc.stdout or "") + (("\n" + proc.stderr) if proc.stderr else "")
    result["output"] = combined
    result["exit_code"] = proc.returncode
    result["counts_parsed"] = _parse_counts(combined, result)
    if proc.timed_out:
        result["status"] = "timeout"
        result["timed_out"] = True
        result["error"] = (
            f"timed out after {limit:g}s and the process tree was killed "
            "(watch mode, a prompt, or a suite slower than the limit: see --timeout)"
        )
    elif proc.returncode == 0:
        if result["counts_parsed"] and result["tests_run"] == 0:
            # e.g. `node --test` without test files, unittest before 3.12: nothing was verified.
            result["status"] = "skipped"
            result["error"] = "no tests found"
        elif result["counts_parsed"] or has_test_evidence(combined):
            result["status"] = "passed"
        else:
            result["status"] = "skipped"
            result["error"] = NO_TEST_RESULT
    elif framework in PYTHON_FRAMEWORKS and proc.returncode in NO_TESTS_EXIT_CODES and result["tests_failed"] == 0:
        result["status"] = "skipped"
        result["error"] = "no tests found"
    elif result["tests_run"] == 0 and _NO_TEST_FILES.search(strip_ansi(combined)):
        # vitest and jest exit 1 when they find no test file: nothing was verified.
        result["status"] = "skipped"
        result["error"] = "no tests found"
    else:
        result["status"] = "failed"
        result["error"] = f"exit code {proc.returncode}"
    return result


def _positive_seconds(value: str) -> float:
    try:
        seconds = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a number: {value}") from None
    if seconds <= 0:
        raise argparse.ArgumentTypeError("the time limit must be greater than 0")
    return seconds


def _write_log(path: Path, text: str) -> Optional[str]:
    """Write the full output; return an error message instead of raising."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    except OSError as exc:
        return str(exc)
    return None


def main(argv: Optional[Sequence[str]] = None) -> int:
    utf8_stdio()
    parser = argparse.ArgumentParser(description="Run the project's test suite")
    parser.add_argument("project", nargs="?", default=".")
    parser.add_argument("--coverage", action="store_true", help="Run with coverage when supported")
    parser.add_argument(
        "--timeout", type=_positive_seconds, default=None, metavar="SECONDS",
        help=f"Time limit of the test command (default {TIMEOUT_SECONDS}); the process tree is killed when it expires",
    )
    parser.add_argument("--log", type=Path, metavar="FILE", help="Write the full combined test output to FILE")
    args = parser.parse_args(argv)
    timeout = TIMEOUT_SECONDS if args.timeout is None else args.timeout

    project_path = Path(args.project).resolve()
    if not project_path.is_dir():
        print(json.dumps({"error": f"Directory not found: {project_path}"}))
        return EXIT_USAGE

    print(f"\n{'=' * 60}")
    print("[TEST RUNNER] Unified Test Execution")
    print(f"{'=' * 60}")
    print(f"Project: {project_path}")
    print(f"Coverage: {'enabled' if args.coverage else 'disabled'}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    info = detect_test_framework(project_path)
    print(f"Type: {info['type']}")
    print(f"Framework: {info['framework']}")
    print("-" * 60)

    output: Dict[str, Any] = {
        "script": "test_runner",
        "project": str(project_path),
        "type": info["type"],
        "framework": info["framework"],
    }

    if not info["cmd"]:
        reason = info["skip_reason"] or "no test command"
        print(f"SKIPPED ({reason})")
        output.update({"status": "skipped", "timed_out": False, "reason": reason})
        print(json.dumps(output, indent=2))
        return EXIT_SKIPPED

    cmd = info["cmd"]
    coverage = "not requested"
    if args.coverage and info["coverage_cmd"]:
        cmd, coverage = info["coverage_cmd"], "collected"
    elif args.coverage:
        coverage = f"skipped ({info['coverage_skip_reason']})"
    print(f"Running: {' '.join(cmd)}")
    print(f"Time limit: {timeout:g}s")
    if coverage.startswith("skipped"):
        # The suite still runs: a missing coverage tool must not turn passing tests into FAIL.
        print(f"SKIPPED ({info['coverage_skip_reason']})")
    print("-" * 60)

    result = run_tests(cmd, project_path, timeout=timeout, framework=info["framework"])
    lines = strip_ansi(result["output"]).rstrip("\n").split("\n") if result["output"].strip() else []
    if len(lines) > TAIL_LINES:
        print(f"... ({len(lines) - TAIL_LINES} earlier lines omitted; --log FILE keeps the full output)")
    for line in lines[-TAIL_LINES:]:
        print(line)

    log_path: Optional[Path] = args.log.resolve() if args.log else None
    log_error = _write_log(log_path, result["output"]) if log_path else None

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    if result["status"] == "passed":
        print("[PASS] All tests passed")
    elif result["status"] == "skipped":
        print(f"SKIPPED ({result['error']})")
    elif result["status"] == "timeout":
        print(f"[TIMEOUT] Test command {result['error']}")
    else:
        print(f"[FAIL] Some tests failed ({result['error']})")

    if result["tests_run"] > 0:
        print(
            f"Tests: {result['tests_run']} total, {result['tests_passed']} passed, "
            f"{result['tests_failed']} failed"
        )
    if log_path:
        print(f"Log: could not write {log_path}: {log_error}" if log_error else f"Log: {log_path}")

    output.update({
        "command": cmd,
        "status": result["status"],
        "timed_out": result["timed_out"],
        "exit_code": result["exit_code"],
        "duration_seconds": result["duration_seconds"],
        "tests_run": result["tests_run"],
        "tests_passed": result["tests_passed"],
        "tests_failed": result["tests_failed"],
        "counts_parsed": result["counts_parsed"],
        "coverage": coverage,
    })
    if result["status"] != "passed":
        output["reason"] = result["error"]
    if log_path and not log_error:
        output["log"] = str(log_path)
    print("\n" + json.dumps(output, indent=2))
    return {"passed": EXIT_PASS, "skipped": EXIT_SKIPPED}.get(result["status"], EXIT_FAIL)


if __name__ == "__main__":
    raise SystemExit(main())
