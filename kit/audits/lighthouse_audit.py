#!/usr/bin/env python3
"""Run a Lighthouse audit and enforce configurable quality thresholds.

The ``lighthouse`` CLI is resolved with ``shutil.which`` (``lighthouse.cmd`` on
Windows) and run without a shell. When it is not installed or cannot start,
the audit is SKIPPED (exit 3), never PASS.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional, Sequence
from urllib.parse import urlparse

EXIT_PASS, EXIT_FAIL, EXIT_USAGE, EXIT_SKIPPED = 0, 1, 2, 3


def utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        except (AttributeError, ValueError, OSError):
            pass


def valid_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise argparse.ArgumentTypeError("URL must start with http:// or https://")
    return value


def run_lighthouse(url: str, timeout: int = 180) -> dict:
    executable = shutil.which("lighthouse")
    if not executable:
        return {"url": url, "status": "skipped", "reason": "Lighthouse CLI not found on PATH", "fix": "npm install -g lighthouse"}

    output_path: Optional[Path] = None
    try:
        fd, raw_path = tempfile.mkstemp(prefix="redevkit-lighthouse-", suffix=".json")
        os.close(fd)
        output_path = Path(raw_path)
        proc = subprocess.run(
            [
                executable,
                url,
                "--output=json",
                f"--output-path={output_path}",
                "--chrome-flags=--headless --no-sandbox --disable-dev-shm-usage",
                "--only-categories=performance,accessibility,best-practices,seo",
                "--quiet",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
        if proc.returncode != 0 and (not output_path.exists() or output_path.stat().st_size == 0):
            return {"url": url, "status": "error", "error": "Lighthouse execution failed", "stderr": proc.stderr[-1200:]}
        report = json.loads(output_path.read_text("utf-8"))
        categories = report.get("categories", {})
        scores = {
            "performance": round(float(categories.get("performance", {}).get("score") or 0) * 100),
            "accessibility": round(float(categories.get("accessibility", {}).get("score") or 0) * 100),
            "best_practices": round(float(categories.get("best-practices", {}).get("score") or 0) * 100),
            "seo": round(float(categories.get("seo", {}).get("score") or 0) * 100),
        }
        audits = report.get("audits", {})
        metrics = {}
        for key, label in (
            ("largest-contentful-paint", "lcp_ms"),
            ("cumulative-layout-shift", "cls"),
            ("interaction-to-next-paint", "inp_ms"),
            ("total-blocking-time", "tbt_ms"),
        ):
            value = audits.get(key, {}).get("numericValue")
            if value is not None:
                metrics[label] = round(float(value), 3)
        return {"url": url, "status": "success", "scores": scores, "metrics": metrics}
    except subprocess.TimeoutExpired:
        return {"url": url, "status": "error", "error": f"Lighthouse timed out after {timeout}s"}
    except FileNotFoundError as exc:
        return {"url": url, "status": "skipped", "reason": f"Lighthouse could not start: {exc}"}
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return {"url": url, "status": "error", "error": str(exc)}
    finally:
        if output_path:
            output_path.unlink(missing_ok=True)


def main(argv: Optional[Sequence[str]] = None) -> int:
    utf8_stdio()
    parser = argparse.ArgumentParser(description="Run Lighthouse and enforce score thresholds")
    parser.add_argument("url", type=valid_url)
    parser.add_argument("--min-performance", type=int, default=50)
    parser.add_argument("--min-accessibility", type=int, default=80)
    parser.add_argument("--min-best-practices", type=int, default=80)
    parser.add_argument("--min-seo", type=int, default=80)
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args(argv)

    result = run_lighthouse(args.url, args.timeout)
    if result.get("status") == "skipped":
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print(f"SKIPPED ({result['reason']})")
        return EXIT_SKIPPED
    thresholds = {
        "performance": args.min_performance,
        "accessibility": args.min_accessibility,
        "best_practices": args.min_best_practices,
        "seo": args.min_seo,
    }
    failures = []
    if result.get("status") == "success":
        failures = [name for name, minimum in thresholds.items() if result["scores"].get(name, 0) < minimum]
        result["thresholds"] = thresholds
        result["failed_thresholds"] = failures
        result["passed"] = not failures
    else:
        result["passed"] = False
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return EXIT_PASS if result["passed"] else EXIT_FAIL


if __name__ == "__main__":
    raise SystemExit(main())
