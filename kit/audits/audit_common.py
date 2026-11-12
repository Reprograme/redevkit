#!/usr/bin/env python3
"""Shared helpers for the REDEVKIT audits (imported, never run directly).

Path exclusion
--------------
Every audit that walks the project uses ``PathFilter``. A path is excluded by
the LAST matching rule of, in order:

1. the shared defaults (``DEFAULT_EXCLUDED_DIRS`` and
   ``DEFAULT_EXCLUDED_FILES``: dependencies, vendored code, build output,
   caches, generated reports, minified assets, agent folders) and the extra
   directories of the calling audit;
2. the project's ``.gitignore`` files (root and nested, each relative to its
   own directory) and ``.git/info/exclude`` (disable with ``--no-gitignore``);
3. the user's patterns: ``.redevkit/audit-ignore`` (one pattern per line),
   then every ``--exclude PATTERN`` given on the command line.

All patterns use ``.gitignore`` syntax (``dir/``, ``*.ext``, ``/anchored``,
``a/**/b``, ``!re-include``) and are evaluated on the path RELATIVE to the
project root, segment by segment, case-insensitively: the location of the
project itself never matters, and ``build`` never matches ``app-builder``.

Server-rendered templates
-------------------------
``.php`` and ``.phtml`` files are templates only when markup remains after
their PHP blocks are removed (controllers, models and config are pure code).
``mask_server_code`` replaces every ``<?php ... ?>`` / ``<?= ... ?>`` block
with ``{...}``, the same "dynamic value" marker the JSX-aware checks already
understand, so ``alt="<?= $alt ?>"`` is a non-empty value and
``<img src="<?= $x ?>">`` no longer ends the tag at the ``?>``.

External commands
-----------------
Every audit starts external tools (``npm``, ``tsc``, ``lighthouse``, the
project's test command, the other audit scripts) through ``run_external``:

* the command never reads the terminal: its stdin is the null device, and the
  environment says ``CI=1`` (kept when the caller already set ``CI``),
  ``NO_COLOR=1`` and ``FORCE_COLOR=0``, so test runners run once instead of
  entering watch mode, nothing prompts and the output carries no colour codes;
* the command runs in its own process group; when the time limit expires the
  WHOLE process tree is killed (on Windows ``npm.cmd`` is a ``cmd.exe`` that
  starts ``node``: killing only the first process leaves ``node`` running and
  holding the output pipes);
* the output is read incrementally, so what was printed before a timeout is
  kept, and no wait on the pipes is unbounded.
"""
from __future__ import annotations

import os
import re
import signal
import subprocess
import threading
import time
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Mapping, NamedTuple, Optional, Sequence, Tuple, Union

DEFAULT_EXCLUDED_DIRS: Tuple[str, ...] = (
    # version control, editors and agent folders
    ".git", ".hg", ".svn", ".idea", ".vscode", ".agents", ".claude", ".codex", ".redevkit",
    # third-party dependencies and vendored code
    "node_modules", "bower_components", "jspm_packages", "vendor", ".venv", "venv",
    "site-packages", ".yarn", ".pnpm-store",
    # build output and framework caches
    "dist", "build", "out", ".next", ".nuxt", ".svelte-kit", ".output", ".turbo", ".cache",
    ".parcel-cache", ".vercel", ".angular", "storybook-static",
    # tool caches
    "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".tox", ".nox", ".gradle",
    # generated reports
    "coverage", ".nyc_output", "htmlcov", "playwright-report", "test-results", "blob-report",
)
DEFAULT_EXCLUDED_FILES: Tuple[str, ...] = (
    "*.min.js", "*.min.mjs", "*.min.cjs", "*.min.css", "*.map",
)
USER_IGNORE_FILE = ".redevkit/audit-ignore"
SERVER_TEMPLATE_SUFFIXES = frozenset({".php", ".phtml"})
SERVER_CODE_MARKER = "{...}"


# --------------------------------------------------------------------------
# .gitignore-style patterns
# --------------------------------------------------------------------------

class Rule:
    """One compiled ``.gitignore`` pattern."""

    __slots__ = ("pattern", "regex", "negate", "dir_only")

    def __init__(self, pattern: str, regex: "re.Pattern[str]", negate: bool, dir_only: bool) -> None:
        self.pattern = pattern
        self.regex = regex
        self.negate = negate
        self.dir_only = dir_only

    def matches(self, rel: str, is_dir: bool) -> bool:
        if self.dir_only and not is_dir:
            return False
        return self.regex.match(rel) is not None

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"Rule({self.pattern!r})"


def _class_to_regex(pattern: str, start: int) -> Tuple[Optional[str], int]:
    """Translate a ``[...]`` class starting at ``start``; (None, start) if unterminated."""
    i = start + 1
    negate = False
    if i < len(pattern) and pattern[i] in "!^":
        negate = True
        i += 1
    body_start = i
    if i < len(pattern) and pattern[i] == "]":
        i += 1
    while i < len(pattern) and pattern[i] != "]":
        i += 1
    if i >= len(pattern):
        return None, start
    body = pattern[body_start:i].replace("\\", "\\\\").replace("^", "\\^").replace("[", "\\[")
    if negate:
        return f"[^/{body}]", i + 1
    return f"[{body}]", i + 1


def glob_to_regex(pattern: str) -> str:
    """Translate a gitignore glob (without anchoring) to a regex body."""
    out: List[str] = []
    i, n = 0, len(pattern)
    while i < n:
        char = pattern[i]
        if char == "*":
            if pattern.startswith("**", i):
                at_segment_start = i == 0 or pattern[i - 1] == "/"
                after = i + 2
                if at_segment_start and after == n:
                    out.append(".*")
                    i = after
                    continue
                if at_segment_start and pattern[after] == "/":
                    out.append("(?:.*/)?")
                    i = after + 1
                    continue
                while i < n and pattern[i] == "*":
                    i += 1
                out.append("[^/]*")
                continue
            out.append("[^/]*")
            i += 1
        elif char == "?":
            out.append("[^/]")
            i += 1
        elif char == "[":
            translated, end = _class_to_regex(pattern, i)
            if translated is None:
                out.append(re.escape(char))
                i += 1
            else:
                out.append(translated)
                i = end
        elif char == "\\" and i + 1 < n:
            out.append(re.escape(pattern[i + 1]))
            i += 2
        else:
            out.append(re.escape(char))
            i += 1
    return "".join(out)


def compile_pattern(line: str) -> Optional[Rule]:
    """Compile one ``.gitignore`` line; None for blank lines, comments and patterns ``re`` rejects."""
    text = line.rstrip("\r\n")
    if not text.endswith("\\ "):  # trailing spaces are ignored unless escaped
        text = text.rstrip(" \t")
    if not text or text.startswith("#"):
        return None
    original = text
    negate = text.startswith("!")
    if negate:
        text = text[1:]
    elif text.startswith("\\!") or text.startswith("\\#"):
        text = text[1:]
    dir_only = text.endswith("/")
    text = text.rstrip("/")
    if not text:
        return None
    anchored = "/" in text
    text = text.lstrip("/")
    if not text:
        return None
    body = glob_to_regex(text)
    if not anchored:
        body = "(?:.*/)?" + body
    try:
        regex = re.compile(f"^{body}$", re.IGNORECASE | re.DOTALL)
    except re.error:
        # A pattern git accepts but ``re`` does not (for example the reversed
        # range in ``*.[a-Z]``): ignore the rule instead of crashing the audit.
        return None
    return Rule(original, regex, negate, dir_only)


def compile_patterns(lines: Iterable[str]) -> List[Rule]:
    rules: List[Rule] = []
    for line in lines:
        rule = compile_pattern(line)
        if rule is not None:
            rules.append(rule)
    return rules


def _read_lines(path: Path) -> List[str]:
    try:
        with open(path, "r", encoding="utf-8-sig", errors="replace") as handle:
            return handle.read().splitlines()
    except OSError:
        return []


def default_patterns(extra_dirs: Iterable[str] = ()) -> List[str]:
    dirs = list(DEFAULT_EXCLUDED_DIRS) + [d for d in extra_dirs if d not in DEFAULT_EXCLUDED_DIRS]
    return [f"{name}/" for name in dirs] + list(DEFAULT_EXCLUDED_FILES)


# --------------------------------------------------------------------------
# PathFilter
# --------------------------------------------------------------------------

class PathFilter:
    """Decide which project paths an audit may read (see the module docstring)."""

    def __init__(
        self,
        root: Path | str,
        *,
        extra_dirs: Iterable[str] = (),
        user_patterns: Sequence[str] = (),
        defaults: bool = True,
        gitignore: bool = True,
        config: bool = True,
    ) -> None:
        self.root = Path(root).resolve()
        base = default_patterns(extra_dirs) if defaults else [f"{name}/" for name in extra_dirs]
        self._base_rules = compile_patterns(base)
        user: List[str] = []
        self.config_file: Optional[Path] = None
        if config:
            candidate = self.root / USER_IGNORE_FILE
            if candidate.is_file():
                self.config_file = candidate
                user.extend(_read_lines(candidate))
        user.extend(user_patterns)
        self._user_rules = compile_patterns(user)
        self.user_patterns = [rule.pattern for rule in self._user_rules]
        self.gitignore = gitignore
        self._gitignore_rules: Dict[str, List[Rule]] = {}
        self._dir_cache: Dict[str, bool] = {}

    # -- rules ----------------------------------------------------------
    def _rules_for_base(self, base: str) -> List[Rule]:
        """Rules of the .gitignore in directory ``base`` (relative, '' = root)."""
        if not self.gitignore:
            return []
        cached = self._gitignore_rules.get(base)
        if cached is not None:
            return cached
        folder = self.root / base if base else self.root
        lines: List[str] = []
        if not base:
            exclude = self.root / ".git" / "info" / "exclude"
            if exclude.is_file():
                lines.extend(_read_lines(exclude))
        ignore = folder / ".gitignore"
        if ignore.is_file():
            lines.extend(_read_lines(ignore))
        rules = compile_patterns(lines)
        self._gitignore_rules[base] = rules
        return rules

    def _decide(self, rel: str, is_dir: bool) -> bool:
        excluded = False
        for rule in self._base_rules:
            if rule.matches(rel, is_dir):
                excluded = not rule.negate
        if self.gitignore:
            parts = rel.split("/")
            for depth in range(len(parts)):
                base = "/".join(parts[:depth])
                rules = self._rules_for_base(base)
                if not rules:
                    continue
                sub = "/".join(parts[depth:])
                for rule in rules:
                    if rule.matches(sub, is_dir):
                        excluded = not rule.negate
        for rule in self._user_rules:
            if rule.matches(rel, is_dir):
                excluded = not rule.negate
        return excluded

    # -- queries ---------------------------------------------------------
    def relative(self, path: Path | str) -> Optional[str]:
        """Path relative to the project root (posix), or None when outside it."""
        candidate = Path(path)
        if not candidate.is_absolute():
            candidate = self.root / candidate
        try:
            rel = candidate.relative_to(self.root)
        except ValueError:
            try:
                rel = candidate.resolve().relative_to(self.root)
            except (ValueError, OSError):
                return None
        text = rel.as_posix()
        return "" if text == "." else text

    def _dir_excluded(self, rel: str) -> bool:
        cached = self._dir_cache.get(rel)
        if cached is None:
            cached = self._decide(rel, True)
            self._dir_cache[rel] = cached
        return cached

    def excluded_rel(self, rel: str, is_dir: bool) -> bool:
        """True when ``rel`` (posix, relative to the root) or one of its parents is excluded."""
        if not rel:
            return False
        parts = rel.split("/")
        for depth in range(1, len(parts)):
            if self._dir_excluded("/".join(parts[:depth])):
                return True
        return self._dir_excluded(rel) if is_dir else self._decide(rel, False)

    def is_excluded(self, path: Path | str, is_dir: Optional[bool] = None) -> bool:
        rel = self.relative(path)
        if rel is None:
            return False
        if is_dir is None:
            is_dir = (self.root / rel).is_dir() if rel else True
        return self.excluded_rel(rel, is_dir)

    def walk(self, start: Path | str | None = None) -> Iterator[Path]:
        """Yield every non-excluded file under ``start`` (default: the root), sorted."""
        top = Path(start) if start is not None else self.root
        if not top.is_absolute():
            top = self.root / top
        top_rel = self.relative(top)
        if top_rel is None or (top_rel and self.excluded_rel(top_rel, True)):
            return
        for current, dirs, files in os.walk(str(top)):
            current_rel = self.relative(current) or ""
            prefix = f"{current_rel}/" if current_rel else ""
            dirs[:] = sorted(d for d in dirs if not self._dir_excluded(prefix + d))
            for name in sorted(files):
                if not self._decide(prefix + name, False):
                    yield Path(current) / name

    def describe(self) -> str:
        """One line for the audit header."""
        extras = []
        if self.gitignore:
            extras.append(".gitignore")
        if self.config_file is not None:
            extras.append(USER_IGNORE_FILE)
        if self.user_patterns:
            extras.append(f"{len(self.user_patterns)} user pattern(s)")
        return "Excluded: defaults" + ("".join(f" + {item}" for item in extras))


# --------------------------------------------------------------------------
# Command line
# --------------------------------------------------------------------------

def add_exclusion_arguments(parser) -> None:
    """Add ``--exclude`` (repeatable) and ``--no-gitignore`` to an argparse parser."""
    parser.add_argument(
        "--exclude", action="append", default=[], metavar="PATTERN",
        help="Exclude paths matching this .gitignore-style pattern, relative to the project "
             f"root (repeatable; also read from {USER_IGNORE_FILE})",
    )
    parser.add_argument(
        "--no-gitignore", action="store_true",
        help="Do not read the project's .gitignore files",
    )


def path_filter_from_args(root: Path | str, args, **kwargs) -> PathFilter:
    return PathFilter(
        root,
        user_patterns=list(getattr(args, "exclude", None) or []),
        gitignore=not getattr(args, "no_gitignore", False),
        **kwargs,
    )


# --------------------------------------------------------------------------
# Reading sources and server-rendered templates
# --------------------------------------------------------------------------

def read_text(path: Path | str) -> str:
    """Read a source file as UTF-8 (BOM stripped), never failing on odd bytes."""
    with open(path, "r", encoding="utf-8-sig", errors="replace") as handle:
        return handle.read()


_PHP_OPEN = re.compile(r"<\?(?:php\b|=)?", re.IGNORECASE)
_HEREDOC = re.compile(r"<<<[ \t]*([\"']?)([A-Za-z_]\w*)\1[^\n]*\n")
_BLADE_COMMENT = re.compile(r"\{\{--.*?--\}\}", re.DOTALL)
_MARKUP_TAG = re.compile(r"<(?:!doctype\b|[A-Za-z][\w:.-]*(?=[\s/>]))", re.IGNORECASE)


def _skip_quoted(text: str, i: int) -> int:
    quote = text[i]
    i += 1
    while i < len(text):
        if text[i] == "\\":
            i += 2
            continue
        if text[i] == quote:
            return i + 1
        i += 1
    return len(text)


def _php_block_end(text: str, i: int) -> int:
    """Index just after the ``?>`` closing the PHP block that starts at ``i``."""
    n = len(text)
    while i < n:
        if text.startswith("?>", i):
            return i + 2
        char = text[i]
        if char in "'\"`":
            i = _skip_quoted(text, i)
        elif text.startswith("<<<", i):
            match = _HEREDOC.match(text, i)
            if not match:
                i += 3
                continue
            closing = re.compile(r"^[ \t]*" + re.escape(match.group(2)) + r"\b", re.MULTILINE)
            found = closing.search(text, match.end())
            i = found.end() if found else n
        elif text.startswith("/*", i):
            end = text.find("*/", i + 2)
            i = n if end == -1 else end + 2
        elif char == "#" or text.startswith("//", i):
            while i < n and text[i] != "\n" and not text.startswith("?>", i):
                i += 1
        else:
            i += 1
    return n


def mask_server_code(text: str) -> str:
    """Replace PHP blocks with ``{...}`` (keeping line numbers) and drop Blade comments."""
    text = _BLADE_COMMENT.sub(lambda m: "\n" * m.group(0).count("\n"), text)
    out: List[str] = []
    pos = 0
    while True:
        match = _PHP_OPEN.search(text, pos)
        if not match:
            out.append(text[pos:])
            break
        out.append(text[pos:match.start()])
        end = _php_block_end(text, match.end())
        out.append(SERVER_CODE_MARKER + "\n" * text.count("\n", match.start(), end))
        pos = end
    return "".join(out)


def is_server_template_suffix(path: Path | str) -> bool:
    return Path(path).suffix.lower() in SERVER_TEMPLATE_SUFFIXES


def has_markup(text: str) -> bool:
    """True when the text contains an HTML/XML tag (call it on masked text)."""
    return _MARKUP_TAG.search(text) is not None


def read_markup_source(path: Path | str) -> Optional[str]:
    """Source of a page-like file, with server code masked.

    Returns None for a ``.php``/``.phtml`` file that holds no markup once its
    PHP code is removed (a controller, model or config file, not a view).
    """
    text = read_text(path)
    if not is_server_template_suffix(path):
        return text
    masked = mask_server_code(text)
    return masked if has_markup(masked) else None


# --------------------------------------------------------------------------
# External commands
# --------------------------------------------------------------------------

PIPE_GRACE_SECONDS = 5   # bounded wait for the output pipes once the process ended or was killed
TREE_KILL_SECONDS = 20   # bounded wait for the tool that kills the process tree
_ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)")
_CMD_METACHARACTERS = frozenset("&|<>^()")


class CommandResult(NamedTuple):
    """Outcome of ``run_external``. ``returncode`` is None only when a killed process could not be reaped."""

    returncode: Optional[int]
    stdout: str
    stderr: str
    timed_out: bool


def strip_ansi(text: str) -> str:
    """Remove terminal colour and cursor sequences (some tools colour piped output on Windows)."""
    return _ANSI_ESCAPE.sub("", text)


def command_env(extra: Optional[Mapping[str, str]] = None) -> Dict[str, str]:
    """Environment of every external command: non-interactive and without colours."""
    env = dict(os.environ)
    if not env.get("CI"):
        env["CI"] = "1"  # vitest, jest, react-scripts, npx: run once, no watch mode, no prompt
    env["NO_COLOR"] = "1"
    env["FORCE_COLOR"] = "0"
    if extra:
        env.update(extra)
    return env


def windows_command_line(args: Sequence[str]) -> str:
    """Command line for a ``.cmd``/``.bat`` shim: also quotes arguments holding cmd.exe metacharacters.

    ``subprocess.list2cmdline`` quotes only white space, so ``http://host/?a=1&b=2`` given to
    ``lighthouse.cmd`` was cut at the ``&`` by cmd.exe, which then ran ``b=2 ...`` as a command.
    """
    parts: List[str] = []
    for arg in args:
        quoted = subprocess.list2cmdline([arg])
        if quoted == arg and _CMD_METACHARACTERS.intersection(arg):
            trailing = len(arg) - len(arg.rstrip("\\"))
            quoted = '"' + arg + "\\" * trailing + '"'
        parts.append(quoted)
    return " ".join(parts)


def _descendant_pids(pid: int) -> List[int]:
    """POSIX: every descendant of ``pid``, read from ``ps`` (best effort; [] when ps is missing)."""
    try:
        listing = subprocess.run(
            ["ps", "-A", "-o", "pid=", "-o", "ppid="], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, timeout=5, check=False,
        ).stdout.decode("ascii", "replace")
    except (OSError, subprocess.SubprocessError):
        return []
    children: Dict[int, List[int]] = {}
    for line in listing.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            children.setdefault(int(parts[1]), []).append(int(parts[0]))
    found: List[int] = []
    queue = [pid]
    while queue:
        for child in children.get(queue.pop(), []):
            if child not in found:
                found.append(child)
                queue.append(child)
    return found


def kill_process_tree(proc: "subprocess.Popen[bytes]") -> None:
    """Kill ``proc`` and every process it started. Call it only while ``proc`` is not reaped."""
    if os.name == "nt":
        root = os.environ.get("SystemRoot") or os.environ.get("WINDIR") or r"C:\Windows"
        taskkill = os.path.join(root, "System32", "taskkill.exe")
        try:
            subprocess.run(
                [taskkill if os.path.isfile(taskkill) else "taskkill", "/F", "/T", "/PID", str(proc.pid)],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                timeout=TREE_KILL_SECONDS, check=False,
            )
        except (OSError, subprocess.SubprocessError):
            pass
    else:
        # The command leads its own session: its group covers the usual tree. A nested
        # run_external (an audit started by an orchestrator) leads another session, so the
        # descendants are also killed one by one.
        descendants = _descendant_pids(proc.pid)
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except OSError:
            pass
        for pid in descendants:
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass
    try:
        proc.kill()
    except OSError:
        pass


def _pump(stream, sink: List[bytes]) -> None:
    """Reader thread: collect a pipe chunk by chunk (so a timeout keeps what was printed)."""
    try:
        descriptor = stream.fileno()
        while True:
            chunk = os.read(descriptor, 65536)
            if not chunk:
                break
            sink.append(chunk)
    except (OSError, ValueError):
        pass
    finally:
        try:
            stream.close()
        except OSError:
            pass


def _decode_output(chunks: List[bytes]) -> str:
    text = b"".join(list(chunks)).decode("utf-8", errors="replace")
    return text.replace("\r\n", "\n").replace("\r", "\n")


def run_external(
    cmd: Union[Sequence[str], str],
    cwd: Union[Path, str, None] = None,
    timeout: Optional[float] = None,
    env: Optional[Mapping[str, str]] = None,
    merge_stderr: bool = False,
) -> CommandResult:
    """Run an external command without a shell, never interactive, with a real time limit.

    ``env`` holds extra variables added to ``command_env()``. With ``merge_stderr`` the two
    streams are read as one (in the order the tool wrote them) and ``stderr`` is empty.
    On timeout the whole process tree is killed and the result has ``timed_out`` True and
    the output produced so far. ``OSError`` (``FileNotFoundError`` included) is raised when
    the command cannot start.
    """
    options: Dict[str, object] = {}
    if os.name == "nt":
        options["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    else:
        options["start_new_session"] = True
    proc = subprocess.Popen(  # an argument list (or a quoted Windows command line), never a shell
        cmd if isinstance(cmd, str) else [str(part) for part in cmd],
        cwd=str(cwd) if cwd is not None else None,
        env=command_env(env),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT if merge_stderr else subprocess.PIPE,
        **options,  # type: ignore[arg-type]
    )
    sinks: Dict[str, List[bytes]] = {"stdout": [], "stderr": []}
    readers: List[threading.Thread] = []
    for name in ("stdout", "stderr"):
        stream = getattr(proc, name)
        if stream is not None:
            reader = threading.Thread(target=_pump, args=(stream, sinks[name]), daemon=True)
            reader.start()
            readers.append(reader)

    timed_out = False
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        kill_process_tree(proc)
    except BaseException:  # Ctrl+C and the like: never leave the command running
        kill_process_tree(proc)
        raise

    # A process that outlived the command and still holds a pipe must not block the audit.
    # The reader of a pipe that is still held goes on alone and closes it when it ends.
    deadline = time.monotonic() + PIPE_GRACE_SECONDS
    for reader in readers:
        reader.join(max(0.0, deadline - time.monotonic()))
    returncode = proc.poll()
    if returncode is None:
        try:
            returncode = proc.wait(timeout=PIPE_GRACE_SECONDS)
        except subprocess.TimeoutExpired:
            returncode = None
    return CommandResult(returncode, _decode_output(sinks["stdout"]), _decode_output(sinks["stderr"]), timed_out)
