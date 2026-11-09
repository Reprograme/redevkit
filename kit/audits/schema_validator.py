#!/usr/bin/env python3
"""
Schema Validator - Database schema validation.
Validates Prisma schemas and lists Drizzle schema files.

Usage:
    python schema_validator.py <project_path>

Checks:
    - Prisma schema syntax hints
    - Index recommendations
    - Naming conventions

Files are discovered with one directory walk that prunes SKIP_DIRS by path
segment (node_modules is never entered). Schema issues are advisory: the
audit passes with warnings. Only Prisma schemas are validated: Drizzle files
are listed as "not validated". With no schema files, or with Drizzle files
only (nothing validated), it is SKIPPED.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

EXIT_PASS, EXIT_FAIL, EXIT_USAGE, EXIT_SKIPPED = 0, 1, 2, 3
SKIP_DIRS = {
    "node_modules", ".git", "dist", "build", ".next", "out", "coverage", "__pycache__",
    ".venv", "venv", "vendor", ".agents", ".claude", ".codex", ".redevkit",
}
MAX_SCHEMAS = 10


def utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        except (AttributeError, ValueError, OSError):
            pass


def walk_files(root: Path):
    for current, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for name in sorted(files):
            yield Path(current) / name


def find_schema_files(project_path: Path) -> List[Tuple[str, Path]]:
    """Find database schema files outside node_modules and build output."""
    schemas: List[Tuple[str, Path]] = []
    for path in walk_files(project_path):
        parent = path.parent.name.lower()
        name = path.name.lower()
        if path.suffix == ".prisma" and (name == "schema.prisma" or parent in {"prisma", "schema"}):
            schemas.append(("prisma", path))
        elif path.suffix == ".ts" and parent in {"drizzle", "schema"} and ("schema" in name or "table" in name):
            schemas.append(("drizzle", path))
    schemas.sort(key=lambda item: item[0] != "prisma")  # stable: validated schemas first
    return schemas[:MAX_SCHEMAS]


def validate_prisma_schema(file_path: Path) -> List[str]:
    """Validate a Prisma schema file."""
    issues: List[str] = []
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except OSError as exc:
        return [f"Error reading schema: {str(exc)[:80]}"]

    models = re.findall(r"model\s+(\w+)\s*{([^}]+)}", content, re.DOTALL)
    for model_name, model_body in models:
        if not model_name[0].isupper():
            issues.append(f"Model '{model_name}' should be PascalCase")
        if "@id" not in model_body and "@@id" not in model_body:
            issues.append(f"Model '{model_name}' might be missing an @id field")
        if "createdAt" not in model_body and "created_at" not in model_body:
            issues.append(f"Model '{model_name}' missing createdAt field (recommended)")
        for fk in re.findall(r"^\s*(\w+Id)\s+\w+", model_body, re.MULTILINE):
            if not re.search(r"@@index\(\[[^\]]*\b" + re.escape(fk) + r"\b", content):
                issues.append(f"Consider adding @@index([{fk}]) for better query performance in {model_name}")

    for enum_name in re.findall(r"enum\s+(\w+)\s*{", content):
        if not enum_name[0].isupper():
            issues.append(f"Enum '{enum_name}' should be PascalCase")
    return issues


def main(argv: Optional[Sequence[str]] = None) -> int:
    utf8_stdio()
    parser = argparse.ArgumentParser(description="Validate database schema files (Prisma, Drizzle)")
    parser.add_argument("project", nargs="?", default=".")
    args = parser.parse_args(argv)
    project_path = Path(args.project).resolve()
    if not project_path.is_dir():
        print(json.dumps({"error": f"Directory not found: {project_path}"}))
        return EXIT_USAGE

    print(f"\n{'=' * 60}")
    print("[SCHEMA VALIDATOR] Database Schema Validation")
    print(f"{'=' * 60}")
    print(f"Project: {project_path}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 60)

    schemas = find_schema_files(project_path)
    print(f"Found {len(schemas)} schema files")
    if not schemas:
        print("SKIPPED (no Prisma or Drizzle schema files found)")
        return EXIT_SKIPPED

    validated = [path for kind, path in schemas if kind == "prisma"]
    not_validated = [path.relative_to(project_path).as_posix() for kind, path in schemas if kind == "drizzle"]
    for rel in not_validated:
        print(f"Not validated: {rel} (drizzle, no Drizzle rules)")
    if not validated:
        print("SKIPPED (Drizzle schemas found, not validated)")
        return EXIT_SKIPPED

    all_issues = []
    for file_path in validated:
        rel = file_path.relative_to(project_path).as_posix()
        print(f"\nValidating: {rel} (prisma)")
        issues = validate_prisma_schema(file_path)
        if issues:
            all_issues.append({"file": rel, "type": "prisma", "issues": issues})

    print("\n" + "=" * 60)
    print("SCHEMA ISSUES")
    print("=" * 60)
    if all_issues:
        for item in all_issues:
            print(f"\n{item['file']} ({item['type']}):")
            for issue in item["issues"][:5]:
                print(f"  - {issue}")
            if len(item["issues"]) > 5:
                print(f"  ... and {len(item['issues']) - 5} more issues")
    else:
        print("No schema issues found!")
    if not_validated:
        print(f"\nNot validated: {len(not_validated)} Drizzle schema file(s) (listed above)")

    total_issues = sum(len(item["issues"]) for item in all_issues)
    output = {
        "script": "schema_validator",
        "project": str(project_path),
        "schemas_checked": len(validated),
        "files": [path.relative_to(project_path).as_posix() for path in validated],
        "not_validated": not_validated,
        "issues_found": total_issues,
        "passed": True,  # schema issues are advisory warnings
        "issues": all_issues,
    }
    print("\n" + json.dumps(output, indent=2))
    return EXIT_PASS


if __name__ == "__main__":
    raise SystemExit(main())
