#!/usr/bin/env python3
"""
SEO Checker - Search Engine Optimization Audit.
Checks HTML/JSX/TSX pages for SEO best practices.

WHAT IT CHECKS:
    - <title> element and meta description on layout/document files
    - Open Graph tags
    - Heading hierarchy (single H1)
    - Image alt attributes

Discovery uses one directory walk that prunes SKIP_DIRS by path segment
(node_modules is never entered). Non-page files are recognised by whole words
of the file name, not substrings (``capital.tsx`` is not an "api" file). The
page title counts only when a real ``<title>`` element exists: a ``title=``
attribute is not a page title. With no page files the audit is SKIPPED.

Usage:
    python seo_checker.py <project_path>
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Sequence

EXIT_PASS, EXIT_FAIL, EXIT_USAGE, EXIT_SKIPPED = 0, 1, 2, 3

SKIP_DIRS = {
    "node_modules", ".next", "dist", "build", ".git", ".github", "out",
    "__pycache__", ".vscode", ".idea", "coverage", "test", "tests",
    "__tests__", "spec", "docs", "documentation", "examples",
    ".agents", ".claude", ".codex", ".redevkit",
}

# Whole words of a file name that mark non-page modules.
SKIP_WORDS = {
    "config", "setup", "util", "utils", "helper", "helpers", "hook", "hooks", "context",
    "store", "service", "services", "api", "lib", "constant", "constants", "type", "types",
    "interface", "interfaces", "mock", "mocks", "test", "spec", "stories", "story",
}
PAGE_DIRS = {"pages", "app", "routes", "views", "screens"}
PAGE_WORDS = {
    "page", "index", "home", "about", "contact", "blog", "post", "article", "product",
    "landing", "layout", "document",
}
PAGE_SUFFIXES = {".html", ".htm", ".jsx", ".tsx"}
MAX_PAGES = 50

TITLE_ELEMENT = re.compile(r"<title\b[^>]*>", re.IGNORECASE)


def utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        except (AttributeError, ValueError, OSError):
            pass


def name_words(name: str) -> List[str]:
    """Split a file name into lowercase words: 'userProfile.test' -> user, profile, test."""
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", name)
    return [word.lower() for word in re.split(r"[^A-Za-z0-9]+", spaced) if word]


def is_page_file(file_path: Path, root: Optional[Path] = None) -> bool:
    """Check if this file is likely a public-facing page."""
    words = name_words(file_path.name)
    if any(word in SKIP_WORDS for word in words):
        return False
    if file_path.suffix.lower() in {".html", ".htm"}:
        return True
    try:
        rel_dirs = file_path.relative_to(root).parts[:-1] if root else file_path.parts[:-1]
    except ValueError:
        rel_dirs = file_path.parts[:-1]
    if any(part.lower() in PAGE_DIRS for part in rel_dirs):
        return True
    return any(word in PAGE_WORDS for word in name_words(file_path.stem))


def find_pages(project_path: Path) -> List[Path]:
    """Find page files to check."""
    files: List[Path] = []
    for current, dirs, names in os.walk(project_path):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for name in sorted(names):
            path = Path(current) / name
            if path.suffix.lower() in PAGE_SUFFIXES and is_page_file(path, project_path):
                files.append(path)
    return files[:MAX_PAGES]


def check_content(content: str) -> List[str]:
    """Return SEO issues for one page source."""
    issues: List[str] = []
    lowered = content.lower()
    is_layout = "<Head" in content or "<head>" in lowered or "<head " in lowered

    if is_layout and not TITLE_ELEMENT.search(content):
        issues.append("Missing <title> tag")

    has_description = re.search(r"name\s*=\s*[\"']description[\"']", content, re.IGNORECASE)
    if is_layout and not has_description:
        issues.append("Missing meta description")

    if is_layout and "og:" not in content:
        issues.append("Missing Open Graph tags")

    h1_matches = re.findall(r"<h1\b[^>]*>", content, re.IGNORECASE)
    if len(h1_matches) > 1:
        issues.append(f"Multiple H1 tags ({len(h1_matches)})")

    for img in re.findall(r"<img\b[^>]*>", content, re.IGNORECASE):
        if "alt=" not in img.lower():
            issues.append("Image missing alt attribute")
            break
        if 'alt=""' in img or "alt=''" in img:
            issues.append("Image has empty alt attribute")
            break
    return issues


def check_page(file_path: Path, root: Optional[Path] = None) -> dict:
    display = file_path.relative_to(root).as_posix() if root else file_path.name
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except OSError as exc:
        return {"file": display, "issues": [f"Error: {exc}"]}
    return {"file": display, "issues": check_content(content)}


def main(argv: Optional[Sequence[str]] = None) -> int:
    utf8_stdio()
    parser = argparse.ArgumentParser(description="Audit page sources for SEO basics")
    parser.add_argument("project", nargs="?", default=".")
    args = parser.parse_args(argv)
    project_path = Path(args.project).resolve()
    if not project_path.is_dir():
        print(json.dumps({"error": f"Directory not found: {project_path}"}))
        return EXIT_USAGE

    print(f"\n{'=' * 60}")
    print("  SEO CHECKER - Search Engine Optimization Audit")
    print(f"{'=' * 60}")
    print(f"Project: {project_path}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 60)

    pages = find_pages(project_path)
    if not pages:
        print("    Looking for: HTML, JSX, TSX in pages/app/routes directories")
        print("SKIPPED (no page files found)")
        return EXIT_SKIPPED

    print(f"Found {len(pages)} page files to analyze\n")
    all_issues = [result for result in (check_page(f, project_path) for f in pages) if result["issues"]]

    print("=" * 60)
    print("SEO ANALYSIS RESULTS")
    print("=" * 60)
    if all_issues:
        issue_counts: dict = {}
        for item in all_issues:
            for issue in item["issues"]:
                issue_counts[issue] = issue_counts.get(issue, 0) + 1
        print("\nIssue Summary:")
        for issue, count in sorted(issue_counts.items(), key=lambda x: -x[1]):
            print(f"  [{count}] {issue}")
        print(f"\nAffected files ({len(all_issues)}):")
        for item in all_issues[:5]:
            print(f"  - {item['file']}")
        if len(all_issues) > 5:
            print(f"  ... and {len(all_issues) - 5} more")
    else:
        print("\n[OK] No SEO issues found!")

    total_issues = sum(len(item["issues"]) for item in all_issues)
    passed = total_issues == 0
    output = {
        "script": "seo_checker",
        "project": str(project_path),
        "files_checked": len(pages),
        "files_with_issues": len(all_issues),
        "issues_found": total_issues,
        "passed": passed,
    }
    print("\n" + json.dumps(output, indent=2))
    return EXIT_PASS if passed else EXIT_FAIL


if __name__ == "__main__":
    raise SystemExit(main())
