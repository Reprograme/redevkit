#!/usr/bin/env python3
"""Run the complete REDEVKIT verification suite.

Usage:
    python verify_all.py [project] [--url URL] [--no-runtime] [--no-tests] [--stop-on-fail]
                         [--report FILE] [--exclude PATTERN ...] [--no-gitignore]
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional, Sequence

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

from validation_runner import CheckSpec, run_suite  # noqa: E402

VERIFICATION_SUITE = (
    CheckSpec(
        "Security Scan",
        "security_scan.py",
        "P0 Security",
        required=True,
        args=("--output", "summary", "--fail-on", "high"),
        excludes=True,
    ),
    CheckSpec("Dependency Analysis", "dependency_analyzer.py", "P0 Security", excludes=True),
    CheckSpec("Lint Check", "lint_runner.py", "P1 Code Quality", required=True),
    CheckSpec("Type Coverage", "type_coverage.py", "P1 Code Quality", excludes=True),
    CheckSpec("Schema Validation", "schema_validator.py", "P2 Data Layer", excludes=True),
    CheckSpec("Test Suite", "test_runner.py", "P3 Testing", tests=True),
    CheckSpec("UX Audit", "ux_audit.py", "P4 UX & Accessibility", excludes=True),
    CheckSpec("Accessibility Check", "accessibility_checker.py", "P4 UX & Accessibility", excludes=True),
    CheckSpec("SEO Check", "seo_checker.py", "P5 SEO & Content", excludes=True),
    CheckSpec("GEO Check", "geo_checker.py", "P5 SEO & Content", excludes=True),
    CheckSpec("Bundle Analysis", "bundle_analyzer.py", "P6 Build Performance", excludes=True),
    CheckSpec("React Performance", "react_performance_checker.py", "P6 Build Performance", excludes=True),
    CheckSpec("Mobile Audit", "mobile_audit.py", "P7 Platform Quality", excludes=True),
    CheckSpec("i18n Check", "i18n_checker.py", "P7 Platform Quality", excludes=True),
    CheckSpec("API Validation", "api_validator.py", "P7 Platform Quality", excludes=True),
    CheckSpec("Lighthouse Audit", "lighthouse_audit.py", "P8 Runtime", target="url", required=True, timeout=180),
    CheckSpec("Playwright E2E", "playwright_runner.py", "P8 Runtime", target="url", timeout=120),
)

SUITE = VERIFICATION_SUITE


def main(argv: Optional[Sequence[str]] = None) -> int:
    return run_suite(
        "REDEVKIT - FULL VERIFICATION",
        "FULL VERIFICATION REPORT",
        "Run the complete REDEVKIT verification suite",
        SUITE,
        argv,
    )


if __name__ == "__main__":
    raise SystemExit(main())
