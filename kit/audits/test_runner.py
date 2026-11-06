#!/usr/bin/env python3
"""
Test Runner - Unified test execution and coverage reporting.
Runs the project's tests based on project type.

Usage:
    python test_runner.py <project_path> [--coverage]

Supports:
    - Node.js: npm test, jest, vitest (project-local binaries only, no downloads)
    - Python: pytest, unittest (always through the current interpreter)

Executables are resolved with shutil.which (npm resolves to npm.cmd on
Windows) and Python is invoked through sys.executable. When a runner is not
available the result is SKIPPED (exit 3), never PASS.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

EXIT_PASS, EXIT_FAIL, EXIT_USAGE, EXIT_SKIPPED = 0, 1, 2, 3
TIMEOUT_SECONDS = 300
NO_TESTS_EXIT_CODES = {5}  # pytest "no tests collected", unittest "NO TESTS RAN" (3.12+)


def utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        except (AttributeError, ValueError, OSError):
            pass


def which(name: str) -> Optional[str]:
    """Resolve an executable on PATH (``npm`` -> ``npm.cmd`` on Windows)."""
    return shutil.which(name)


def local_bin(project_path: Path, name: str) -> Optional[str]:
    """Project-local node_modules/.bin executable; never downloads with npx."""
    folder = project_path / "node_modules" / ".bin"
    if not folder.is_dir():
        return None
    return shutil.which(name, path=str(folder))


def python_module_available(module: str) -> bool:
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


def detect_test_framework(project_path: Path) -> Dict[str, Any]:
    """Detect the test command. ``cmd`` is None and ``skip_reason`` set when it cannot run."""
    result: Dict[str, Any] = {
        "type": "unknown",
        "framework": None,
        "cmd": None,
        "coverage_cmd": None,
        "skip_reason": "no test framework detected",
    }

    package_json = project_path / "package.json"
    if package_json.exists():
        result["type"] = "node"
        try:
            pkg = json.loads(package_json.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            pkg = {}
            result["skip_reason"] = f"package.json could not be read: {exc}"
        scripts = pkg.get("scripts", {}) if isinstance(pkg, dict) else {}
        deps: Dict[str, Any] = {}
        if isinstance(pkg, dict):
            deps.update(pkg.get("dependencies", {}) or {})
            deps.update(pkg.get("devDependencies", {}) or {})

        coverage_cmd = None
        framework = None
        if "vitest" in deps:
            framework = "vitest"
            vitest = local_bin(project_path, "vitest")
            coverage_cmd = [vitest, "run", "--coverage"] if vitest else None
        elif "jest" in deps:
            framework = "jest"
            jest = local_bin(project_path, "jest")
            coverage_cmd = [jest, "--coverage"] if jest else None

        if isinstance(scripts, dict) and "test" in scripts:
            npm = which("npm")
            result["framework"] = framework or "npm test"
            if npm:
                result["cmd"] = [npm, "test"]
                result["coverage_cmd"] = coverage_cmd
                result["skip_reason"] = None
            else:
                result["skip_reason"] = "npm not found on PATH"
            return result
        if framework:
            result["framework"] = framework
            binary = local_bin(project_path, framework)
            if binary:
                result["cmd"] = [binary, "run"] if framework == "vitest" else [binary]
                result["coverage_cmd"] = coverage_cmd
                result["skip_reason"] = None
            else:
                result["skip_reason"] = f"{framework} is not installed in node_modules/.bin (run the package install first)"
            return result

    if _python_project(project_path):
        result["type"] = "python"
        if python_module_available("pytest"):
            result["framework"] = "pytest"
            result["cmd"] = [sys.executable, "-m", "pytest", "-v"]
            result["coverage_cmd"] = [sys.executable, "-m", "pytest", "--cov", "--cov-report=term-missing"]
            result["skip_reason"] = None
        elif _pytest_configured(project_path):
            result["framework"] = "pytest"
            result["skip_reason"] = f"pytest is not installed for {sys.executable}"
        else:
            result["framework"] = "unittest"
            result["cmd"] = [sys.executable, "-m", "unittest", "discover", "-v"]
            result["skip_reason"] = None
    return result


def _parse_counts(output: str, result: Dict[str, Any]) -> None:
    # Vitest and Jest print a file/suite summary ("Test Files  3 passed", "Test Suites: 3 passed")
    # before the test summary ("Tests  22 passed"): count tests, not files.
    tests_line = re.search(r"^\s*Tests:?\s+(.*)$", output, re.MULTILINE)
    scope = tests_line.group(1) if tests_line else output
    passed = re.search(r"(\d+)\s+passed", scope, re.IGNORECASE)
    failed = re.search(r"(\d+)\s+failed", scope, re.IGNORECASE)
    if passed:
        result["tests_passed"] = int(passed.group(1))
    if failed:
        result["tests_failed"] = int(failed.group(1))
    ran = re.search(r"^Ran (\d+) tests?", output, re.MULTILINE)
    if ran:
        result["tests_run"] = int(ran.group(1))
    else:
        result["tests_run"] = result["tests_passed"] + result["tests_failed"]


def run_tests(cmd: List[str], cwd: Path) -> Dict[str, Any]:
    """Run tests and return results. ``status`` is passed, failed or skipped."""
    result: Dict[str, Any] = {
        "status": "failed",
        "output": "",
        "error": "",
        "tests_run": 0,
        "tests_passed": 0,
        "tests_failed": 0,
    }
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=TIMEOUT_SECONDS,
            check=False,
        )
    except FileNotFoundError:
        result["status"] = "skipped"
        result["error"] = f"command not found: {cmd[0]}"
        return result
    except subprocess.TimeoutExpired:
        result["status"] = "failed"
        result["error"] = f"timeout after {TIMEOUT_SECONDS}s"
        return result
    except OSError as exc:
        result["status"] = "skipped"
        result["error"] = f"could not start {cmd[0]}: {exc}"
        return result

    combined = (proc.stdout or "") + "\n" + (proc.stderr or "")
    result["output"] = (proc.stdout or "")[:3000]
    result["error"] = (proc.stderr or "")[-1500:]
    _parse_counts(combined, result)
    if proc.returncode == 0:
        result["status"] = "passed"
    elif proc.returncode in NO_TESTS_EXIT_CODES and result["tests_failed"] == 0:
        result["status"] = "skipped"
        result["error"] = "no tests found"
    else:
        result["status"] = "failed"
    return result


def main(argv: Optional[Sequence[str]] = None) -> int:
    utf8_stdio()
    parser = argparse.ArgumentParser(description="Run the project's test suite")
    parser.add_argument("project", nargs="?", default=".")
    parser.add_argument("--coverage", action="store_true", help="Run with coverage when supported")
    args = parser.parse_args(argv)

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
        output.update({"status": "skipped", "reason": reason})
        print(json.dumps(output, indent=2))
        return EXIT_SKIPPED

    cmd = info["coverage_cmd"] if args.coverage and info["coverage_cmd"] else info["cmd"]
    print(f"Running: {' '.join(cmd)}")
    print("-" * 60)

    result = run_tests(cmd, project_path)
    if result["output"]:
        lines = result["output"].split("\n")
        for line in lines[:30]:
            print(line)
        if len(lines) > 30:
            print(f"... ({len(lines) - 30} more lines)")

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    if result["status"] == "passed":
        print("[PASS] All tests passed")
    elif result["status"] == "skipped":
        print(f"SKIPPED ({result['error']})")
    else:
        print("[FAIL] Some tests failed")
        if result["error"]:
            print(f"Error: {result['error'][-400:]}")

    if result["tests_run"] > 0:
        print(
            f"Tests: {result['tests_run']} total, {result['tests_passed']} passed, "
            f"{result['tests_failed']} failed"
        )

    output.update({
        "command": cmd,
        "status": result["status"],
        "tests_run": result["tests_run"],
        "tests_passed": result["tests_passed"],
        "tests_failed": result["tests_failed"],
    })
    print("\n" + json.dumps(output, indent=2))
    return {"passed": EXIT_PASS, "skipped": EXIT_SKIPPED}.get(result["status"], EXIT_FAIL)


if __name__ == "__main__":
    raise SystemExit(main())
