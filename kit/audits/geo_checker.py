#!/usr/bin/env python3
"""
GEO Checker - Generative Engine Optimization Audit
Checks PUBLIC WEB CONTENT for AI citation readiness.

PURPOSE:
    - Analyze pages that will be INDEXED by AI engines (ChatGPT, Perplexity, etc.)
    - Check for structured data, author info, dates, FAQ sections
    - Help content rank in AI-generated answers

WHAT IT CHECKS:
    - HTML files (actual web pages)
    - JSX/TSX files (React page components)
    - NOT markdown files (those are developer docs, not public content)

    - PHP views (.php/.phtml) that render page content: markup after the PHP
      blocks are masked AND an <h1>. Layouts, partials, error and e-mail
      templates are not public pages.

Path rules (app/, pages/, skipped directories) are evaluated on the path
RELATIVE to the project, so the location of the project itself never matters.
The shared exclusion policy (``audit_common.PathFilter``) applies first.
With no public pages the audit is SKIPPED.

Usage:
    python geo_checker.py <project_path> [--exclude PATTERN] [--no-gitignore]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import List, Optional, Sequence

sys.dont_write_bytecode = True  # importing the shared helper must not leave __pycache__ behind
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_common import (  # noqa: E402
    PathFilter, add_exclusion_arguments, is_server_template_suffix, path_filter_from_args, read_markup_source,
)

EXIT_PASS, EXIT_FAIL, EXIT_USAGE, EXIT_SKIPPED = 0, 1, 2, 3
MAX_PAGES = 100


def utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)  # type: ignore[union-attr]
        except (AttributeError, ValueError, OSError):
            pass


# Directories that never represent public source content (on top of the shared defaults).
SKIP_DIRS = {
    "node_modules", ".next", "dist", "build", ".git", ".github",
    ".agents", ".claude", ".codex", ".redevkit", "__pycache__", ".vscode", ".idea", "coverage",
    "test", "tests", "__tests__", "spec", "public", "components",
    "errors", "email", "emails", "layouts", "partials", "includes",
}

PAGE_SUFFIXES = {".html", ".htm", ".jsx", ".tsx", ".php", ".phtml"}
ARTICLE_SEGMENTS = {"blog", "blogs", "article", "articles", "post", "posts", "news"}
_H1 = re.compile(r"<h1\b", re.IGNORECASE)


def _lower_parts(file_path: Path, root: Optional[Path] = None) -> List[str]:
    """Lowercase path segments relative to the project root (when given)."""
    if root is not None:
        try:
            file_path = file_path.relative_to(root)
        except ValueError:
            pass
    return [part.lower() for part in file_path.parts]


def is_page_file(file_path: Path, root: Optional[Path] = None) -> bool:
    """Return True only for route entry points, not layouts or components."""
    if file_path.suffix.lower() not in PAGE_SUFFIXES:
        return False
    parts = _lower_parts(file_path, root)
    if any(part in SKIP_DIRS for part in parts):
        return False
    if file_path.suffix.lower() in {".html", ".htm"}:
        return True

    name = file_path.stem.lower()
    if is_server_template_suffix(file_path):
        # A PHP view is a content page when it renders an <h1> (see find_web_pages);
        # partials (_nav.php), layouts and error pages are not.
        return not name.startswith("_") and not re.search(r"(?:^|[._-])(?:error|exception|404|500|layout)(?:[._-]|$)", name)
    if name.endswith((".test", ".spec")) or name.startswith(("test_", "spec_")):
        return False

    # Next.js App Router: only page.tsx/page.jsx is a public route entry.
    if "app" in parts:
        return name == "page"

    # Next.js Pages Router: each source file is a route except framework/API files.
    if "pages" in parts:
        pages_index = parts.index("pages")
        route_parts = parts[pages_index + 1 :]
        if "api" in route_parts or name.startswith("_"):
            return False
        return True

    # Other routers commonly use explicit page/index route entries.
    return "routes" in parts and name in {"page", "index"}


def geo_filter(project_path: Path, args=None) -> PathFilter:
    if args is not None:
        return path_filter_from_args(project_path, args, extra_dirs=SKIP_DIRS)
    return PathFilter(project_path, extra_dirs=SKIP_DIRS)


def _php_content_page(file_path: Path) -> bool:
    try:
        content = read_markup_source(file_path)
    except OSError:
        return False
    return content is not None and _H1.search(content) is not None


def find_web_pages(project_path: Path, path_filter: Optional[PathFilter] = None) -> list[Path]:
    """Find public-facing route source files deterministically."""
    path_filter = path_filter if path_filter is not None else geo_filter(project_path)
    files = []
    for file_path in path_filter.walk(project_path):
        if not is_page_file(file_path, project_path):
            continue
        if is_server_template_suffix(file_path) and not _php_content_page(file_path):
            continue
        files.append(file_path)
    return sorted(set(files), key=lambda item: item.as_posix())[:MAX_PAGES]


def _read_route_content(file_path: Path) -> str:
    """Read a route and its directly imported local content modules.

    Next.js route entries often delegate all visible markup to content.tsx or
    localized MDX files. Static analysis must follow those imports or it scores
    a thin wrapper instead of the page users and crawlers receive.
    """
    if is_server_template_suffix(file_path):
        return read_markup_source(file_path) or ""
    content = file_path.read_text(encoding="utf-8", errors="ignore")
    import_paths = re.findall(r"(?:import|from)\s+(?:[^'\"]+?\s+from\s+)?['\"](\.{1,2}/[^'\"]+)['\"]", content)
    extensions = ("", ".tsx", ".ts", ".jsx", ".js", ".mdx", ".md")
    seen = {file_path.resolve()}
    resolved_imports = []
    for import_path in import_paths:
        base = (file_path.parent / import_path).resolve()
        candidates = [Path(f"{base}{extension}") for extension in extensions]
        candidates.extend(base / f"index{extension}" for extension in extensions[1:])
        for candidate in candidates:
            if not candidate.is_file() or candidate.resolve() in seen:
                continue
            seen.add(candidate.resolve())
            resolved_imports.append(candidate)
            break

    # A localized wrapper renders one locale at a time. Analyze the canonical
    # English source rather than concatenating four mutually exclusive H1s.
    canonical_locale = [item for item in resolved_imports if ".en." in item.name.lower()]
    selected = canonical_locale or resolved_imports
    chunks = [content]
    chunks.extend(item.read_text(encoding="utf-8", errors="ignore") for item in selected)
    return "\n".join(chunks)


def check_page(file_path: Path, project_path: Path | None = None) -> dict:
    """Score a route source file without requiring article metadata on product docs."""
    display = file_path.relative_to(project_path).as_posix() if project_path else file_path.as_posix()
    try:
        content = _read_route_content(file_path)
    except Exception as exc:
        return {"file": display, "passed": [], "issues": [f"Error: {exc}"], "score": 0}

    issues = []
    passed = []
    optional_points = 0
    lower_content = content.lower()
    parts = set(_lower_parts(file_path, project_path))
    is_article = bool(parts & ARTICLE_SEGMENTS)
    is_root_landing = file_path.parent.name.lower() == "app"

    heading_content = re.sub(r"```.*?```", "", content, flags=re.S)
    heading_content = re.sub(r"`(?:\.|[^`])*`", "", heading_content, flags=re.S)
    h1_count = len(re.findall(r"<h1[^>]*>", heading_content, re.I))
    h1_count += len(re.findall(r"^#\s+\S", heading_content, re.M))
    h2_count = len(re.findall(r"<h2[^>]*>", heading_content, re.I))
    h2_count += len(re.findall(r"^##\s+\S", heading_content, re.M))
    required_total = 1 if is_root_landing else 2
    required_passed = 0

    if h1_count == 1:
        passed.append("Single H1 heading (clear topic)")
        required_passed += 1
    elif h1_count == 0:
        issues.append("No H1 heading - page topic unclear")
    else:
        issues.append(f"Multiple H1 headings ({h1_count}) - confusing for AI")

    if not is_root_landing:
        repeated_heading = h2_count >= 1 and ".map(" in content
        if h2_count >= 2 or repeated_heading:
            detail = "dynamic repeated" if repeated_heading and h2_count < 2 else str(h2_count)
            passed.append(f"{detail} H2 subheadings (good structure)")
            required_passed += 1
        else:
            issues.append("Add at least two H2 subheadings for scannable content")

    if "application/ld+json" in lower_content:
        passed.append("JSON-LD structured data found")
        optional_points += 10
    if re.search(r'"@type"\s*:\s*"(Organization|Person|Brand|Article|FAQPage)"', content, re.I):
        passed.append("Recognizable schema entity found")
        optional_points += 5

    author_patterns = ("author", "byline", "written-by", "contributor", 'rel="author"')
    has_author = any(pattern in lower_content for pattern in author_patterns)
    date_patterns = ("datepublished", "datemodified", "datetime=", "pubdate", "article:published")
    has_date = any(pattern in lower_content for pattern in date_patterns)
    if is_article:
        required_total += 2
        if has_author:
            passed.append("Author attribution found")
            required_passed += 1
        else:
            issues.append("Article has no author attribution")
        if has_date:
            passed.append("Publication date found")
            required_passed += 1
        else:
            issues.append("Article has no publication date")
    else:
        optional_points += 3 if has_author else 0
        optional_points += 3 if has_date else 0

    optional_checks = (
        (r"<details|faq|frequently.?asked|\"FAQPage\"", "FAQ section detected", 5),
        (r"<(ul|ol)[^>]*>", "Structured list content found", 5),
        (r"<table[^>]*>", "Comparison table found", 5),
        (r"\d+%|according to|data\s+(shows|reveals)|\d+x\s+(faster|better|more)", "Data-backed claims found", 5),
        (r"is defined as|refers to|means that|in short,|simply put,|<dfn", "Direct-answer phrasing found", 5),
    )
    for pattern, label, points in optional_checks:
        if re.search(pattern, content, re.I):
            passed.append(label)
            optional_points += points

    base_score = (required_passed / required_total * 70) if required_total else 70
    score = min(100, round(base_score + min(optional_points, 30)))
    return {"file": display, "passed": passed, "issues": issues, "score": score}


def main(argv: Optional[Sequence[str]] = None) -> int:
    utf8_stdio()
    parser = argparse.ArgumentParser(description="Audit public pages for AI citation readiness")
    parser.add_argument("project", nargs="?", default=".")
    add_exclusion_arguments(parser)
    args = parser.parse_args(argv)
    target_path = Path(args.project).resolve()
    if not target_path.is_dir():
        print(json.dumps({"error": f"Directory not found: {target_path}"}))
        return EXIT_USAGE

    print("\n" + "=" * 60)
    print("  GEO CHECKER - AI Citation Readiness Audit")
    print("=" * 60)
    print(f"Project: {target_path}")
    path_filter = geo_filter(target_path, args)
    print(path_filter.describe())
    print("-" * 60)

    # Find web pages only
    pages = find_web_pages(target_path, path_filter)

    if not pages:
        print("    Looking for: HTML, JSX, TSX files in pages/app directories, PHP views with an <h1>")
        print("    Skipping: docs, tests, config files, node_modules")
        print("SKIPPED (no public web pages found)")
        return EXIT_SKIPPED
    
    print(f"Found {len(pages)} public pages to analyze\n")
    
    # Check each page
    results = []
    for page in pages:
        result = check_page(page, target_path)
        results.append(result)
    
    # Print results
    for result in results:
        status = "[OK]" if result['score'] >= 60 else "[!]"
        print(f"{status} {result['file']}: {result['score']}%")
        if result['issues'] and result['score'] < 60:
            for issue in result['issues'][:2]:  # Show max 2 issues
                print(f"    - {issue}")
    
    # Average score
    avg_score = sum(r['score'] for r in results) / len(results) if results else 0
    
    print("\n" + "=" * 60)
    print(f"AVERAGE GEO SCORE: {avg_score:.0f}%")
    print("=" * 60)
    
    if avg_score >= 80:
        print("[OK] Excellent - Content well-optimized for AI citations")
    elif avg_score >= 60:
        print("[OK] Good - Some improvements recommended")
    elif avg_score >= 40:
        print("[!] Needs work - Add structured elements")
    else:
        print("[X] Poor - Content needs GEO optimization")
    
    # JSON output
    output = {
        "script": "geo_checker",
        "project": str(target_path),
        "pages_checked": len(results),
        "average_score": round(avg_score),
        "passed": avg_score >= 60
    }
    print("\n" + json.dumps(output, indent=2))
    
    return EXIT_PASS if avg_score >= 60 else EXIT_FAIL


if __name__ == "__main__":
    raise SystemExit(main())
