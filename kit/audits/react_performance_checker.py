#!/usr/bin/env python3
"""
React Performance Checker
Static performance audit for React/Next.js projects, based on the Vercel
Engineering React best practices.

The tree is walked once per scan root; every check reads from that single
file list. Findings are advisory WARNINGs (consecutive ``await`` statements
may be legitimately dependent), so they block only with ``--fail-on-warnings``.

Usage:
    python react_performance_checker.py <project_path> [--fail-on-warnings]
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

EXIT_PASS, EXIT_FAIL, EXIT_USAGE, EXIT_SKIPPED = 0, 1, 2, 3

SKIP_DIRS = {
    ".git", ".next", ".agents", ".claude", ".codex", ".redevkit", "node_modules", "dist",
    "build", "coverage", "out", ".turbo", ".cache", "vendor",
}
SOURCE_EXTENSIONS = (".ts", ".tsx", ".js", ".jsx")

# A component is PascalCase with at least one lowercase letter (so constants
# such as API_URL or MAX never match) and is either a function declaration or
# a const bound to a function expression / arrow function / memo / forwardRef.
_PASCAL = r"[A-Z](?=[A-Za-z0-9]*[a-z])[A-Za-z0-9]*"
COMPONENT_PATTERN = re.compile(
    r"(?:^|[^\w$.])(?:export\s+(?:default\s+)?)?"
    r"(?:function\s+(" + _PASCAL + r")\s*[<(]"
    r"|(?:const|let|var)\s+(" + _PASCAL + r")\s*(?::\s*[^=\n]+)?=\s*"
    r"(?:React\.)?(?:memo\s*\(|forwardRef\s*[<(]|function\b|async\s*\(|\([^)\n]*\)\s*(?::\s*[^=\n]+)?=>|[A-Za-z_$][\w$]*\s*=>))",
    re.MULTILINE,
)
WATERFALL_PATTERN = re.compile(r"await\s+\w+.*?\n\s*(?:const\s+\w+\s*=\s*|let\s+\w+\s*=\s*)?await\s+\w+")


def utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        except (AttributeError, ValueError, OSError):
            pass


def find_components(content: str) -> List[str]:
    return [a or b for a, b in COMPONENT_PATTERN.findall(content)]


class PerformanceChecker:
    def __init__(self, project_path: str):
        self.project_path = Path(project_path).resolve()
        self.issues: List[Dict[str, str]] = []
        self.warnings: List[Dict[str, str]] = []
        self.passed: List[str] = []
        self.walk_count = 0
        self.is_react_project = False
        self.scan_roots = self._discover_scan_roots()
        self._files: Optional[Dict[Path, str]] = None

    def _discover_scan_roots(self) -> List[Path]:
        """Prefer actual React source roots over generated or unrelated files."""
        candidates = []
        for base in (self.project_path, self.project_path / "web"):
            package_json = base / "package.json"
            if not package_json.exists():
                continue
            try:
                package_text = package_json.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if not any(name in package_text for name in ('"next"', '"react"')):
                continue
            self.is_react_project = True
            source = base / "src"
            candidates.append(source if source.is_dir() else base)
        return candidates or [self.project_path]

    def _walk_tree(self, root: Path) -> Iterable[Path]:
        """Single os.walk of one scan root, pruning SKIP_DIRS by segment."""
        self.walk_count += 1
        for current, dirs, files in os.walk(root):
            dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
            for name in sorted(files):
                if name.endswith(SOURCE_EXTENSIONS):
                    yield Path(current) / name

    @property
    def files(self) -> Dict[Path, str]:
        """Source files and their contents, loaded with one pass per tree."""
        if self._files is None:
            loaded: Dict[Path, str] = {}
            seen = set()
            for root in self.scan_roots:
                for path in self._walk_tree(root):
                    resolved = path.resolve()
                    if resolved in seen:
                        continue
                    seen.add(resolved)
                    try:
                        loaded[path] = path.read_text(encoding="utf-8", errors="replace")
                    except OSError:
                        continue
            self._files = loaded
        return self._files

    def _iter_files(self, extensions: Sequence[str]):
        suffixes = tuple(f".{ext}" for ext in extensions)
        for path, content in self.files.items():
            if path.name.endswith(suffixes):
                yield path, content

    def _rel(self, path: Path) -> str:
        try:
            return path.relative_to(self.project_path).as_posix()
        except ValueError:
            return path.as_posix()

    def _warn(self, path: Path, issue: str, fix: str, section: str, severity: str = "WARNING") -> None:
        self.warnings.append({
            "file": self._rel(path), "type": severity, "issue": issue, "fix": fix, "section": section,
        })

    def check_waterfalls(self) -> None:
        """Sequential awaits (Section 1). Advisory: they may be dependent."""
        print("\n[*] Checking for waterfalls (sequential awaits)...")
        for path, content in self._iter_files(["ts", "tsx", "js", "jsx"]):
            if WATERFALL_PATTERN.search(content):
                self._warn(
                    path,
                    "Consecutive awaits (possible waterfall; fine if the second depends on the first)",
                    "Use Promise.all() when the awaited calls are independent",
                    "1-async-eliminating-waterfalls.md",
                )

    def check_barrel_imports(self) -> None:
        """Barrel imports (Section 2)."""
        print("[*] Checking for barrel imports...")
        pattern = re.compile(r"import[^;\n]*from\s+['\"](?:@/|\.{1,2}/)[^'\"]*/index['\"]")
        for path, content in self._iter_files(["ts", "tsx", "js", "jsx"]):
            if pattern.search(content):
                self._warn(path, "Potential barrel imports detected", "Import directly from specific files",
                           "2-bundle-bundle-size-optimization.md")

    def check_dynamic_imports(self) -> None:
        """Large components imported statically (Section 2), using one import index."""
        print("[*] Checking for missing dynamic imports...")
        ts_files = list(self._iter_files(["ts", "tsx"]))
        large = {path.stem for path, content in ts_files if len(content) > 10000}
        if not large:
            return
        import_re = re.compile(r"import\s+(?:\{\s*)?([A-Za-z_$][\w$]*)")
        for path, content in ts_files:
            if "dynamic(" in content:
                continue
            imported = set(import_re.findall(content))
            for name in sorted((imported & large) - {path.stem}):
                self._warn(path, f"Large component {name} imported statically", "Use dynamic() for code splitting",
                           "2-bundle-bundle-size-optimization.md")
                break

    def check_useEffect_fetching(self) -> None:
        """Data fetching in useEffect (Section 4)."""
        print("[*] Checking for useEffect data fetching...")
        for path, content in self._iter_files(["ts", "tsx"]):
            if "useEffect" in content and re.search(r"useEffect.*?fetch\(", content, re.DOTALL):
                self._warn(path, "Data fetching in useEffect", "Consider using SWR or React Query for deduplication",
                           "4-client-client-side-data-fetching.md")

    def check_missing_memoization(self) -> None:
        """Components with props and no memo (Section 5)."""
        print("[*] Checking for missing memoization...")
        for path, content in self._iter_files(["tsx", "jsx"]):
            if not find_components(content):
                continue
            if "React.memo" in content or "memo(" in content:
                continue
            if "props:" in content or "Props>" in content or re.search(r"\(\s*\{[^)]*\}\s*:\s*\w*Props\b", content):
                self._warn(path, "Component with props not memoized", "Consider using React.memo if props are stable",
                           "5-rerender-re-render-optimization.md")

    def check_image_optimization(self) -> None:
        """<img> instead of next/image (Section 6)."""
        print("[*] Checking for image optimization...")
        for path, content in self._iter_files(["ts", "tsx", "js", "jsx"]):
            if "<img" in content and "next/image" not in content:
                self._warn(path, "Using <img> instead of next/image", "Use next/image for automatic optimization",
                           "6-rendering-rendering-performance.md")

    def generate_report(self) -> None:
        print("\n" + "=" * 60)
        print("REACT PERFORMANCE AUDIT REPORT")
        print("=" * 60)
        print(f"\n[CRITICAL ISSUES] ({len(self.issues)})")
        for issue in self.issues:
            print(f"  - {issue['file']}\n    Issue: {issue['issue']}\n    Fix: {issue['fix']}\n    Reference: {issue['section']}\n")
        print(f"\n[WARNINGS] ({len(self.warnings)})")
        for warning in self.warnings[:10]:
            print(f"  - {warning['file']}\n    Issue: {warning['issue']}\n    Fix: {warning['fix']}\n    Reference: {warning['section']}\n")
        if len(self.warnings) > 10:
            print(f"  ... and {len(self.warnings) - 10} more warnings")
        print("\n" + "=" * 60)
        print("SUMMARY:")
        print(f"  Critical Issues: {len(self.issues)}")
        print(f"  Warnings: {len(self.warnings)}")
        print(f"  Files scanned: {len(self.files)}")
        print("=" * 60)
        if not self.issues and not self.warnings:
            print("\n[SUCCESS] No major performance issues detected!")
        else:
            print("\n[REVIEW] Review the findings above (WARNINGs are advisory)")

    def applicable(self) -> bool:
        if self.is_react_project:
            return True
        return any(path.suffix in {".tsx", ".jsx"} for path in self.files)

    def run(self) -> bool:
        """Run all checks; returns True when there are no CRITICAL issues."""
        print("=" * 60)
        print("React Performance Checker (Vercel Engineering)")
        print("=" * 60)
        print(f"Scanning: {self.project_path}")
        self.check_waterfalls()
        self.check_barrel_imports()
        self.check_dynamic_imports()
        self.check_useEffect_fetching()
        self.check_missing_memoization()
        self.check_image_optimization()
        self.generate_report()
        return len(self.issues) == 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    utf8_stdio()
    parser = argparse.ArgumentParser(description="Audit React/Next.js performance patterns")
    parser.add_argument("project_path", nargs="?", default=".")
    parser.add_argument("--fail-on-warnings", action="store_true", help="Treat advisory warnings as blocking")
    args = parser.parse_args(argv)

    if not os.path.isdir(args.project_path):
        parser.error(f"Path not found: {args.project_path}")

    checker = PerformanceChecker(args.project_path)
    if not checker.applicable():
        print("SKIPPED (not a React project: no react/next dependency and no .jsx/.tsx files)")
        return EXIT_SKIPPED
    critical_passed = checker.run()
    passed = critical_passed and (not args.fail_on_warnings or not checker.warnings)
    return EXIT_PASS if passed else EXIT_FAIL


if __name__ == "__main__":
    raise SystemExit(main())
