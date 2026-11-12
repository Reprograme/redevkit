#!/usr/bin/env python3
"""Code state - a content fingerprint of the project's working tree.

Usage:
    python code_state.py [project] [--json] [--expect FINGERPRINT]

The test and verify commands record the output in their report; the verify and
deploy commands recompute it and compare. Two code states are the same when
their ``Tree fingerprint`` is equal.

The fingerprint is a SHA-256 over the sorted list of ``<file sha256>  <path>``
lines, so it changes whenever a file is added, removed, renamed or edited,
tracked by git or not. It never depends on the shell, on the commit history or
on git being present:

* git repository: every tracked file, plus every untracked file that git does
  not ignore and that is not dependency, build or report output (the shared
  defaults of ``audit_common``);
* no git: every file the shared defaults and the project's ``.gitignore``
  files do not exclude.

Never part of the fingerprint: ``.redevkit/``, ``specs/`` and the agent folders
(``.claude/``, ``.agents/``, ``.codex/``) at the project root, because reports
and memory are written after a run and must not make the code look changed.

Read-only: it runs ``git rev-parse``, ``git branch``, ``git status`` and
``git ls-files`` and reads files; it writes nothing.

Exit codes: 0 computed (with ``--expect``: same fingerprint), 1 with
``--expect``: different fingerprint, 2 usage error.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

from audit_common import PathFilter  # noqa: E402

EXIT_SAME, EXIT_DIFFERENT, EXIT_USAGE = 0, 1, 2
GIT_TIMEOUT = 60
CHUNK = 1024 * 1024
PREFIX = "sha256:"
# Root-level folders that hold reports, memory and agent files, never project code.
RESERVED_ROOT_DIRS: Tuple[str, ...] = (".redevkit", "specs", ".claude", ".agents", ".codex", ".git")
MAX_CHANGED_LISTED = 50


def utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)  # type: ignore[union-attr]
        except (AttributeError, ValueError, OSError):
            pass


def _git(project: Path, *args: str) -> Optional[bytes]:
    """Output of a read-only git command, or None when git is missing or the command fails."""
    git = shutil.which("git")
    if not git:
        return None
    try:
        proc = subprocess.run(
            [git, "-c", "core.quotepath=off", *args],
            cwd=str(project),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=GIT_TIMEOUT,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return proc.stdout if proc.returncode == 0 else None


def _text(value: Optional[bytes]) -> str:
    return (value or b"").decode("utf-8", errors="replace").strip()


def _reserved(rel: str) -> bool:
    return rel.split("/", 1)[0] in RESERVED_ROOT_DIRS


def _split_z(value: bytes) -> List[str]:
    return [item.decode("utf-8", errors="surrogateescape") for item in value.split(b"\0") if item]


def git_files(project: Path) -> Optional[List[str]]:
    """Tracked files plus untracked, not ignored, not generated files; None outside git."""
    tracked = _git(project, "ls-files", "-z", "--cached")
    untracked = _git(project, "ls-files", "-z", "--others", "--exclude-standard")
    if tracked is None or untracked is None:
        return None
    generated = PathFilter(project, gitignore=False, config=False)
    files = {rel for rel in _split_z(tracked) if not _reserved(rel)}
    for rel in _split_z(untracked):
        if not _reserved(rel) and not generated.excluded_rel(rel, False):
            files.add(rel)
    return sorted(files)


def walked_files(project: Path) -> List[str]:
    """Every file the shared defaults and the .gitignore files do not exclude (no git)."""
    path_filter = PathFilter(project, config=False)
    files = []
    for path in path_filter.walk():
        rel = path_filter.relative(path)
        if rel and not _reserved(rel):
            files.append(rel)
    return sorted(files)


def _file_digest(path: Path) -> Optional[str]:
    """SHA-256 of a file's bytes (of the link target for a symlink); None when it is not a file."""
    try:
        if path.is_symlink():
            return hashlib.sha256(b"link:" + os.readlink(str(path)).encode("utf-8", "surrogateescape")).hexdigest()
        if not path.is_file():
            return None  # deleted from the working tree, or a submodule directory
        digest = hashlib.sha256()
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(CHUNK), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError:
        return None


def tree_fingerprint(project: Path, files: Sequence[str]) -> Tuple[str, int]:
    """(fingerprint, number of files hashed) for the given relative posix paths."""
    total = hashlib.sha256()
    count = 0
    for rel in files:
        digest = _file_digest(project / rel)
        if digest is None:
            continue
        total.update(f"{digest}  {rel}\n".encode("utf-8", "surrogateescape"))
        count += 1
    return PREFIX + total.hexdigest(), count


def _changed(project: Path) -> Optional[List[str]]:
    excludes = [f":(exclude){name}" for name in RESERVED_ROOT_DIRS if name != ".git"]
    status = _git(project, "status", "--porcelain", "--", ".", *excludes)
    if status is None:
        return None
    return [line for line in status.decode("utf-8", errors="replace").splitlines() if line.strip()]


def compute(project: Path) -> Dict[str, Any]:
    """The code state of ``project`` as a dictionary (see the module docstring)."""
    in_git = _text(_git(project, "rev-parse", "--is-inside-work-tree")) == "true"
    files = git_files(project) if in_git else None
    basis = "git"
    if files is None:
        in_git = False
        basis = "walk"
        files = walked_files(project)
    fingerprint, count = tree_fingerprint(project, files)

    state: Dict[str, Any] = {
        "script": "code_state",
        "project": str(project),
        "git": in_git,
        "basis": basis,
        "tree_fingerprint": fingerprint,
        "files": count,
    }
    if in_git:
        head = _text(_git(project, "rev-parse", "--verify", "--quiet", "HEAD"))
        changed = _changed(project) or []
        state.update({
            "head": head or "none",
            "branch": _text(_git(project, "branch", "--show-current")) or "n/a (detached HEAD)",
            "working_tree": "dirty" if changed else "clean",
            "changed_files": changed,
        })
    else:
        state.update({
            "head": "n/a (not a git repository)",
            "branch": "n/a",
            "working_tree": "n/a",
            "changed_files": [],
        })
    return state


def normalize_fingerprint(value: str) -> str:
    text = value.strip().strip("`").strip().lower()
    return text if text.startswith(PREFIX) else PREFIX + text


def print_state(state: Dict[str, Any]) -> None:
    print("Code state")
    print(f"Commit (HEAD): {state['head']}")
    print(f"Branch: {state['branch']}")
    print(f"Working tree: {state['working_tree']}")
    changed = state["changed_files"]
    print(f"Changed files: {len(changed) if changed else 'none'}")
    for line in changed[:MAX_CHANGED_LISTED]:
        print(f"  {line}")
    if len(changed) > MAX_CHANGED_LISTED:
        print(f"  ... ({len(changed) - MAX_CHANGED_LISTED} more)")
    print(f"Tree fingerprint: {state['tree_fingerprint']}")
    source = "git ls-files (tracked + untracked, not ignored)" if state["basis"] == "git" else "directory walk"
    print(f"Files hashed: {state['files']} ({source}; reports, memory and agent folders excluded)")


def main(argv: Optional[Sequence[str]] = None) -> int:
    utf8_stdio()
    parser = argparse.ArgumentParser(description="Print the code state (content fingerprint) of a project")
    parser.add_argument("project", nargs="?", default=".")
    parser.add_argument("--json", action="store_true", help="Print only the JSON object")
    parser.add_argument(
        "--expect", metavar="FINGERPRINT",
        help="Compare with a recorded Tree fingerprint: prints SAME or DIFFERENT, exit 0 or 1",
    )
    args = parser.parse_args(argv)

    project = Path(args.project).resolve()
    if not project.is_dir():
        parser.error(f"Project directory does not exist: {project}")

    state = compute(project)
    if args.expect is not None:
        expected = normalize_fingerprint(args.expect)
        state["expected"] = expected
        state["same"] = expected == state["tree_fingerprint"]

    if args.json:
        print(json.dumps(state, indent=2, ensure_ascii=False))
    else:
        print_state(state)
        if args.expect is not None:
            print(f"Expected: {state['expected']}")
            print("Compare: SAME" if state["same"] else "Compare: DIFFERENT")
    if args.expect is not None and not state["same"]:
        return EXIT_DIFFERENT
    return EXIT_SAME


if __name__ == "__main__":
    raise SystemExit(main())
