#!/usr/bin/env python3
"""
API Validator - Checks API endpoints for best practices.
Validates OpenAPI specs, response formats, and common issues.

Usage:
    python api_validator.py <project_path>

Files are found with one directory walk under the shared exclusion policy
(``audit_common.PathFilter``), by path segment, never by substring, so
``app-builder/`` or ``capital.ts`` are not confused with ``build`` or ``api``.
Only files NAMED as OpenAPI/Swagger specs are validated as specs. With no API
files the audit is SKIPPED.
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
from audit_common import PathFilter, add_exclusion_arguments, path_filter_from_args, read_text  # noqa: E402

EXIT_PASS, EXIT_FAIL, EXIT_USAGE, EXIT_SKIPPED = 0, 1, 2, 3
CODE_SUFFIXES = {".ts", ".js", ".py"}
API_DIRS = {"routes", "controllers", "endpoints", "api"}
SPEC_NAMES = {"swagger.json", "swagger.yaml", "swagger.yml", "openapi.json", "openapi.yaml", "openapi.yml"}
# "api" as a whole word of the file name: api.ts, user-api.ts, api_client.py, userApi.ts
API_NAME = re.compile(r"(?:^|[._-])api(?:[._-]|$)|[a-z]Api(?:[A-Z]|$)|^Api[A-Z]")
MAX_FILES = 15


def utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)  # type: ignore[union-attr]
        except (AttributeError, ValueError, OSError):
            pass


def is_spec_file(path: Path) -> bool:
    name = path.name.lower()
    return name in SPEC_NAMES or name.endswith((".openapi.json", ".openapi.yaml", ".openapi.yml"))


def is_api_file(path: Path, root: Path) -> bool:
    name = path.name.lower()
    if is_spec_file(path):
        return True
    if path.suffix.lower() not in CODE_SUFFIXES or name.endswith(".d.ts"):
        return False
    rel_dirs = {part.lower() for part in path.relative_to(root).parts[:-1]}
    if rel_dirs & API_DIRS:
        return True
    return bool(API_NAME.search(path.stem))


def find_api_files(project_path: Path, path_filter: Optional[PathFilter] = None) -> List[Path]:
    """Find API-related files, never entering node_modules or build output."""
    path_filter = path_filter if path_filter is not None else PathFilter(project_path)
    return [path for path in path_filter.walk(project_path) if is_api_file(path, project_path)]


def check_openapi_spec(file_path: Path) -> dict:
    """Check OpenAPI/Swagger specification."""
    issues = []
    passed = []
    
    try:
        content = read_text(file_path)

        if file_path.suffix.lower() == '.json':
            spec = json.loads(content)
        else:
            # Basic YAML check
            if 'openapi:' in content or 'swagger:' in content:
                passed.append("[OK] OpenAPI/Swagger version defined")
            else:
                issues.append("[X] No OpenAPI version found")
            
            if 'paths:' in content:
                passed.append("[OK] Paths section exists")
            else:
                issues.append("[X] No paths defined")
            
            if 'components:' in content or 'definitions:' in content:
                passed.append("[OK] Schema components defined")
            
            return {'file': str(file_path), 'passed': passed, 'issues': issues, 'type': 'openapi'}
        
        # JSON OpenAPI checks
        if 'openapi' in spec or 'swagger' in spec:
            passed.append("[OK] OpenAPI version defined")
        
        if 'info' in spec:
            if 'title' in spec['info']:
                passed.append("[OK] API title defined")
            if 'version' in spec['info']:
                passed.append("[OK] API version defined")
            if 'description' not in spec['info']:
                issues.append("[!] API description missing")
        
        if 'paths' in spec:
            path_count = len(spec['paths'])
            passed.append(f"[OK] {path_count} endpoints defined")
            
            # Check each path
            for path, methods in spec['paths'].items():
                for method, details in methods.items():
                    if method in ['get', 'post', 'put', 'patch', 'delete']:
                        if 'responses' not in details:
                            issues.append(f"[X] {method.upper()} {path}: No responses defined")
                        if 'summary' not in details and 'description' not in details:
                            issues.append(f"[!] {method.upper()} {path}: No description")
        
    except Exception as e:
        issues.append(f"[X] Parse error: {e}")
    
    return {'file': str(file_path), 'passed': passed, 'issues': issues, 'type': 'openapi'}

def check_api_code(file_path: Path) -> dict:
    """Check API code for common issues."""
    issues = []
    passed = []
    
    try:
        content = read_text(file_path)

        # Check for error handling
        error_patterns = [
            r'try\s*{', r'try:', r'\.catch\(',
            r'except\s+', r'catch\s*\('
        ]
        has_error_handling = any(re.search(p, content) for p in error_patterns)
        if has_error_handling:
            passed.append("[OK] Error handling present")
        else:
            issues.append("[X] No error handling found")
        
        # Check for status codes
        status_patterns = [
            r'status\s*\(\s*\d{3}\s*\)', r'statusCode\s*[=:]\s*\d{3}',
            r'HttpStatus\.', r'status_code\s*=\s*\d{3}',
            r'\.status\(\d{3}\)', r'res\.status\('
        ]
        has_status = any(re.search(p, content) for p in status_patterns)
        if has_status:
            passed.append("[OK] HTTP status codes used")
        else:
            issues.append("[!] No explicit HTTP status codes")
        
        # Check for validation
        validation_patterns = [
            r'validate', r'schema', r'zod', r'joi', r'yup',
            r'pydantic', r'@Body\(', r'@Query\('
        ]
        has_validation = any(re.search(p, content, re.I) for p in validation_patterns)
        if has_validation:
            passed.append("[OK] Input validation present")
        else:
            issues.append("[!] No input validation detected")
        
        # Check for auth middleware
        auth_patterns = [
            r'auth', r'jwt', r'bearer', r'token',
            r'middleware', r'guard', r'@Authenticated'
        ]
        has_auth = any(re.search(p, content, re.I) for p in auth_patterns)
        if has_auth:
            passed.append("[OK] Authentication/authorization detected")
        
        # Check for rate limiting
        rate_patterns = [r'rateLimit', r'throttle', r'rate.?limit']
        has_rate = any(re.search(p, content, re.I) for p in rate_patterns)
        if has_rate:
            passed.append("[OK] Rate limiting present")
        
        # Check for logging
        log_patterns = [r'console\.log', r'logger\.', r'logging\.', r'log\.']
        has_logging = any(re.search(p, content) for p in log_patterns)
        if has_logging:
            passed.append("[OK] Logging present")
        
    except Exception as e:
        issues.append(f"[X] Read error: {e}")
    
    return {'file': str(file_path), 'passed': passed, 'issues': issues, 'type': 'code'}


def main(argv: Optional[Sequence[str]] = None) -> int:
    utf8_stdio()
    parser = argparse.ArgumentParser(description="Check API code and OpenAPI specs for best practices")
    parser.add_argument("project", nargs="?", default=".")
    add_exclusion_arguments(parser)
    args = parser.parse_args(argv)
    project_path = Path(args.project).resolve()
    if not project_path.is_dir():
        print(json.dumps({"error": f"Directory not found: {project_path}"}))
        return EXIT_USAGE

    print("\n" + "=" * 60)
    print("  API VALIDATOR - Endpoint Best Practices Check")
    print("=" * 60)
    path_filter = path_filter_from_args(project_path, args)
    print(path_filter.describe() + "\n")

    api_files = find_api_files(project_path, path_filter)
    if not api_files:
        print("   Looking for: routes/, controllers/, endpoints/, api/, *api*.ts|js|py, openapi/swagger specs")
        print("SKIPPED (no API files found)")
        return EXIT_SKIPPED

    results = []
    for file_path in api_files[:MAX_FILES]:
        if is_spec_file(file_path):  # not "openapi" as a substring: openapi-client.ts is code
            result = check_openapi_spec(file_path)
        else:
            result = check_api_code(file_path)
        result["file"] = file_path.relative_to(project_path).as_posix()
        results.append(result)

    total_issues = 0
    total_passed = 0
    for result in results:
        print(f"\n[FILE] {result['file']} [{result['type']}]")
        for item in result["passed"]:
            print(f"   {item}")
            total_passed += 1
        for item in result["issues"]:
            print(f"   {item}")
            if item.startswith("[X]"):
                total_issues += 1

    print("\n" + "=" * 60)
    print(f"[RESULTS] {total_passed} passed, {total_issues} critical issues")
    print("=" * 60)
    if total_issues == 0:
        print("[OK] API validation passed")
        return EXIT_PASS
    print("[X] Fix critical issues before deployment")
    return EXIT_FAIL


if __name__ == "__main__":
    raise SystemExit(main())
