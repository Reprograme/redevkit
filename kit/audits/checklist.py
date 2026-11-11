#!/usr/bin/env python3
"""Run the fast REDEVKIT validation checklist.

Usage:
    python checklist.py [project] [--url URL] [--no-runtime] [--no-tests] [--stop-on-fail]
                        [--report FILE] [--exclude PATTERN ...] [--no-gitignore]
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional, Sequence

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

from validation_runner import CheckSpec, run_suite  # noqa: E402

CORE_CHECKS = (
    CheckSpec(
        "Security Scan",
        "security_scan.py",
        "P0 Security",
        required=True,
        args=("--output", "summary", "--fail-on", "high"),
        excludes=True,
    ),
    CheckSpec("Lint Check", "lint_runner.py", "P1 Code Quality", required=True),
    CheckSpec("Type Coverage", "type_coverage.py", "P1 Code Quality", excludes=True),
    CheckSpec("Schema Validation", "schema_validator.py", "P2 Data Layer", excludes=True),
    CheckSpec("Test Runner", "test_runner.py", "P3 Testing", tests=True),
    CheckSpec("UX Audit", "ux_audit.py", "P4 UX & Accessibility", excludes=True),
    CheckSpec("Accessibility Check", "accessibility_checker.py", "P4 UX & Accessibility", excludes=True),
    CheckSpec("SEO Check", "seo_checker.py", "P5 SEO", excludes=True),
)

URL_CHECKS = (
    CheckSpec("Lighthouse Audit", "lighthouse_audit.py", "P6 Runtime Checks", target="url", required=True, timeout=180),
    CheckSpec("Playwright Smoke Test", "playwright_runner.py", "P6 Runtime Checks", target="url", timeout=120),
)

SUITE = CORE_CHECKS + URL_CHECKS


def main(argv: Optional[Sequence[str]] = None) -> int:
    return run_suite(
        "REDEVKIT - FAST CHECKLIST",
        "CHECKLIST SUMMARY",
        "Run the fast REDEVKIT validation checklist",
        SUITE,
        argv,
    )


if __name__ == "__main__":
    raise SystemExit(main())
