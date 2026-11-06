#!/usr/bin/env python3
"""Shared process runner for the REDEVKIT audit orchestrators.

``checklist.py`` and ``verify_all.py`` import this module. Every audit script
lives in the same directory as this file (``.redevkit/audits/`` once
installed), so scripts are resolved with ``Path(__file__).parent``.

Exit-code contract of every audit script:

* ``0`` - PASS
* ``1`` - FAIL (findings at or above the failure threshold)
* ``2`` - usage error or missing input path
* ``3`` - SKIPPED (the audit could not run or does not apply; the script
  prints a ``SKIPPED (<reason>)`` line)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple

EXIT_PASS = 0
EXIT_FAIL = 1
EXIT_USAGE = 2
EXIT_SKIPPED = 3

AUDITS_DIR = Path(__file__).resolve().parent
SKIP_LINE = re.compile(r"SKIPPED \((?P<reason>[^\n]*)\)")


def utf8_stdio() -> None:
    """Force UTF-8 on stdout/stderr when the stream supports it."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        except (AttributeError, ValueError, OSError):
            pass


@dataclass(frozen=True)
class CheckSpec:
    name: str
    script: str
    category: str
    target: str = "project"  # "project" | "url" | "none"
    required: bool = False
    args: Tuple[str, ...] = ()
    timeout: int = 300


@dataclass
class CheckResult:
    name: str
    category: str
    status: str  # "passed" | "failed" | "skipped" | "error"
    required: bool
    duration_seconds: float = 0.0
    command: List[str] = field(default_factory=list)
    stdout: str = ""
    stderr: str = ""
    reason: str = ""
    notes: List[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.status == "passed"


class Console:
    def __init__(self) -> None:
        enabled = sys.stdout.isatty() and "NO_COLOR" not in os.environ
        self.bold = "\033[1m" if enabled else ""
        self.cyan = "\033[96m" if enabled else ""
        self.green = "\033[92m" if enabled else ""
        self.yellow = "\033[93m" if enabled else ""
        self.red = "\033[91m" if enabled else ""
        self.end = "\033[0m" if enabled else ""

    def header(self, text: str) -> None:
        line = "=" * 70
        print(f"\n{self.bold}{self.cyan}{line}\n{text.center(70)}\n{line}{self.end}\n")

    def passed(self, text: str) -> None:
        print(f"{self.green}[PASS] {text}{self.end}")

    def skipped(self, text: str) -> None:
        print(f"{self.yellow}[SKIP] {text}{self.end}")

    def failed(self, text: str) -> None:
        print(f"{self.red}[FAIL] {text}{self.end}")

    def info(self, text: str) -> None:
        print(text)


CONSOLE = Console()


def build_parser(description: str) -> argparse.ArgumentParser:
    """Single CLI definition shared by checklist.py and verify_all.py (P4)."""
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("project", nargs="?", default=".", help="Project path to validate")
    parser.add_argument("--url", help="Running application URL for Lighthouse and Playwright")
    parser.add_argument(
        "--no-runtime",
        action="store_true",
        help="Skip every URL-based runtime check (Lighthouse, Playwright)",
    )
    parser.add_argument("--stop-on-fail", action="store_true", help="Stop after the first failed check")
    parser.add_argument("--report", type=Path, help="Write a machine-readable JSON report")
    return parser


def select_specs(specs: Iterable[CheckSpec], no_runtime: bool) -> List[CheckSpec]:
    """Drop URL-based checks when ``--no-runtime`` is set."""
    return [spec for spec in specs if not (no_runtime and spec.target == "url")]


def _command_for(spec: CheckSpec, script: Path, project: Path, url: Optional[str]) -> Optional[List[str]]:
    command = [sys.executable, str(script)]
    if spec.target == "project":
        command.append(str(project))
    elif spec.target == "url":
        if not url:
            return None
        command.append(url)
    command.extend(spec.args)
    return command


def _skip_notes(stdout: str) -> List[str]:
    notes: List[str] = []
    for match in SKIP_LINE.finditer(stdout or ""):
        note = f"SKIPPED ({match.group('reason')})"
        if note not in notes:
            notes.append(note)
    return notes


def _child_env() -> dict:
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def run_check(spec: CheckSpec, audits_dir: Path, project: Path, url: Optional[str]) -> CheckResult:
    script = audits_dir / spec.script
    if not script.is_file():
        reason = f"script not found: {script.name}"
        CONSOLE.skipped(f"{spec.name}: SKIPPED ({reason})")
        return CheckResult(spec.name, spec.category, "skipped", spec.required, reason=reason)

    command = _command_for(spec, script, project, url)
    if command is None:
        reason = "URL not provided"
        CONSOLE.skipped(f"{spec.name}: SKIPPED ({reason})")
        return CheckResult(spec.name, spec.category, "skipped", spec.required, reason=reason)

    started = datetime.now(timezone.utc)
    try:
        proc = subprocess.run(
            command,
            cwd=str(project),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=spec.timeout,
            check=False,
            env=_child_env(),
        )
    except subprocess.TimeoutExpired as exc:
        duration = (datetime.now(timezone.utc) - started).total_seconds()
        result = CheckResult(
            spec.name, spec.category, "error", spec.required, duration, command,
            _decode(exc.stdout), _decode(exc.stderr), f"timed out after {spec.timeout}s",
        )
        CONSOLE.failed(f"{spec.name}: {result.reason}")
        return result
    except OSError as exc:
        duration = (datetime.now(timezone.utc) - started).total_seconds()
        result = CheckResult(spec.name, spec.category, "error", spec.required, duration, command, reason=str(exc))
        CONSOLE.failed(f"{spec.name}: {exc}")
        return result

    duration = (datetime.now(timezone.utc) - started).total_seconds()
    stdout = proc.stdout or ""
    notes = _skip_notes(stdout)
    if proc.returncode == EXIT_PASS:
        status, reason = "passed", ""
    elif proc.returncode == EXIT_SKIPPED:
        status = "skipped"
        reason = notes[-1][len("SKIPPED ("):-1] if notes else "audit reported SKIPPED"
        notes = []
    else:
        status, reason = "failed", f"exit code {proc.returncode}"
    result = CheckResult(
        spec.name, spec.category, status, spec.required, duration,
        command, stdout, proc.stderr or "", reason=reason, notes=notes,
    )
    if status == "passed":
        CONSOLE.passed(f"{spec.name} ({duration:.1f}s)")
        for note in notes:
            CONSOLE.info(f"       {note}")
    elif status == "skipped":
        CONSOLE.skipped(f"{spec.name}: SKIPPED ({reason})")
    else:
        CONSOLE.failed(f"{spec.name} ({duration:.1f}s, exit {proc.returncode})")
        _print_failure_output(result)
    return result


def _decode(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _print_failure_output(result: CheckResult, limit: int = 1600) -> None:
    combined = "\n".join(part.strip() for part in (result.stdout, result.stderr) if part.strip())
    if combined:
        print(combined[-limit:])


def execute_suite(
    specs: Sequence[CheckSpec],
    audits_dir: Path,
    project: Path,
    url: Optional[str],
    stop_on_fail: bool = False,
) -> List[CheckResult]:
    results: List[CheckResult] = []
    current_category = ""
    for spec in specs:
        if spec.category != current_category:
            current_category = spec.category
            CONSOLE.header(current_category)
        result = run_check(spec, audits_dir, project, url)
        results.append(result)
        if stop_on_fail and result.status in {"failed", "error"}:
            break
    return results


def suite_success(results: Iterable[CheckResult]) -> bool:
    return all(result.status not in {"failed", "error"} for result in results)


def print_summary(title: str, results: List[CheckResult], started: datetime) -> bool:
    CONSOLE.header(title)
    counts = {status: sum(r.status == status for r in results) for status in ("passed", "failed", "error", "skipped")}
    duration = (datetime.now(timezone.utc) - started).total_seconds()
    print(f"Duration: {duration:.1f}s")
    print(
        f"Checks: {len(results)} | Passed: {counts['passed']} | Failed: {counts['failed']} "
        f"| Errors: {counts['error']} | Skipped: {counts['skipped']}"
    )
    for result in results:
        if result.status == "skipped":
            print(f"[SKIPPED] {result.category} / {result.name} - SKIPPED ({result.reason})")
            continue
        marker = {"passed": "PASS", "failed": "FAIL", "error": "ERROR"}[result.status]
        detail = f" - {result.reason}" if result.reason else ""
        print(f"[{marker}] {result.category} / {result.name}{detail}")
        for note in result.notes:
            print(f"         {note}")
    ok = suite_success(results)
    if ok and counts["skipped"]:
        CONSOLE.passed(f"No blocking failures; {counts['skipped']} check(s) SKIPPED (not verified)")
    elif ok:
        CONSOLE.passed("Validation completed successfully")
    else:
        CONSOLE.failed("Validation found blocking failures")
    return ok


def write_report(path: Path, project: Path, audits_dir: Path, results: List[CheckResult], started: datetime) -> None:
    payload = {
        "project": str(project),
        "audits_dir": str(audits_dir),
        "started_at": started.isoformat(),
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "success": suite_success(results),
        "results": [asdict(result) for result in results],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def run_suite(title: str, summary_title: str, description: str, suite: Sequence[CheckSpec],
              argv: Optional[Sequence[str]] = None) -> int:
    """Entry point shared by checklist.py and verify_all.py."""
    utf8_stdio()
    parser = build_parser(description)
    args = parser.parse_args(argv)

    project = Path(args.project).resolve()
    if not project.is_dir():
        parser.error(f"Project directory does not exist: {project}")

    specs = select_specs(suite, args.no_runtime)
    started = datetime.now(timezone.utc)
    CONSOLE.header(title)
    print(f"Project: {project}\nAudits: {AUDITS_DIR}\nURL: {args.url or 'not provided'}")
    if args.no_runtime:
        print("Runtime checks: disabled (--no-runtime)")

    results = execute_suite(specs, AUDITS_DIR, project, args.url, args.stop_on_fail)
    success = print_summary(summary_title, results, started)
    if args.report:
        write_report(args.report.resolve(), project, AUDITS_DIR, results, started)
        print(f"Report: {args.report.resolve()}")
    return EXIT_PASS if success else EXIT_FAIL
