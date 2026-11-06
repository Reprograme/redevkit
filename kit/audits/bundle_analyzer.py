#!/usr/bin/env python3
"""Analyze built JavaScript/CSS asset sizes without external dependencies.

Only known build-output roots are scanned, and SKIP_DIRS (node_modules, ...)
is pruned by path segment inside them. Without build output the audit is
SKIPPED: build the project first.
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Sequence

EXIT_PASS, EXIT_FAIL, EXIT_USAGE, EXIT_SKIPPED = 0, 1, 2, 3
SKIP_DIRS = {"node_modules", ".git", ".agents", ".claude", ".codex", ".redevkit", ".venv", "venv", "__pycache__"}
BUILD_ROOTS = (".next/static", "dist", "build/static", "build/assets", "out/_next/static")
SEVERITY = {"none": 99, "low": 1, "medium": 2, "high": 3, "critical": 4}


def utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        except (AttributeError, ValueError, OSError):
            pass


def iter_build_files(build_root: Path):
    """Walk one build root, pruning SKIP_DIRS by segment."""
    for current, dirs, files in os.walk(build_root):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for name in sorted(files):
            yield Path(current) / name


def human_bytes(value: int) -> str:
    units = ("B", "KiB", "MiB", "GiB")
    size = float(value)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{value} B"


def analyze(root: Path, file_warn_kib: int, file_fail_kib: int, total_fail_kib: int) -> dict[str, Any]:
    assets: list[dict[str, Any]] = []
    seen: set[Path] = set()
    for relative in BUILD_ROOTS:
        build_root = root / relative
        if not build_root.is_dir():
            continue
        for path in iter_build_files(build_root):
            if path.suffix.lower() not in {".js", ".mjs", ".css"}:
                continue
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            try:
                data = path.read_bytes()
            except OSError:
                continue
            assets.append({
                "file": path.relative_to(root).as_posix(),
                "type": path.suffix.lower().lstrip("."),
                "bytes": len(data),
                "gzip_bytes": len(gzip.compress(data, compresslevel=6)),
            })

    findings: list[dict[str, Any]] = []
    for asset in assets:
        kib = asset["bytes"] / 1024
        if kib >= file_fail_kib:
            findings.append({"severity": "high", "issue": "Oversized asset", "file": asset["file"], "size": human_bytes(asset["bytes"])})
        elif kib >= file_warn_kib:
            findings.append({"severity": "medium", "issue": "Large asset", "file": asset["file"], "size": human_bytes(asset["bytes"])})

    js_total = sum(a["bytes"] for a in assets if a["type"] in {"js", "mjs"})
    if js_total / 1024 >= total_fail_kib:
        findings.append({"severity": "high", "issue": "Large total JavaScript payload", "file": "<all JS assets>", "size": human_bytes(js_total)})

    assets.sort(key=lambda item: item["bytes"], reverse=True)
    counts = {severity: sum(f["severity"] == severity for f in findings) for severity in ("critical", "high", "medium", "low")}
    return {
        "project": str(root),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "build_roots_checked": [name for name in BUILD_ROOTS if (root / name).is_dir()],
        "asset_count": len(assets),
        "totals": {
            "bytes": sum(a["bytes"] for a in assets),
            "gzip_bytes": sum(a["gzip_bytes"] for a in assets),
            "javascript_bytes": js_total,
            "css_bytes": sum(a["bytes"] for a in assets if a["type"] == "css"),
        },
        "largest_assets": assets[:30],
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
    parser = argparse.ArgumentParser(description="Audit generated JavaScript and CSS bundle sizes")
    parser.add_argument("project", nargs="?", default=".")
    parser.add_argument("--output", choices=["json", "summary"], default="summary")
    parser.add_argument("--file-warn-kib", type=int, default=250)
    parser.add_argument("--file-fail-kib", type=int, default=750)
    parser.add_argument("--total-js-fail-kib", type=int, default=2048)
    parser.add_argument("--fail-on", choices=list(SEVERITY), default="high")
    args = parser.parse_args(argv)
    root = Path(args.project).resolve()
    if not root.is_dir():
        parser.error(f"Project directory does not exist: {root}")
    report = analyze(root, args.file_warn_kib, args.file_fail_kib, args.total_js_fail_kib)
    if not report["build_roots_checked"]:
        reason = "no build output found (" + ", ".join(BUILD_ROOTS) + "); build the project first"
        if args.output == "json":
            report.update({"status": "skipped", "reason": reason})
            print(json.dumps(report, indent=2, ensure_ascii=False))
        else:
            print(f"Bundle Analysis: {root}")
        print(f"SKIPPED ({reason})")
        return EXIT_SKIPPED
    if args.output == "json":
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        totals = report["totals"]
        print(f"Bundle Analysis: {root}")
        print(f"Assets: {report['asset_count']} | Raw: {human_bytes(totals['bytes'])} | Gzip: {human_bytes(totals['gzip_bytes'])}")
        for asset in report["largest_assets"][:10]:
            print(f"{human_bytes(asset['bytes']):>10} ({human_bytes(asset['gzip_bytes'])} gzip)  {asset['file']}")
        for finding in report["findings"]:
            print(f"[{finding['severity'].upper()}] {finding['issue']}: {finding['file']} ({finding['size']})")
    return EXIT_FAIL if should_fail(report, args.fail_on) else EXIT_PASS


if __name__ == "__main__":
    raise SystemExit(main())
