#!/usr/bin/env python3
"""Lightweight static accessibility audit for HTML, JSX, TSX and PHP views.

This checker intentionally limits itself to findings that can be inferred from
source. Component names such as ``<Button>`` and ``<InputGroup>`` are not
mistaken for native HTML elements.

Comments (HTML ``<!-- -->``, JSX ``{/* */}``, JS ``/* */`` and ``//``) are
removed before any check, so a tag mentioned in a comment is never a finding.
JSX expressions such as ``tabIndex={1}`` are recognised. In ``.php`` and
``.phtml`` views every PHP block is replaced by a dynamic-value marker first
(see ``audit_common``); PHP files without markup (controllers, models) are not
pages and are ignored. Checks that need a whole document (``<html lang>``, skip
link) only run on files that contain that element, so partial views never
trigger them.

Paths follow the shared exclusion policy (``audit_common.PathFilter``).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Sequence

sys.dont_write_bytecode = True  # importing the shared helper must not leave __pycache__ behind
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_common import (  # noqa: E402
    PathFilter, add_exclusion_arguments, is_server_template_suffix, path_filter_from_args, read_markup_source,
)

EXIT_PASS, EXIT_FAIL, EXIT_USAGE, EXIT_SKIPPED = 0, 1, 2, 3
SUFFIXES = {".html", ".htm", ".jsx", ".tsx", ".php", ".phtml"}
# Inputs whose accessible name comes from value/alt or the browser default.
SELF_LABELLED_INPUTS = {"submit", "reset", "button", "image"}

_BLOCK_COMMENTS = re.compile(r"<!--.*?-->|/\*.*?\*/", re.DOTALL)
# A // comment starts at line start or after a delimiter; "http://" never matches.
_LINE_COMMENT = re.compile(r"(^|[\s;{}(),])//[^\n]*", re.MULTILINE)
NAVIGATION_BLOCK = re.compile(r"<(?:nav|header)|role\s*=\s*[\"']navigation[\"']", re.IGNORECASE)
SKIP_LINK = re.compile(r"href\s*=\s*[\"']#(?:main|main-content|maincontent|content|primary)[\"']", re.IGNORECASE)
SKIP_LINK_TEXT = re.compile(
    r"<a\b[^>]*href\s*=\s*[\"']#[^\"']+[\"'][^>]*>[^<]*\b(?:skip|pular|saltar)\b"
    r"|<a\b[^>]*class\s*=\s*[\"'][^\"']*\bskip",
    re.IGNORECASE,
)
POSITIVE_TABINDEX = re.compile(
    r"\btabindex\s*=\s*(?:\{\s*)?[\"']?\s*\+?([1-9]\d*)\s*[\"']?\s*\}?",
    re.IGNORECASE,
)


def utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)  # type: ignore[union-attr]
        except (AttributeError, ValueError, OSError):
            pass


def strip_comments(content: str) -> str:
    """Blank out comments while keeping line numbers stable."""
    content = _BLOCK_COMMENTS.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), content)
    return _LINE_COMMENT.sub(lambda m: m.group(1) + " " * (len(m.group(0)) - len(m.group(1))), content)


def find_html_files(project_path: Path, path_filter: Optional[PathFilter] = None) -> list[Path]:
    """Markup files to check; PHP files count only when they hold markup (views)."""
    path_filter = path_filter if path_filter is not None else PathFilter(project_path)
    files = []
    for path in path_filter.walk(project_path):
        if path.suffix.lower() not in SUFFIXES:
            continue
        if is_server_template_suffix(path):
            try:
                if read_markup_source(path) is None:
                    continue
            except OSError:
                continue
        files.append(path)
    return sorted(files)


def _opening_tags(content: str, tag: str) -> list[str]:
    # Case-sensitive on purpose: <Input> and <Html> are components, not native elements.
    return re.findall(rf"<{tag}\b[^>]*>", content, re.DOTALL)


def _input_type(tag: str) -> str:
    match = re.search(r"\btype\s*=\s*[\"']?([a-z]+)", tag)
    return match.group(1) if match else "text"


def check_content(content: str) -> list[str]:
    issues: list[str] = []
    content = strip_comments(content)

    for input_tag in _opening_tags(content, "input"):
        normalized = input_tag.lower()
        input_type = _input_type(normalized)
        if input_type == "hidden":
            continue
        if input_type in SELF_LABELLED_INPUTS and (input_type in {"submit", "reset"} or "value=" in normalized or "alt=" in normalized):
            continue
        accessible = any(
            token in normalized
            for token in ("aria-label=", "aria-labelledby=", "id=", "{...", "name=", "title=")
        )
        if not accessible:
            issues.append("Native input without id, name, aria-label, or aria-labelledby")
            break

    for match in re.finditer(r"<button\b([^>]*)>(.*?)</button\s*>", content, re.DOTALL):
        attributes, body = match.groups()
        if "aria-label=" in attributes.lower() or "aria-labelledby=" in attributes.lower():
            continue
        text = re.sub(r"<[^>]+>|\{[^}]+\}", "", body).strip()
        has_child_content = bool(re.search(r"<[A-Za-z]", body) or re.search(r"\{[^}]+\}", body))
        if not text and not has_child_content:
            issues.append("Native button without accessible text or label")
            break

    html_tags = _opening_tags(content, "html")
    if html_tags and not any(re.search(r"\blang\s*=", tag, re.IGNORECASE) for tag in html_tags):
        issues.append("Missing lang attribute on <html>")

    # A skip link bypasses repeated blocks (WCAG 2.4.1): required only when the
    # document has navigation or a header before its content.
    if _opening_tags(content, "body") and NAVIGATION_BLOCK.search(content):
        if not SKIP_LINK.search(content) and not SKIP_LINK_TEXT.search(content):
            issues.append("Document body is missing a skip-to-main-content link")

    # Native elements are lowercase; the handler is onClick (JSX) or onclick (HTML).
    non_interactive_click = re.finditer(
        r"<(div|span|li|section|article)\b([^>]*)\b(?i:onclick)\s*=([^>]*)>",
        content,
        re.DOTALL,
    )
    for match in non_interactive_click:  # Match objects: unpack the groups, not the match
        _, before, after = match.groups()
        attributes = f"{before} {after}".lower()
        keyboard_enabled = "onkeydown=" in attributes or "onkeyup=" in attributes
        semantic_button = 'role="button"' in attributes or "role='button'" in attributes
        focusable = "tabindex=" in attributes
        if not (keyboard_enabled and semantic_button and focusable):
            issues.append("Non-interactive element with onClick lacks role, tabIndex, or keyboard handler")
            break

    if POSITIVE_TABINDEX.search(content):
        issues.append("Avoid positive tabIndex values")

    for media_tag in re.findall(r"<(?:audio|video)\b[^>]*>", content, re.DOTALL):
        if "autoplay" in media_tag.lower() and "muted" not in media_tag.lower():
            issues.append("Autoplay media should be muted")
            break

    for div_tag in re.findall(r"<div\b[^>]*role\s*=\s*[\"']button[\"'][^>]*>", content, re.DOTALL):
        lowered_tag = div_tag.lower()
        if "tabindex=" not in lowered_tag or ("onkeydown=" not in lowered_tag and "onkeyup=" not in lowered_tag):
            issues.append("role='button' requires tabIndex and a keyboard handler")
            break

    return issues


def check_accessibility(file_path: Path) -> list[str]:
    try:
        content = read_markup_source(file_path)
    except OSError:
        return []
    return check_content(content) if content is not None else []


def main(argv: Optional[Sequence[str]] = None) -> int:
    utf8_stdio()
    parser = argparse.ArgumentParser(description="Static accessibility audit for HTML, JSX, TSX and PHP views")
    parser.add_argument("project", nargs="?", default=".")
    add_exclusion_arguments(parser)
    args = parser.parse_args(argv)
    project_path = Path(args.project).resolve()
    if not project_path.is_dir():
        print(json.dumps({"error": f"Directory not found: {project_path}"}))
        return EXIT_USAGE

    print(f"\n{'=' * 60}\n[ACCESSIBILITY CHECKER] WCAG Static Audit\n{'=' * 60}")
    print(f"Project: {project_path}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n" + "-" * 60)

    path_filter = path_filter_from_args(project_path, args)
    print(path_filter.describe())
    files = find_html_files(project_path, path_filter)
    print(f"Found {len(files)} HTML/JSX/TSX/PHP view files")
    if not files:
        print("SKIPPED (no HTML, JSX, TSX or PHP view files found)")
        return EXIT_SKIPPED
    all_issues = []
    for file_path in files:
        issues = check_accessibility(file_path)
        if issues:
            all_issues.append({"file": file_path.relative_to(project_path).as_posix(), "issues": issues})

    print("\n" + "=" * 60 + "\nACCESSIBILITY ISSUES\n" + "=" * 60)
    if all_issues:
        for item in all_issues[:20]:
            print(f"\n{item['file']}:")
            for issue in item["issues"]:
                print(f"  - {issue}")
    else:
        print("No statically detectable accessibility issues found.")

    total_issues = sum(len(item["issues"]) for item in all_issues)
    output = {
        "script": "accessibility_checker",
        "project": str(project_path),
        "files_checked": len(files),
        "files_with_issues": len(all_issues),
        "issues_found": total_issues,
        "passed": total_issues == 0,
    }
    print("\n" + json.dumps(output, indent=2))
    return EXIT_PASS if output["passed"] else EXIT_FAIL


if __name__ == "__main__":
    raise SystemExit(main())
