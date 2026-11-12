#!/usr/bin/env python3
"""REDEVKIT security scanner.

Performs lightweight, local checks for dependency hygiene, hard-coded secrets,
dangerous code patterns, and common security misconfiguration.

The scanner is intentionally dependency-free. It is a guardrail, not a
replacement for a full SAST/SCA product.

External tools (``npm audit``) are resolved with ``shutil.which`` (``npm.cmd``
on Windows) and run without a shell. When a sub-tool cannot run, the report
says ``SKIPPED (<reason>)`` for it; a failure is never silently swallowed.
"""
from __future__ import annotations

import argparse
import bisect
import io
import json
import re
import shutil
import sys
import tokenize
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

sys.dont_write_bytecode = True  # importing the shared helper must not leave __pycache__ behind
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_common import PathFilter, add_exclusion_arguments, path_filter_from_args, run_external  # noqa: E402

EXIT_PASS, EXIT_FAIL, EXIT_USAGE, EXIT_SKIPPED = 0, 1, 2, 3
NPM_AUDIT_TIMEOUT = 90


def utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)  # type: ignore[union-attr]
        except (AttributeError, ValueError, OSError):
            pass


SECRET_PATTERNS: Tuple[Tuple[str, str, str], ...] = (
    (r"api[_-]?key\s*[=:]\s*[\"'][^\"']{10,}[\"']", "API Key", "high"),
    (r"token\s*[=:]\s*[\"'][^\"']{10,}[\"']", "Token", "high"),
    (r"bearer\s+[a-zA-Z0-9\-_.]{16,}", "Bearer Token", "critical"),
    (r"AKIA[0-9A-Z]{16}", "AWS Access Key", "critical"),
    (r"aws[_-]?secret[_-]?access[_-]?key\s*[=:]\s*[\"'][^\"']+[\"']", "AWS Secret", "critical"),
    (r"AZURE[_-]?[A-Z_]+\s*[=:]\s*[\"'][^\"']+[\"']", "Azure Credential", "critical"),
    (r"GOOGLE[_-]?[A-Z_]+\s*[=:]\s*[\"'][^\"']+[\"']", "GCP Credential", "critical"),
    (r"password\s*[=:]\s*[\"'][^\"']{6,}[\"']", "Password", "high"),
    (r"(?:mongodb|postgres(?:ql)?|mysql|redis):\/\/[^\s\"']+", "Database Connection String", "critical"),
    (r"-----BEGIN\s+(?:RSA|PRIVATE|EC|OPENSSH)\s+KEY-----", "Private Key", "critical"),
    (r"ssh-rsa\s+[A-Za-z0-9+/]{80,}", "SSH Key", "critical"),
    (r"eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+", "JWT Token", "high"),
)

# Applied to code with strings AND comments removed, so text inside string
# literals (documentation, error messages) never triggers them.
# eval/exec are flagged as calls of the builtin only: a method or member call
# (``regex.exec(``, ``model.eval()``, ``$pdo->exec(``, ``Foo::exec(``) is not one.
DANGEROUS_PATTERNS: Tuple[Tuple[str, str, str, str], ...] = (
    (r"(?<![.$>:])\beval\s*\(", "eval() usage", "critical", "Code injection risk"),
    (r"(?<![.$>:])\bexec\s*\(", "exec() usage", "critical", "Code injection risk"),
    (r"new\s+Function\s*\(", "Function constructor", "high", "Code injection risk"),
    (r"child_process\.exec\s*\(", "child_process.exec", "high", "Command injection risk"),
    (r"subprocess\.(?:call|run|Popen)\s*\([^\n]*shell\s*=\s*True", "subprocess shell=True", "high", "Command injection risk"),
    (r"dangerouslySetInnerHTML", "dangerouslySetInnerHTML", "high", "XSS risk"),
    (r"\.innerHTML\s*=", "innerHTML assignment", "medium", "XSS risk"),
    (r"document\.write\s*\(", "document.write", "medium", "XSS risk"),
    (r"verify\s*=\s*False", "SSL verification disabled", "high", "MITM risk"),
    (r"--insecure\b", "Insecure flag", "medium", "Security disabled"),
    (r"disable[_-]?ssl", "SSL disabled", "high", "MITM risk"),
    (r"pickle\.loads?\s*\(", "pickle usage", "high", "Unsafe deserialization risk"),
    (r"yaml\.load\s*\(", "yaml.load usage", "high", "Unsafe deserialization risk"),
)

# SQL-building rules (S3). SQL lives inside string literals, so these rules run
# on the comment-free source BEFORE strings are stripped. They do not require
# the concatenated operand to be quoted: ``"SELECT ... " + userId`` matches.
_SQL_KEYWORD = (
    r"(?:\bSELECT\b"
    r"|(?i:\binsert\s+into\b|\bupdate\s+[\w.\"`\[\]]+\s+set\b|\bdelete\s+from\b"
    r"|\bselect\s+(?:\*|[\w.]+(?:\s*,\s*[\w.]+)*)\s+from\b))"
)
# "SQL string concatenation" is ``<keyword> ... + operand`` or ``operand + ... <keyword>`` on
# one line, where an operand is ``[A-Za-z_$][\w$.\[\]()]*``. It is not a single regex: that
# regex rescanned the rest of the line from every ``x +`` and was quadratic in the line
# length (87 s for a 400 KB single-line bundle). ``_sql_concatenation_lines`` reads each
# line once.
SQL_CONCATENATION = ("SQL string concatenation", "critical", "SQL injection risk")
_SQL_KEYWORD_RE = re.compile(_SQL_KEYWORD)
_PLUS_OPERAND = re.compile(r"\+\s*[A-Za-z_$]")
_OPERAND_START = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_$")
_OPERAND_PUNCTUATION = frozenset("_$.[]()")
_OPERAND_GAP = 200  # white space (line breaks included) accepted between "+" and its operand
SQL_PATTERNS: Tuple[Tuple["re.Pattern[str]", str, str, str], ...] = (
    (
        re.compile(r"\b(?:[fF][rR]?|[rR][fF])[\"'][^\n]*?" + _SQL_KEYWORD + r"[^\n]*?\{"),
        "SQL f-string", "critical", "SQL injection risk",
    ),
    (
        re.compile(r"`[^`]*?" + _SQL_KEYWORD + r"[^`]*?\$\{"),
        "SQL template literal interpolation", "critical", "SQL injection risk",
    ),
    (
        re.compile(_SQL_KEYWORD + r"[^\n]*?[\"']\s*(?:%\s*[A-Za-z_(]|\.format\s*\()"),
        "SQL string formatting", "critical", "SQL injection risk",
    ),
)

SEVERITY_RANK = {"none": 99, "low": 1, "medium": 2, "high": 3, "critical": 4}
# Directory exclusion is the shared policy of audit_common.PathFilter
# (defaults + .gitignore + .redevkit/audit-ignore + --exclude).
CODE_EXTENSIONS = {".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".py", ".go", ".java", ".rb", ".php"}
CONFIG_EXTENSIONS = {".json", ".yaml", ".yml", ".toml", ".env", ".ini", ".conf"}
PLACEHOLDER_MARKERS = (
    "YOUR_", "EXAMPLE", "CHANGEME", "CHANGE_ME", "REPLACE_ME", "PLACEHOLDER",
    "DUMMY", "SAMPLE", "FAKE_", "TEST_TOKEN", "TEST_KEY",
)
ALLOW_MARKERS = ("redevkit: allow-secret", "# nosec")
SELF_PATH = Path(__file__).resolve()


def which(name: str) -> Optional[str]:
    return shutil.which(name)


def _new_result(tool: str, status: str) -> Dict[str, Any]:
    return {"tool": tool, "findings": [], "status": status, "scanned_files": 0, "skipped": []}


def _filter_for(project: Path, path_filter: Optional[PathFilter]) -> PathFilter:
    return path_filter if path_filter is not None else PathFilter(project)


def _iter_files(project: Path, extensions: set, path_filter: Optional[PathFilter] = None):
    for path in _filter_for(project, path_filter).walk(project):
        if path.resolve() == SELF_PATH:
            continue
        if path.suffix.lower() in extensions or path.name.startswith(".env"):
            yield path


def _relative(path: Path, project: Path) -> str:
    try:
        return path.relative_to(project).as_posix()
    except ValueError:
        return path.as_posix()


def _is_placeholder(value: str) -> bool:
    upper = value.upper()
    return any(marker in upper for marker in PLACEHOLDER_MARKERS)


def _redact(value: str) -> str:
    value = value.strip().replace("\n", " ")
    if len(value) <= 12:
        return "<redacted>"
    return f"{value[:4]}…{value[-4:]}"


def _blank(chunk: str) -> str:
    return re.sub(r"[^\r\n]", " ", chunk)


_PY_STRING_TYPES = {tokenize.STRING}
for _name in ("FSTRING_START", "FSTRING_MIDDLE", "FSTRING_END", "TSTRING_START", "TSTRING_MIDDLE", "TSTRING_END"):
    if hasattr(tokenize, _name):
        _PY_STRING_TYPES.add(getattr(tokenize, _name))


def _python_views(text: str) -> Tuple[str, str]:
    """Return (code without comments, code without comments and strings)."""
    split = text.splitlines(keepends=True)
    no_comments = [list(line) for line in split]
    no_strings = [list(line) for line in split]

    def blank(target: List[List[str]], start: Tuple[int, int], end: Tuple[int, int]) -> None:
        (srow, scol), (erow, ecol) = start, end
        for row in range(srow, erow + 1):
            if not (1 <= row <= len(target)):
                continue
            line = target[row - 1]
            begin = scol if row == srow else 0
            finish = ecol if row == erow else len(line)
            for col in range(begin, min(finish, len(line))):
                if line[col] not in "\r\n":
                    line[col] = " "

    try:
        for tok in tokenize.generate_tokens(io.StringIO(text).readline):
            if tok.type == tokenize.COMMENT:
                blank(no_comments, tok.start, tok.end)
                blank(no_strings, tok.start, tok.end)
            elif tok.type in _PY_STRING_TYPES:
                blank(no_strings, tok.start, tok.end)
    except (tokenize.TokenError, IndentationError, SyntaxError):
        pass
    return "".join("".join(line) for line in no_comments), "".join("".join(line) for line in no_strings)


def _generic_views(text: str, hash_comments: bool = False) -> Tuple[str, str]:
    """C-family sources: return (without comments, without comments and strings).

    ``hash_comments`` also treats ``#`` as a line comment (PHP, Ruby), except
    PHP 8 attributes ``#[...]``.
    """
    no_comments: List[str] = []
    no_strings: List[str] = []
    i, n = 0, len(text)
    while i < n:
        two = text[i:i + 2]
        char = text[i]
        if two == "//" or (hash_comments and char == "#" and two != "#["):
            end = text.find("\n", i)
            end = n if end == -1 else end
            chunk = _blank(text[i:end])
            no_comments.append(chunk)
            no_strings.append(chunk)
            i = end
        elif two == "/*":
            end = text.find("*/", i + 2)
            end = n if end == -1 else end + 2
            chunk = _blank(text[i:end])
            no_comments.append(chunk)
            no_strings.append(chunk)
            i = end
        elif char in "\"'`":
            end = i + 1
            while end < n:
                if text[end] == "\\":
                    end += 2
                    continue
                if text[end] == char:
                    end += 1
                    break
                if text[end] == "\n" and char != "`":
                    break
                end += 1
            end = min(end, n)
            chunk = text[i:end]
            no_comments.append(chunk)
            no_strings.append(_blank(chunk))
            i = end
        else:
            no_comments.append(char)
            no_strings.append(char)
            i += 1
    return "".join(no_comments), "".join(no_strings)


def code_views(text: str, suffix: str) -> Tuple[str, str]:
    if suffix.lower() == ".py":
        return _python_views(text)
    return _generic_views(text, hash_comments=suffix.lower() in {".php", ".rb"})


def _operand_before(text: str, plus: int) -> Optional[int]:
    """Index of the last character of the operand that precedes the ``+`` at ``plus``, or None."""
    index = plus - 1
    floor = max(0, plus - _OPERAND_GAP)
    while index >= floor and text[index].isspace():
        index -= 1
    end = index
    while index >= 0 and (text[index].isalnum() or text[index] in _OPERAND_PUNCTUATION):
        if text[index] in _OPERAND_START:
            return end  # an identifier starts inside the run that ends right before the "+"
        index -= 1
    return None


def _sql_concatenation_lines(text: str) -> List[int]:
    """Lines (1-based) where a SQL keyword and a ``+ operand`` / ``operand +`` share a line.

    Linear in the size of the text: per line that holds a keyword, one search after the
    first keyword and one pass over the ``+`` signs before the last keyword.
    """
    line_starts = [0]
    position = text.find("\n")
    while position != -1:
        line_starts.append(position + 1)
        position = text.find("\n", position + 1)

    def line_of(index: int) -> int:
        return bisect.bisect_right(line_starts, index)

    keywords: Dict[int, Tuple[int, int]] = {}  # line -> (end of its first keyword, start of its last keyword)
    for match in _SQL_KEYWORD_RE.finditer(text):
        line = line_of(match.start())
        first_end = keywords[line][0] if line in keywords else match.end()
        keywords[line] = (first_end, match.start())

    lines: List[int] = []
    for line, (first_end, last_start) in keywords.items():
        line_start = line_starts[line - 1]
        line_end = line_starts[line] - 1 if line < len(line_starts) else len(text)
        # <keyword> ... + operand (the operand may be on the next line)
        after = _PLUS_OPERAND.search(text, first_end, min(len(text), line_end + _OPERAND_GAP))
        if after and after.start() <= line_end:
            lines.append(line)
        # operand + ... <keyword> (the operand may be on the previous line)
        plus = text.find("+", line_start, last_start)
        while plus != -1:
            operand_end = _operand_before(text, plus)
            if operand_end is not None:
                lines.append(line_of(operand_end))
                break
            plus = text.find("+", plus + 1, last_start)
    return sorted(set(lines))


def find_sql_injection(text_without_comments: str) -> List[Tuple[int, str, str, str]]:
    """Return (line, name, severity, category) for SQL built from variables."""
    found: List[Tuple[int, str, str, str]] = [
        (line, *SQL_CONCATENATION) for line in _sql_concatenation_lines(text_without_comments)
    ]
    line_starts: Optional[List[int]] = None
    seen = set()
    for pattern, name, severity, category in SQL_PATTERNS:
        for match in pattern.finditer(text_without_comments):
            if line_starts is None:
                line_starts = [0] + [m.end() for m in re.finditer("\n", text_without_comments)]
            line = bisect.bisect_right(line_starts, match.start())
            if (line, name) in seen:
                continue
            seen.add((line, name))
            found.append((line, name, severity, category))
    return found


def _skip(result: Dict[str, Any], reason: str) -> None:
    result["skipped"].append(reason)


def _npm_audit(project: Path, result: Dict[str, Any]) -> None:
    npm = which("npm")
    if not npm:
        _skip(result, "npm audit: npm not found on PATH")
        return
    try:
        proc = run_external([npm, "audit", "--json"], cwd=project, timeout=NPM_AUDIT_TIMEOUT)
    except OSError as exc:
        _skip(result, f"npm audit: could not start npm ({exc})")
        return
    if proc.timed_out:
        _skip(result, f"npm audit: timed out after {NPM_AUDIT_TIMEOUT}s")
        return

    raw = (proc.stdout or "").strip() or (proc.stderr or "").strip()
    if not raw:
        _skip(result, f"npm audit: no output (exit {proc.returncode})")
        return
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        _skip(result, f"npm audit: output is not JSON (exit {proc.returncode})")
        return
    if not isinstance(data, dict):
        _skip(result, "npm audit: unexpected output format")
        return
    if data.get("error"):
        error = data["error"]
        detail = error.get("summary") or error.get("code") if isinstance(error, dict) else str(error)
        _skip(result, f"npm audit: {str(detail).splitlines()[0] if detail else 'failed'}")
        return
    metadata = data.get("metadata", {}).get("vulnerabilities") if isinstance(data.get("metadata"), dict) else None
    if not isinstance(metadata, dict):
        _skip(result, "npm audit: no vulnerability metadata in output")
        return
    counts = {key: int(metadata.get(key, 0) or 0) for key in ("critical", "high", "moderate", "low")}
    result["npm_audit"] = counts
    for severity in ("critical", "high"):
        if counts[severity]:
            result["findings"].append({
                "type": "npm audit", "severity": severity,
                "message": f"{counts[severity]} {severity} dependency vulnerabilities.",
            })


def scan_dependencies(project_path: str, path_filter: Optional[PathFilter] = None) -> Dict[str, Any]:
    """Root manifests and lock files; ``path_filter`` is accepted for a uniform signature."""
    project = Path(project_path)
    result = _new_result("dependency_scanner", "[OK] Supply chain checks passed")

    ecosystems = {
        "node": (["package.json"], ["package-lock.json", "npm-shrinkwrap.json", "yarn.lock", "pnpm-lock.yaml", "bun.lock", "bun.lockb"]),
        "python": (["pyproject.toml", "setup.py", "setup.cfg", "requirements.in"], ["poetry.lock", "Pipfile.lock", "uv.lock", "requirements.txt"]),
        "ruby": (["Gemfile"], ["Gemfile.lock"]),
        "rust": (["Cargo.toml"], ["Cargo.lock"]),
        "go": (["go.mod"], ["go.sum"]),
    }
    for name, (manifests, locks) in ecosystems.items():
        if name == "node" and not _node_has_dependencies(project):
            continue  # nothing to lock: a package.json without dependencies needs no lock file
        if name == "python" and not _python_has_dependencies(project):
            continue  # a pyproject.toml that only configures tools (ruff, pytest, ...) locks nothing
        if any((project / f).exists() for f in manifests) and not any((project / f).exists() for f in locks):
            result["findings"].append({
                "type": "Missing lock file",
                "severity": "high",
                "ecosystem": name,
                "message": f"{name}: manifest found but no supported lock file is present.",
            })

    if (project / "package.json").exists():
        if _node_has_dependencies(project):
            _npm_audit(project, result)
        else:
            result["npm_audit"] = "not_applicable (no dependencies)"

    if result["findings"]:
        result["status"] = "[!] Dependency risks found"
    return result


def scan_secrets(project_path: str, path_filter: Optional[PathFilter] = None) -> Dict[str, Any]:
    project = Path(project_path).resolve()
    result = _new_result("secret_scanner", "[OK] No secrets detected")
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}

    for path in _iter_files(project, CODE_EXTENSIONS | CONFIG_EXTENSIONS, path_filter):
        result["scanned_files"] += 1
        try:
            content = path.read_text("utf-8", errors="ignore")
        except OSError:
            continue
        lines = content.splitlines()
        for pattern, secret_type, severity in SECRET_PATTERNS:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                matched = match.group(0)
                line = content.count("\n", 0, match.start()) + 1
                source_line = lines[line - 1].lower() if line <= len(lines) else ""
                if _is_placeholder(matched) or any(marker in source_line for marker in ALLOW_MARKERS):
                    continue
                result["findings"].append({
                    "file": _relative(path, project), "line": line, "type": secret_type,
                    "severity": severity, "preview": _redact(matched),
                })
                counts[severity] += 1

    result["by_severity"] = counts
    if counts["critical"]:
        result["status"] = "[!!] CRITICAL: Potential secrets exposed"
    elif counts["high"]:
        result["status"] = "[!] HIGH: Potential secrets found"
    elif sum(counts.values()):
        result["status"] = "[?] Potential secrets need review"
    return result


def scan_code_patterns(project_path: str, path_filter: Optional[PathFilter] = None) -> Dict[str, Any]:
    project = Path(project_path).resolve()
    result = _new_result("pattern_scanner", "[OK] No dangerous patterns")
    by_category: Dict[str, int] = {}

    def record(path: Path, line_number: int, name: str, severity: str, category: str, original: List[str]) -> None:
        snippet = original[line_number - 1].strip()[:120] if line_number <= len(original) else ""
        result["findings"].append({
            "file": _relative(path, project), "line": line_number,
            "pattern": name, "severity": severity, "category": category,
            "snippet": snippet,
        })
        by_category[category] = by_category.get(category, 0) + 1

    for path in _iter_files(project, CODE_EXTENSIONS, path_filter):
        result["scanned_files"] += 1
        try:
            text = path.read_text("utf-8", errors="ignore")
        except OSError:
            continue
        original = text.splitlines()
        without_comments, without_strings = code_views(text, path.suffix)

        # 1. SQL rules first, while string literals are still present.
        for line_number, name, severity, category in find_sql_injection(without_comments):
            record(path, line_number, name, severity, category, original)

        # 2. Everything else on code without strings or comments.
        for line_number, code_line in enumerate(without_strings.splitlines(), 1):
            for pattern, name, severity, category in DANGEROUS_PATTERNS:
                if re.search(pattern, code_line, re.IGNORECASE):
                    record(path, line_number, name, severity, category, original)

    result["by_category"] = by_category
    critical = sum(f["severity"] == "critical" for f in result["findings"])
    high = sum(f["severity"] == "high" for f in result["findings"])
    if critical:
        result["status"] = f"[!!] CRITICAL: {critical} dangerous pattern(s)"
    elif high:
        result["status"] = f"[!] HIGH: {high} risky pattern(s)"
    elif result["findings"]:
        result["status"] = "[?] Patterns need review"
    return result


def _node_has_dependencies(project: Path) -> bool:
    """True when package.json declares any dependency (or cannot be read: stay conservative)."""
    manifest = project / "package.json"
    if not manifest.exists():
        return False
    try:
        data = json.loads(manifest.read_text("utf-8-sig"))
    except (OSError, ValueError):
        return True
    if not isinstance(data, dict):
        return True
    keys =("dependencies", "devDependencies", "optionalDependencies", "peerDependencies")
    return any(isinstance(data.get(k), dict) and data.get(k) for k in keys)


def _python_has_dependencies(project: Path) -> bool:
    """False only when the sole Python manifest is a pyproject.toml declaring no dependency."""
    if any((project / name).exists() for name in ("setup.py", "setup.cfg", "requirements.in")):
        return True
    manifest = project / "pyproject.toml"
    if not manifest.exists():
        return False
    try:
        text = manifest.read_text("utf-8-sig")
    except (OSError, ValueError):
        return True
    try:
        import tomllib  # Python 3.11+
    except ImportError:
        tomllib = None  # type: ignore[assignment]
    if tomllib is None:
        return bool(
            re.search(r"^\s*(?:dependencies|optional-dependencies|dev-dependencies)\s*=\s*[\[{]\s*[^\]}\s]", text, re.MULTILINE)
            or re.search(r"^\s*\[(?:tool\.poetry\.(?:dev-)?dependencies|tool\.poetry\.group\.|dependency-groups)", text, re.MULTILINE)
        )
    try:
        data = tomllib.loads(text)
    except ValueError:  # tomllib.TOMLDecodeError
        return True
    table = data.get("project") if isinstance(data.get("project"), dict) else {}
    if table.get("dependencies") or table.get("optional-dependencies") or data.get("dependency-groups"):
        return True
    tool = data.get("tool") if isinstance(data.get("tool"), dict) else {}
    poetry = tool.get("poetry") if isinstance(tool.get("poetry"), dict) else {}
    poetry_deps = poetry.get("dependencies") if isinstance(poetry.get("dependencies"), dict) else {}
    if any(key.lower() != "python" for key in poetry_deps) or poetry.get("dev-dependencies") or poetry.get("group"):
        return True
    return False


WEB_FRAMEWORKS = {"next", "nuxt", "vite", "@angular/core", "react-dom", "vue", "svelte", "astro", "express", "fastify", "koa", "hono", "@nestjs/core"}


def _looks_like_web_project(project: Path) -> bool:
    """A project that serves pages or uses a web framework (security headers apply).

    A bare package.json (CLI, library, plain JSON API on node:http) is not enough.
    """
    indicators = (
        "next.config.js", "next.config.mjs", "next.config.ts", "vite.config.ts", "vite.config.js",
        "nuxt.config.ts", "angular.json", "nginx.conf", "index.html", "public/index.html", "src/index.html",
    )
    if any((project / name).exists() for name in indicators):
        return True
    manifest = project / "package.json"
    if manifest.exists():
        try:
            data = json.loads(manifest.read_text("utf-8-sig"))
        except (OSError, ValueError):
            return False
        if not isinstance(data, dict):
            return False
        deps = {}
        for key in ("dependencies", "devDependencies"):
            if isinstance(data.get(key), dict):
                deps.update(data[key])
        return any(name in deps for name in WEB_FRAMEWORKS)
    return False


def scan_configuration(project_path: str, path_filter: Optional[PathFilter] = None) -> Dict[str, Any]:
    project = Path(project_path).resolve()
    result = _new_result("config_scanner", "[OK] Configuration checks passed")
    checks: Dict[str, Any] = {}
    patterns = (
        (r'"DEBUG"\s*:\s*true', "Debug mode enabled", "high"),
        (r"\bdebug\s*=\s*True", "Debug mode enabled", "high"),
        (r'"CORS_ALLOW_ALL"\s*:\s*true', "CORS allows every origin", "high"),
        (r'Access-Control-Allow-Origin[^\n]*[\"\']\*[\"\']', "CORS wildcard", "high"),
        (r"allowCredentials[^\n]*true[^\n]*origin[^\n]*\*", "Credentials with wildcard CORS", "critical"),
    )

    extra_names = {"next.config.js", "next.config.mjs", "next.config.ts", "webpack.config.js", ".eslintrc.js", "nginx.conf"}
    header_files = {"next.config.js", "next.config.mjs", "next.config.ts", "middleware.ts", "middleware.js", "nginx.conf", "vercel.json"}
    header_pattern = re.compile(
        r"Content-Security-Policy|Strict-Transport-Security|X-Frame-Options|frame-ancestors|Referrer-Policy",
        re.IGNORECASE,
    )
    has_security_headers = False
    for path in _filter_for(project, path_filter).walk(project):
        filename = path.name
        if path.resolve() == SELF_PATH:
            continue
        if path.suffix.lower() not in CONFIG_EXTENSIONS and filename not in extra_names and not filename.startswith(".env"):
            continue
        result["scanned_files"] += 1
        try:
            content = path.read_text("utf-8", errors="ignore")
        except OSError:
            continue
        if filename in header_files and header_pattern.search(content):
            has_security_headers = True
        for pattern, issue, severity in patterns:
            if re.search(pattern, content, re.IGNORECASE):
                result["findings"].append({"file": _relative(path, project), "issue": issue, "severity": severity})

    if _looks_like_web_project(project):
        checks["security_headers_config"] = has_security_headers
        if not checks["security_headers_config"]:
            result["findings"].append({
                "issue": "No obvious security-header configuration found",
                "severity": "medium",
                "recommendation": "Configure CSP, HSTS, frame-ancestors/X-Frame-Options, and Referrer-Policy as appropriate.",
            })
    else:
        checks["security_headers_config"] = "not_applicable"
    result["checks"] = checks

    if any(f["severity"] == "critical" for f in result["findings"]):
        result["status"] = "[!!] CRITICAL: Configuration issues"
    elif any(f["severity"] == "high" for f in result["findings"]):
        result["status"] = "[!] HIGH: Configuration review needed"
    elif result["findings"]:
        result["status"] = "[?] Configuration review recommended"
    return result


def run_full_scan(project_path: str, scan_type: str = "all", path_filter: Optional[PathFilter] = None) -> Dict[str, Any]:
    project = str(Path(project_path).resolve())
    path_filter = _filter_for(Path(project), path_filter)
    report: Dict[str, Any] = {
        "project": project,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "scan_type": scan_type,
        "scans": {},
        "summary": {
            "total_findings": 0, "critical": 0, "high": 0, "medium": 0, "low": 0,
            "skipped": [], "overall_status": "[OK] SECURE",
        },
    }
    scanners: Dict[str, Tuple[str, Callable[..., Dict[str, Any]]]] = {
        "deps": ("dependencies", scan_dependencies),
        "secrets": ("secrets", scan_secrets),
        "patterns": ("code_patterns", scan_code_patterns),
        "config": ("configuration", scan_configuration),
    }
    for key, (name, scanner) in scanners.items():
        if scan_type not in {"all", key}:
            continue
        scan_result = scanner(project, path_filter)
        report["scans"][name] = scan_result
        report["summary"]["skipped"].extend(scan_result.get("skipped", []))
        findings = scan_result.get("findings", [])
        report["summary"]["total_findings"] += len(findings)
        for finding in findings:
            severity = finding.get("severity", "low")
            if severity in {"critical", "high", "medium", "low"}:
                report["summary"][severity] += 1

    summary = report["summary"]
    if summary["critical"]:
        summary["overall_status"] = "[!!] CRITICAL ISSUES FOUND"
    elif summary["high"]:
        summary["overall_status"] = "[!] HIGH RISK ISSUES"
    elif summary["total_findings"]:
        summary["overall_status"] = "[?] REVIEW RECOMMENDED"
    elif _nothing_scanned(report):
        # No file of a kind this scanner reads and no dependency manifest: nothing was
        # checked, so the result is SKIPPED (exit 3), never "[OK] SECURE".
        summary["nothing_scanned"] = True
        summary["overall_status"] = f"SKIPPED ({NOTHING_TO_SCAN})"
    return report


DEPENDENCY_MANIFESTS = (
    "package.json", "pyproject.toml", "setup.py", "setup.cfg", "requirements.in", "requirements.txt",
    "Gemfile", "Cargo.toml", "go.mod",
)
NOTHING_TO_SCAN = "no source, configuration or dependency file to scan"


def _nothing_scanned(report: Dict[str, Any]) -> bool:
    project = Path(report["project"])
    return (
        not report["summary"]["skipped"]
        and all(scan.get("scanned_files", 0) == 0 for scan in report["scans"].values())
        and not any((project / name).exists() for name in DEPENDENCY_MANIFESTS)
    )


def _should_fail(report: Dict[str, Any], threshold: str) -> bool:
    if threshold == "none":
        return False
    required_rank = SEVERITY_RANK[threshold]
    return any(
        report["summary"].get(severity, 0) > 0 and rank >= required_rank
        for severity, rank in SEVERITY_RANK.items()
        if severity != "none"
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    utf8_stdio()
    parser = argparse.ArgumentParser(description="Run lightweight local security checks")
    parser.add_argument("project_path", nargs="?", default=".", help="Project directory to scan")
    parser.add_argument("--scan-type", choices=["all", "deps", "secrets", "patterns", "config"], default="all")
    parser.add_argument("--output", choices=["json", "summary"], default="json")
    parser.add_argument(
        "--fail-on", choices=["none", "low", "medium", "high", "critical"], default="high",
        help="Return exit code 1 when a finding at or above this severity exists (default: high)",
    )
    add_exclusion_arguments(parser)
    args = parser.parse_args(argv)
    project = Path(args.project_path).resolve()
    if not project.is_dir():
        print(json.dumps({"error": f"Directory not found: {project}"}))
        return EXIT_USAGE

    path_filter = path_filter_from_args(project, args)
    report = run_full_scan(str(project), args.scan_type, path_filter)
    report["excluded"] = path_filter.describe()
    if args.output == "summary":
        summary = report["summary"]
        print(f"\n{'=' * 60}\nSecurity Scan: {report['project']}\n{'=' * 60}")
        print(path_filter.describe())
        print(f"Status: {summary['overall_status']}")
        print(f"Total Findings: {summary['total_findings']}")
        print(f"  Critical: {summary['critical']}\n  High: {summary['high']}\n  Medium: {summary['medium']}\n  Low: {summary['low']}")
        for reason in summary["skipped"]:
            print(f"  SKIPPED ({reason})")
        print("=" * 60)
        for name, scan in report["scans"].items():
            print(f"\n{name.upper()}: {scan['status']}")
            for reason in scan.get("skipped", []):
                print(f"  SKIPPED ({reason})")
            for finding in scan.get("findings", [])[:10]:
                print(f"  - {finding}")
    else:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    if report["summary"].get("nothing_scanned"):
        return EXIT_SKIPPED
    return EXIT_FAIL if _should_fail(report, args.fail_on) else EXIT_PASS


if __name__ == "__main__":
    raise SystemExit(main())
