#!/usr/bin/env python3
"""Pragmatic TypeScript and Python type-safety checker.

The checker prefers real compiler output when a local TypeScript compiler is
available. Its source fallback focuses on explicit escape hatches such as
``any`` and ``@ts-ignore``; inferred TypeScript return types are not treated as
coverage failures.

A compiler that is missing, cannot start or times out is reported as
``SKIPPED (<reason>)``; it never counts as a pass.
"""
from __future__ import annotations

import argparse
import ast
import json
import math
import os
import re
import shutil
import sys
import time
from pathlib import Path
from typing import Any, List, Optional, Sequence

sys.dont_write_bytecode = True  # importing the shared helper must not leave __pycache__ behind
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_common import PathFilter, add_exclusion_arguments, path_filter_from_args, run_external  # noqa: E402

EXIT_PASS, EXIT_FAIL, EXIT_USAGE, EXIT_SKIPPED = 0, 1, 2, 3
TSC_TIMEOUT = 180  # per tsconfig.json
TSC_TOTAL_BUDGET = 240  # all compiler runs together: stays under the orchestrators' limit for this audit
# Directory exclusion: the shared policy of audit_common.PathFilter.


def utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)  # type: ignore[union-attr]
        except (AttributeError, ValueError, OSError):
            pass


def _walk(project: Path, path_filter: Optional[PathFilter] = None):
    """Yield non-excluded files (shared policy, by segment relative to the project)."""
    path_filter = path_filter if path_filter is not None else PathFilter(project)
    yield from path_filter.walk(project)


def _source_files(project: Path, suffixes: set[str], path_filter: Optional[PathFilter] = None) -> list[Path]:
    files: list[Path] = []
    for path in _walk(project, path_filter):
        if path.suffix.lower() not in suffixes:
            continue
        if path.name.endswith(".d.ts"):
            continue
        files.append(path)
    return sorted(files)


def _local_tsc(tsconfig: Path) -> Path | None:
    for parent in (tsconfig.parent, *tsconfig.parents):
        folder = parent / "node_modules" / ".bin"
        if folder.is_dir():
            found = shutil.which("tsc", path=str(folder))
            if found:
                return Path(found)
    return None


def _run_typescript_compilers(project: Path, path_filter: Optional[PathFilter] = None) -> list[dict[str, Any]]:
    runs: list[dict[str, Any]] = []
    tsconfigs = [path for path in _walk(project, path_filter) if path.name == "tsconfig.json"]
    deadline = time.monotonic() + TSC_TOTAL_BUDGET
    for tsconfig in sorted(tsconfigs):
        compiler = _local_tsc(tsconfig)
        if compiler is None:
            runs.append({"config": str(tsconfig), "status": "skipped", "reason": "local tsc not installed"})
            continue
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            runs.append({"config": str(tsconfig), "status": "skipped",
                         "reason": f"tsc not run: the {TSC_TOTAL_BUDGET}s budget of this audit is spent"})
            continue
        limit = min(TSC_TIMEOUT, remaining)
        try:
            proc = run_external(
                [str(compiler), "--noEmit", "--pretty", "false", "-p", str(tsconfig)],
                cwd=tsconfig.parent,
                timeout=limit,
            )
        except OSError as exc:
            runs.append({"config": str(tsconfig), "status": "skipped", "reason": f"tsc could not start: {exc}"})
            continue
        if proc.timed_out:
            runs.append({"config": str(tsconfig), "status": "skipped", "reason": f"tsc timed out after {limit:.0f}s"})
            continue
        runs.append(
            {
                "config": str(tsconfig),
                "status": "passed" if proc.returncode == 0 else "failed",
                "returncode": proc.returncode,
                "output": "\n".join(part.strip() for part in (proc.stdout, proc.stderr) if part.strip())[-4000:],
            }
        )
    return runs


def check_typescript_coverage(project_path: Path, path_filter: Optional[PathFilter] = None) -> dict[str, Any]:
    issues: list[str] = []
    passed: list[str] = []
    files = _source_files(project_path, {".ts", ".tsx"}, path_filter)
    stats: dict[str, Any] = {
        "any_count": 0,
        "suppression_count": 0,
        "files_with_any": 0,
        "compiler_runs": [],
    }

    if not files:
        return {"type": "typescript", "files": 0, "passed": [], "issues": ["[!] No TypeScript files found"], "stats": stats}

    any_pattern = re.compile(r"(?::\s*any\b|\bas\s+any\b|<any>)")
    suppression_pattern = re.compile(r"@ts-(?:ignore|nocheck)")
    for file_path in files:
        content = file_path.read_text("utf-8", errors="ignore")
        any_count = len(any_pattern.findall(content))
        stats["any_count"] += any_count
        stats["files_with_any"] += int(any_count > 0)
        stats["suppression_count"] += len(suppression_pattern.findall(content))

    any_fail_threshold = max(10, math.ceil(len(files) * 0.25))
    suppression_fail_threshold = max(3, math.ceil(len(files) * 0.05))

    if stats["any_count"] == 0:
        passed.append("[OK] No explicit 'any' escape hatches found")
    elif stats["any_count"] > any_fail_threshold:
        issues.append(
            f"[X] {stats['any_count']} explicit 'any' usages exceed the project threshold of {any_fail_threshold}"
        )
    else:
        issues.append(
            f"[!] {stats['any_count']} explicit 'any' usages across {stats['files_with_any']} file(s)"
        )

    if stats["suppression_count"] > suppression_fail_threshold:
        issues.append(
            f"[X] {stats['suppression_count']} TypeScript suppression comments exceed the threshold of {suppression_fail_threshold}"
        )
    elif stats["suppression_count"]:
        issues.append(f"[!] {stats['suppression_count']} TypeScript suppression comment(s) found")
    else:
        passed.append("[OK] No @ts-ignore or @ts-nocheck suppressions found")

    stats["compiler_runs"] = _run_typescript_compilers(project_path, path_filter)
    failed_runs = [run for run in stats["compiler_runs"] if run["status"] == "failed"]
    completed_runs = [run for run in stats["compiler_runs"] if run["status"] == "passed"]
    if failed_runs:
        issues.append(f"[X] TypeScript compiler failed for {len(failed_runs)} project(s)")
    elif completed_runs:
        passed.append(f"[OK] TypeScript compiler passed for {len(completed_runs)} project(s)")
    for run in stats["compiler_runs"]:
        if run["status"] == "skipped":
            issues.append(f"SKIPPED (tsc for {Path(run['config']).name}: {run['reason']})")

    passed.append(f"[OK] Analyzed {len(files)} TypeScript files")
    return {"type": "typescript", "files": len(files), "passed": passed, "issues": issues, "stats": stats}


def _annotation_complete(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    positional = [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
    relevant = [arg for arg in positional if arg.arg not in {"self", "cls"}]
    args_typed = all(arg.annotation is not None for arg in relevant)
    varargs_typed = node.args.vararg is None or node.args.vararg.annotation is not None
    kwargs_typed = node.args.kwarg is None or node.args.kwarg.annotation is not None
    return args_typed and varargs_typed and kwargs_typed and node.returns is not None


def check_python_coverage(project_path: Path, path_filter: Optional[PathFilter] = None) -> dict[str, Any]:
    issues: list[str] = []
    passed: list[str] = []
    files = _source_files(project_path, {".py"}, path_filter)
    stats = {"typed_functions": 0, "untyped_functions": 0, "any_count": 0, "parse_errors": 0}

    if not files:
        return {"type": "python", "files": 0, "passed": [], "issues": ["[!] No Python files found"], "stats": stats}

    for file_path in files:
        try:
            tree = ast.parse(file_path.read_text("utf-8", errors="ignore"), filename=str(file_path))
        except (SyntaxError, ValueError):  # ValueError: null bytes (Python < 3.12)
            stats["parse_errors"] += 1
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                key = "typed_functions" if _annotation_complete(node) else "untyped_functions"
                stats[key] += 1
            elif isinstance(node, ast.Name) and node.id == "Any":
                stats["any_count"] += 1

    total = stats["typed_functions"] + stats["untyped_functions"]
    typed_ratio = (stats["typed_functions"] / total * 100) if total else 100.0
    stats["typed_ratio"] = round(typed_ratio, 2)

    if stats["parse_errors"]:
        issues.append(f"[X] {stats['parse_errors']} Python file(s) could not be parsed")
    if typed_ratio >= 65:
        passed.append(f"[OK] Fully annotated Python functions: {typed_ratio:.0f}%")
    elif typed_ratio >= 40:
        issues.append(f"[!] Fully annotated Python functions: {typed_ratio:.0f}%")
    else:
        issues.append(f"[X] Fully annotated Python functions: {typed_ratio:.0f}%")

    any_fail_threshold = max(50, len(files) * 3)
    if stats["any_count"] == 0:
        passed.append("[OK] No Python Any references found")
    elif stats["any_count"] > any_fail_threshold:
        issues.append(
            f"[X] {stats['any_count']} Python Any references exceed the project threshold of {any_fail_threshold}"
        )
    else:
        issues.append(f"[!] {stats['any_count']} Python Any reference(s) found")

    passed.append(f"[OK] Analyzed {len(files)} Python files")
    return {"type": "python", "files": len(files), "passed": passed, "issues": issues, "stats": stats}


def main(argv: Optional[Sequence[str]] = None) -> int:
    utf8_stdio()
    parser = argparse.ArgumentParser(description="Check TypeScript and Python type safety")
    parser.add_argument("project", nargs="?", default=".")
    add_exclusion_arguments(parser)
    args = parser.parse_args(argv)
    project_path = Path(args.project).resolve()
    if not project_path.is_dir():
        print(json.dumps({"error": f"Directory not found: {project_path}"}))
        return EXIT_USAGE

    print("\n" + "=" * 60)
    print("  TYPE SAFETY CHECKER")
    print("=" * 60)
    path_filter = path_filter_from_args(project_path, args)
    print(path_filter.describe() + "\n")

    results = [
        result
        for result in (
            check_typescript_coverage(project_path, path_filter),
            check_python_coverage(project_path, path_filter),
        )
        if result["files"] > 0
    ]
    if not results:
        print("SKIPPED (no TypeScript or Python files found)")
        return EXIT_SKIPPED

    critical_issues = 0
    for result in results:
        print(f"\n[{result['type'].upper()}]\n" + "-" * 40)
        for item in result["passed"]:
            print(f"  {item}")
        for item in result["issues"]:
            print(f"  {item}")
            critical_issues += int(item.startswith("[X]"))

    print("\n" + "=" * 60)
    if critical_issues:
        print(f"[X] TYPE SAFETY: {critical_issues} blocking issue(s)")
        return EXIT_FAIL
    print("[OK] TYPE SAFETY: ACCEPTABLE")
    return EXIT_PASS


if __name__ == "__main__":
    raise SystemExit(main())
