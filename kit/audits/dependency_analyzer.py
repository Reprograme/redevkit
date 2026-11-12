#!/usr/bin/env python3
"""Offline dependency hygiene analyzer for common package ecosystems.

Manifests are found with one directory walk under the shared exclusion policy
(``audit_common.PathFilter``; node_modules is never entered). A package.json
without dependencies needs no lock file, and a workspace package is covered by
a lock file in any parent directory inside the project. With no manifest the
audit is SKIPPED.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Sequence

sys.dont_write_bytecode = True  # importing the shared helper must not leave __pycache__ behind
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_common import PathFilter, add_exclusion_arguments, path_filter_from_args  # noqa: E402

EXIT_PASS, EXIT_FAIL, EXIT_USAGE, EXIT_SKIPPED = 0, 1, 2, 3
SEVERITY = {"none": 99, "low": 1, "medium": 2, "high": 3, "critical": 4}
JS_LOCK_FILES = ("package-lock.json", "npm-shrinkwrap.json", "yarn.lock", "pnpm-lock.yaml", "bun.lock", "bun.lockb")


def utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)  # type: ignore[union-attr]
        except (AttributeError, ValueError, OSError):
            pass


def iter_named_files(root: Path, names: set, path_filter: Optional[PathFilter] = None):
    path_filter = path_filter if path_filter is not None else PathFilter(root)
    for path in path_filter.walk(root):
        if path.name in names:
            yield path


def _lock_files(package_dir: Path, root: Path) -> list[str]:
    """Lock files next to the manifest, else in the nearest parent inside the project (workspaces)."""
    folder = package_dir
    while True:
        locks = [name for name in JS_LOCK_FILES if (folder / name).exists()]
        if locks or folder == root or root not in folder.parents:
            return locks
        folder = folder.parent


def add(findings: list[dict[str, Any]], severity: str, issue: str, path: Path, detail: str) -> None:
    findings.append({"severity": severity, "issue": issue, "file": path.as_posix(), "detail": detail})


def analyze_package_json(path: Path, root: Path, findings: list[dict[str, Any]]) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text("utf-8-sig"))  # npm accepts a UTF-8 BOM
    except (OSError, ValueError) as exc:  # ValueError: invalid JSON or invalid UTF-8
        add(findings, "high", "Invalid package.json", path.relative_to(root), str(exc))
        return {"file": path.relative_to(root).as_posix(), "dependencies": 0}
    if not isinstance(data, dict):
        add(findings, "high", "Invalid package.json", path.relative_to(root), "top-level value is not an object")
        return {"file": path.relative_to(root).as_posix(), "dependencies": 0}

    deps: dict[str, str] = {}
    for section in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
        values = data.get(section, {})
        if isinstance(values, dict):
            deps.update({str(k): str(v) for k, v in values.items()})

    for name, spec in deps.items():
        normalized = spec.strip().lower()
        if normalized in {"*", "latest", "next"}:
            add(findings, "high", "Unbounded dependency version", path.relative_to(root), f"{name}: {spec}")
        elif normalized.startswith(("http://", "https://", "git://", "git+http://")):
            add(findings, "high", "Dependency fetched from mutable remote", path.relative_to(root), f"{name}: {spec}")
        elif normalized.startswith("github:") and "#" not in normalized:
            add(findings, "medium", "GitHub dependency is not pinned to a ref", path.relative_to(root), f"{name}: {spec}")

    locks = _lock_files(path.parent, root)
    if deps and not locks:  # a manifest without dependencies has nothing to lock
        add(findings, "high", "Missing JavaScript lock file", path.relative_to(root), "Add and commit one package-manager lock file.")
    elif len(locks) > 1:
        add(findings, "medium", "Multiple JavaScript lock files", path.relative_to(root), ", ".join(locks))
    return {"file": path.relative_to(root).as_posix(), "dependencies": len(deps), "lock_files": locks}


def analyze_requirements(path: Path, root: Path, findings: list[dict[str, Any]]) -> dict[str, Any]:
    unpinned = []
    total = 0
    try:
        lines = path.read_text("utf-8-sig", errors="replace").splitlines()
    except OSError as exc:
        add(findings, "high", "Unreadable requirements file", path.relative_to(root), str(exc))
        return {"file": path.relative_to(root).as_posix(), "dependencies": 0}
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith(("#", "-r", "--", "-e")):
            continue
        total += 1
        if " @ " in line or re.search(r"===|==", line):
            continue
        if re.match(r"^[A-Za-z0-9_.-]+(?:\[[^]]+\])?\s*(?:$|[<>!~]=?)", line):
            unpinned.append(line)
    for spec in unpinned[:25]:
        add(findings, "medium", "Python dependency is not exactly pinned", path.relative_to(root), spec)
    return {"file": path.relative_to(root).as_posix(), "dependencies": total, "unpinned": len(unpinned)}


def analyze(root: Path, path_filter: Optional[PathFilter] = None) -> dict[str, Any]:
    root = root.resolve()
    path_filter = path_filter if path_filter is not None else PathFilter(root)
    findings: list[dict[str, Any]] = []
    manifests: list[dict[str, Any]] = []
    other_manifests = 0
    named = list(iter_named_files(root, {
        "package.json", "requirements.txt", "requirements-dev.txt", "requirements-prod.txt",
        "Cargo.toml", "Gemfile", "go.mod", "Pipfile", "pyproject.toml",
    }, path_filter))
    for path in (p for p in named if p.name == "package.json"):
        manifests.append(analyze_package_json(path, root, findings))
    for path in (p for p in named if p.name.startswith("requirements")):
        manifests.append(analyze_requirements(path, root, findings))

    # Lightweight presence checks for other ecosystems.
    for manifest, locks, ecosystem in (
        ("Cargo.toml", ("Cargo.lock",), "Rust"),
        ("Gemfile", ("Gemfile.lock",), "Ruby"),
        ("go.mod", ("go.sum",), "Go"),
        ("Pipfile", ("Pipfile.lock",), "Python/Pipenv"),
        ("pyproject.toml", ("poetry.lock", "uv.lock", "requirements.txt"), "Python"),
    ):
        for path in (p for p in named if p.name == manifest):
            other_manifests += 1
            present = [name for name in locks if (path.parent / name).exists()]
            if not present:
                add(findings, "medium", f"No recognized {ecosystem} lock/resolution file", path.relative_to(root), f"Expected one of: {', '.join(locks)}")

    counts = {severity: sum(f["severity"] == severity for f in findings) for severity in ("critical", "high", "medium", "low")}
    return {
        "project": str(root),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "manifests": manifests,
        "manifest_count": len(manifests) + other_manifests,
        "findings": findings,
        "summary": {"total": len(findings), **counts},
    }


def should_fail(report: dict[str, Any], threshold: str) -> bool:
    if threshold == "none":
        return False
    rank = SEVERITY[threshold]
    return any(report["summary"].get(level, 0) and value >= rank for level, value in SEVERITY.items() if level != "none")


def main(argv: Optional[Sequence[str]] = None) -> int:
    utf8_stdio()
    parser = argparse.ArgumentParser(description="Analyze dependency pinning and lock-file hygiene without network access")
    parser.add_argument("project", nargs="?", default=".")
    parser.add_argument("--output", choices=["json", "summary"], default="summary")
    parser.add_argument("--fail-on", choices=list(SEVERITY), default="high")
    add_exclusion_arguments(parser)
    args = parser.parse_args(argv)
    root = Path(args.project).resolve()
    if not root.is_dir():
        parser.error(f"Project directory does not exist: {root}")
    report = analyze(root, path_filter_from_args(root, args))
    if not report["manifest_count"]:
        print(f"Dependency Analysis: {root}")
        print("SKIPPED (no dependency manifest found)")
        return EXIT_SKIPPED
    if args.output == "json":
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        s = report["summary"]
        print(f"Dependency Analysis: {root}")
        print(f"Findings: {s['total']} (critical={s['critical']}, high={s['high']}, medium={s['medium']}, low={s['low']})")
        for finding in report["findings"][:20]:
            print(f"[{finding['severity'].upper()}] {finding['file']}: {finding['issue']} - {finding['detail']}")
        if not report["findings"]:
            print("[PASS] No dependency hygiene issues detected.")
    return EXIT_FAIL if should_fail(report, args.fail_on) else EXIT_PASS


if __name__ == "__main__":
    raise SystemExit(main())
