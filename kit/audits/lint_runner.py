#!/usr/bin/env python3
"""
Lint Runner - Unified linting and type checking.
Runs the linters that apply to the project type.

Usage:
    python lint_runner.py <project_path>

Supports:
    - Node.js: npm run lint, eslint, tsc --noEmit (project-local binaries only)
    - Python: ruff check, mypy (PATH executable or module of the current interpreter)

A linter that is not installed is SKIPPED, never FAIL and never PASS. When
every linter is skipped the script exits 3 (SKIPPED).
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

EXIT_PASS, EXIT_FAIL, EXIT_USAGE, EXIT_SKIPPED = 0, 1, 2, 3
TIMEOUT_SECONDS = 120


def utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        except (AttributeError, ValueError, OSError):
            pass


def which(name: str) -> Optional[str]:
    return shutil.which(name)


def local_bin(project_path: Path, name: str) -> Optional[str]:
    folder = project_path / "node_modules" / ".bin"
    if not folder.is_dir():
        return None
    return shutil.which(name, path=str(folder))


def python_tool(name: str) -> Optional[List[str]]:
    """Resolve a Python tool: executable on PATH, else ``sys.executable -m <name>``."""
    executable = which(name)
    if executable:
        return [executable]
    try:
        if importlib.util.find_spec(name) is not None:
            return [sys.executable, "-m", name]
    except (ImportError, ValueError):
        pass
    return None


def _linter(name: str, cmd: Optional[List[str]], args: List[str], missing: str) -> Dict[str, Any]:
    if cmd is None:
        return {"name": name, "cmd": None, "skip_reason": missing}
    return {"name": name, "cmd": cmd + args, "skip_reason": None}


def detect_project_type(project_path: Path) -> Dict[str, Any]:
    """Detect project type and the linters that apply."""
    result: Dict[str, Any] = {"type": "unknown", "linters": []}

    package_json = project_path / "package.json"
    if package_json.exists():
        result["type"] = "node"
        try:
            pkg = json.loads(package_json.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pkg = {}
        scripts = pkg.get("scripts", {}) if isinstance(pkg, dict) else {}
        deps: Dict[str, Any] = {}
        if isinstance(pkg, dict):
            deps.update(pkg.get("dependencies", {}) or {})
            deps.update(pkg.get("devDependencies", {}) or {})

        if isinstance(scripts, dict) and "lint" in scripts:
            npm = which("npm")
            result["linters"].append(
                _linter("npm lint", [npm] if npm else None, ["run", "lint"], "npm not found on PATH")
            )
        elif "eslint" in deps:
            eslint = local_bin(project_path, "eslint")
            result["linters"].append(
                _linter("eslint", [eslint] if eslint else None, ["."],
                        "eslint is not installed in node_modules/.bin")
            )

        if "typescript" in deps or (project_path / "tsconfig.json").exists():
            tsc = local_bin(project_path, "tsc")
            result["linters"].append(
                _linter("tsc", [tsc] if tsc else None, ["--noEmit"],
                        "tsc is not installed in node_modules/.bin")
            )

    python_markers = ("pyproject.toml", "requirements.txt", "setup.py", "setup.cfg")
    if any((project_path / name).exists() for name in python_markers):
        result["type"] = "python" if result["type"] == "unknown" else f"{result['type']}+python"
        result["linters"].append(_linter("ruff", python_tool("ruff"), ["check", "."], "ruff is not installed"))
        if (project_path / "mypy.ini").exists() or (project_path / "pyproject.toml").exists():
            result["linters"].append(_linter("mypy", python_tool("mypy"), ["."], "mypy is not installed"))

    return result


def run_linter(linter: Dict[str, Any], cwd: Path) -> Dict[str, Any]:
    """Run one linter. ``status`` is passed, failed or skipped."""
    result: Dict[str, Any] = {"name": linter["name"], "status": "skipped", "output": "", "error": ""}
    if not linter.get("cmd"):
        result["error"] = linter.get("skip_reason") or "not available"
        return result
    try:
        proc = subprocess.run(
            linter["cmd"],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=TIMEOUT_SECONDS,
            check=False,
        )
    except FileNotFoundError:
        result["error"] = f"command not found: {linter['cmd'][0]}"
        return result
    except subprocess.TimeoutExpired:
        result["status"] = "failed"
        result["error"] = f"timeout after {TIMEOUT_SECONDS}s"
        return result
    except OSError as exc:
        result["error"] = f"could not start {linter['cmd'][0]}: {exc}"
        return result

    result["output"] = (proc.stdout or "")[:2000]
    result["error"] = (proc.stderr or "")[:500]
    result["status"] = "passed" if proc.returncode == 0 else "failed"
    return result


def main(argv: Optional[Sequence[str]] = None) -> int:
    utf8_stdio()
    parser = argparse.ArgumentParser(description="Run the project's linters and type checkers")
    parser.add_argument("project", nargs="?", default=".")
    args = parser.parse_args(argv)
    project_path = Path(args.project).resolve()
    if not project_path.is_dir():
        print(json.dumps({"error": f"Directory not found: {project_path}"}))
        return EXIT_USAGE

    print(f"\n{'=' * 60}")
    print("[LINT RUNNER] Unified Linting")
    print(f"{'=' * 60}")
    print(f"Project: {project_path}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    info = detect_project_type(project_path)
    print(f"Type: {info['type']}")
    print(f"Linters: {len(info['linters'])}")
    print("-" * 60)

    if not info["linters"]:
        reason = "no linters apply to this project type"
        print(f"SKIPPED ({reason})")
        print(json.dumps({"script": "lint_runner", "project": str(project_path), "type": info["type"],
                          "checks": [], "status": "skipped", "reason": reason}, indent=2))
        return EXIT_SKIPPED

    results = []
    for linter in info["linters"]:
        print(f"\nRunning: {linter['name']}...")
        result = run_linter(linter, project_path)
        results.append(result)
        if result["status"] == "passed":
            print(f"  [PASS] {linter['name']}")
        elif result["status"] == "skipped":
            print(f"  [SKIP] {linter['name']}: SKIPPED ({result['error']})")
        else:
            print(f"  [FAIL] {linter['name']}")
            if result["error"]:
                print(f"  Error: {result['error'][:200]}")

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for r in results:
        if r["status"] == "skipped":
            print(f"[SKIP] {r['name']} - SKIPPED ({r['error']})")
        else:
            print(f"[{'PASS' if r['status'] == 'passed' else 'FAIL'}] {r['name']}")

    failed = [r for r in results if r["status"] == "failed"]
    ran = [r for r in results if r["status"] != "skipped"]
    status = "failed" if failed else ("passed" if ran else "skipped")
    if status == "skipped":
        print("SKIPPED (no linter could run)")
    print("\n" + json.dumps({"script": "lint_runner", "project": str(project_path), "type": info["type"],
                             "checks": results, "status": status}, indent=2))
    return {"passed": EXIT_PASS, "skipped": EXIT_SKIPPED}.get(status, EXIT_FAIL)


if __name__ == "__main__":
    raise SystemExit(main())
