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
  defaults of ``audit_common``). A submodule (a gitlink, mode 160000) counts
  with the files of its checkout, by the same rule and under its path, so a
  local edit inside it and a checkout of another revision change the
  fingerprint; a submodule that is not checked out counts with the commit the
  index records for it.
  A nested repository that is not a submodule (an untracked folder with its
  own ``.git``, such as a clone that was never added) counts the same way, with
  the files git lists in it (tracked plus untracked, not ignored), under its
  path;
* no git: every file the shared defaults and the project's ``.gitignore``
  files do not exclude. The same walk is used when the project lies inside
  another repository that ignores the project folder (a project kept under an
  ignored ``temp/`` of some other checkout), or when git lists no file at all
  for a project that is not the repository root: git would hash nothing, and
  an edit would leave the fingerprint unchanged.

The executable bit counts too. A file whose git index mode is ``100755`` (for
an untracked file or without git: a file with an execute bit, on a POSIX file
system only; Windows has none) is hashed as ``<file sha256>+x  <path>``, so
``chmod +x`` or ``git update-index --chmod=+x`` changes the fingerprint. Any
other file keeps the plain line: the fingerprint of a project without
executable files does not change with this rule.

A folder whose files cannot be listed (a nested repository that git cannot
read, a folder the walk cannot open) is never left out in silence: the
fingerprint is then ``n/a (code state unavailable: ...)``, naming the folder,
and ``--expect`` prints ``Compare: DIFFERENT`` (exit 1), because nothing can
be compared.

Never part of the fingerprint: ``.redevkit/``, ``specs/`` and the agent folders
(``.claude/``, ``.agents/``, ``.codex/``) at the project root, because reports
and memory are written after a run and must not make the code look changed.
When the file system of the project folder ignores case (Windows, macOS by
default; probed by ``ignores_case``) these names match in any case: ``SPECs/``
there is the ``specs/`` folder the kit writes to. On a case-sensitive file
system ``Specs/`` is another folder, and it is code.

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
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

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
POSIX_MODES = os.name != "nt"  # Windows file systems have no execute bit
EXECUTABLE_MARK = "+x"  # appended to the file hash: a 64-digit hex hash cannot end with it


class UnlistedFolder(Exception):
    """A project folder whose files cannot be listed: the code state is unavailable."""


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


def ignores_case(project: Path) -> bool:
    """True when the file system of the project folder ignores case (Windows, macOS by default).

    Probed on the project itself, not assumed from the OS (a Windows folder can be
    case-sensitive, a Linux volume can ignore case): a root entry whose name with the case
    swapped names the same file. A root without a cased entry holds no reserved folder.
    """
    try:
        names = os.listdir(str(project))
    except OSError:
        return False
    for name in names:
        swapped = name.swapcase()
        if swapped == name or swapped.swapcase() != name:
            continue  # no letter to swap, or a swap that changes the length
        try:
            return os.path.samefile(str(project / name), str(project / swapped))
        except OSError:
            return False  # the swapped name does not exist: case-sensitive
    return False


def _reserved(rel: str, ignore_case: bool = False) -> bool:
    """True for a path inside a reserved root folder (in any case when the volume ignores case)."""
    first = rel.split("/", 1)[0]
    return (first.lower() if ignore_case else first) in RESERVED_ROOT_DIRS


def _split_z(value: bytes) -> List[str]:
    return [item.decode("utf-8", errors="surrogateescape") for item in value.split(b"\0") if item]


def _index_entries(project: Path) -> Dict[str, Tuple[str, str]]:
    """Every index entry: path -> (mode, object id). Modes: ``100644``, ``100755`` (executable),
    ``120000`` (symlink), ``160000`` (submodule, whose object id is the recorded commit)."""
    entries: Dict[str, Tuple[str, str]] = {}
    for item in _split_z(_git(project, "ls-files", "-z", "--stage") or b""):
        meta, _, rel = item.partition("\t")
        fields = meta.split()
        if len(fields) == 3:
            entries[rel] = (fields[0], fields[1])
    return entries


def _gitlinks(project: Path) -> Dict[str, str]:
    """Submodule entries of the index (mode 160000): path -> recorded commit."""
    return {rel: oid for rel, (mode, oid) in _index_entries(project).items() if mode == "160000"}


def _posix_executable(path: Path) -> bool:
    """True for a regular file with an execute bit, on a file system that has one (POSIX)."""
    if not POSIX_MODES:
        return False
    try:
        mode = os.lstat(str(path)).st_mode
    except OSError:
        return False
    return stat.S_ISREG(mode) and bool(mode & 0o111)


def _add_nested(project: Path, rel: str, files: Set[str], gitlinks: Optional[Dict[str, str]],
                executables: Optional[Set[str]]) -> bool:
    """Add the files of the repository checked out at ``rel`` (a submodule or a nested
    repository) under its path; False when git cannot list them."""
    inner_links: Dict[str, str] = {}
    inner_executables: Set[str] = set()
    inner = git_files(project / rel, gitlinks=inner_links, top=False, executables=inner_executables)
    if inner is None:
        return False
    files.update(f"{rel}/{path}" for path in inner)
    if gitlinks is not None:
        gitlinks.update({f"{rel}/{path}": commit for path, commit in inner_links.items()})
    if executables is not None:
        executables.update(f"{rel}/{path}" for path in inner_executables)
    return True


def git_files(project: Path, ignore_case: bool = False, gitlinks: Optional[Dict[str, str]] = None,
              top: bool = True, executables: Optional[Set[str]] = None) -> Optional[List[str]]:
    """Tracked files plus untracked, not ignored, not generated files; None outside git.

    A checked-out submodule contributes its own files (the same rule, recursively) under its
    path. A submodule that is not checked out stays one entry, and ``gitlinks`` (when given)
    receives its recorded commit for ``tree_fingerprint``. An untracked folder with its own
    ``.git`` (a nested repository that is not a submodule; git lists it as one ``lib/``
    entry) contributes its files the same way. An untracked folder whose files git cannot
    list raises ``UnlistedFolder``: it is never dropped in silence. ``executables`` (when
    given) receives the executable files: index mode ``100755`` for a tracked file, the
    execute bit (POSIX only) for an untracked one. The reserved root folders apply only to
    the project itself (``top``), never inside a submodule or a nested repository.
    """
    tracked = _git(project, "ls-files", "-z", "--cached")
    untracked = _git(project, "ls-files", "-z", "--others", "--exclude-standard")
    if tracked is None or untracked is None:
        return None
    index = _index_entries(project)
    generated = PathFilter(project, gitignore=False, config=False)
    files: Set[str] = set()
    for rel in _split_z(tracked):
        if top and _reserved(rel, ignore_case):
            continue
        mode, oid = index.get(rel, ("", ""))
        if mode == "160000":
            checked_out = (project / rel / ".git").exists()
            if checked_out and _add_nested(project, rel, files, gitlinks, executables):
                continue
            if gitlinks is not None:
                gitlinks[rel] = oid
        elif mode == "100755" and executables is not None:
            executables.add(rel)
        files.add(rel)
    for rel in _split_z(untracked):
        folder = rel.endswith("/")
        rel = rel.rstrip("/")
        if (top and _reserved(rel, ignore_case)) or generated.excluded_rel(rel, folder):
            continue
        if folder:
            if (project / rel / ".git").exists() and _add_nested(project, rel, files, gitlinks, executables):
                continue
            raise UnlistedFolder(f"{rel}/ (git fails in this nested repository)")
        if executables is not None and _posix_executable(project / rel):
            executables.add(rel)
        files.add(rel)
    return sorted(files)


def walked_files(project: Path, ignore_case: bool = False, executables: Optional[Set[str]] = None) -> List[str]:
    """Every file the shared defaults and the .gitignore files do not exclude (no git).

    ``executables`` (when given) receives the files with an execute bit (POSIX only). A
    folder that cannot be opened raises ``UnlistedFolder``.
    """
    path_filter = PathFilter(project, config=False)
    errors: List[OSError] = []
    files = []
    for path in path_filter.walk(onerror=errors.append):
        rel = path_filter.relative(path)
        if rel and not _reserved(rel, ignore_case):
            files.append(rel)
            if executables is not None and _posix_executable(path):
                executables.add(rel)
    for error in errors:
        rel = path_filter.relative(error.filename) if error.filename else None
        if rel is None or not _reserved(rel, ignore_case):
            raise UnlistedFolder(f"{rel if rel is not None else error.filename}/ ({error.strerror or error})")
    return sorted(files)


def _file_digest(path: Path) -> Optional[str]:
    """SHA-256 of a file's bytes (of the link target for a symlink); None when it is not a file."""
    try:
        if path.is_symlink():
            return hashlib.sha256(b"link:" + os.readlink(str(path)).encode("utf-8", "surrogateescape")).hexdigest()
        if not path.is_file():
            return None  # deleted from the working tree, or a folder
        digest = hashlib.sha256()
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(CHUNK), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError:
        return None


def tree_fingerprint(project: Path, files: Sequence[str], gitlinks: Optional[Dict[str, str]] = None,
                     executables: Optional[Set[str]] = None) -> Tuple[str, int]:
    """(fingerprint, number of files hashed) for the given relative posix paths.

    A path in ``gitlinks`` (a submodule that is not checked out) is hashed by its recorded
    commit. A path in ``executables`` gets ``+x`` after its hash; the line of any other path
    is the same as before the executable bit counted.
    """
    total = hashlib.sha256()
    count = 0
    for rel in files:
        if gitlinks and rel in gitlinks:
            digest: Optional[str] = hashlib.sha256(b"gitlink:" + gitlinks[rel].encode("ascii", "replace")).hexdigest()
        else:
            digest = _file_digest(project / rel)
        if digest is None:
            continue
        if executables and rel in executables:
            digest += EXECUTABLE_MARK
        total.update(f"{digest}  {rel}\n".encode("utf-8", "surrogateescape"))
        count += 1
    return PREFIX + total.hexdigest(), count


def _changed(project: Path, ignore_case: bool = False) -> Optional[List[str]]:
    magic = "exclude,icase" if ignore_case else "exclude"  # the same matching as _reserved
    excludes = [f":({magic}){name}" for name in RESERVED_ROOT_DIRS if name != ".git"]
    status = _git(project, "status", "--porcelain", "--", ".", *excludes)
    if status is None:
        return None
    return [line for line in status.decode("utf-8", errors="replace").splitlines() if line.strip()]


def _repository_root(project: Path) -> bool:
    """True when ``project`` is the top folder of its git working tree."""
    top = _text(_git(project, "rev-parse", "--show-toplevel"))
    try:
        return bool(top) and os.path.samefile(top, str(project))
    except OSError:
        return False


def ignored_by_enclosing_repo(project: Path) -> bool:
    """True when ``project`` sits inside another repository's working tree that ignores it."""
    if _repository_root(project):
        return False
    return _git(project, "check-ignore", "-q", "--", ".") is not None  # exit 0: ignored


def compute(project: Path) -> Dict[str, Any]:
    """The code state of ``project`` as a dictionary (see the module docstring)."""
    in_git = _text(_git(project, "rev-parse", "--is-inside-work-tree")) == "true"
    enclosing_ignores = in_git and ignored_by_enclosing_repo(project)
    if enclosing_ignores:
        in_git = False  # the enclosing repository lists none of the project's files
    ignore_case = ignores_case(project)
    gitlinks: Dict[str, str] = {}
    executables: Set[str] = set()
    basis = "git"
    unlisted: Optional[str] = None
    try:
        files = git_files(project, ignore_case, gitlinks, executables=executables) if in_git else None
        if files == [] and not _repository_root(project):
            files = None  # a project inside a repository that lists nothing of it: walk instead
        if files is None:
            in_git = False
            basis = "walk"
            gitlinks, executables = {}, set()
            files = walked_files(project, ignore_case, executables)
    except UnlistedFolder as exc:
        unlisted, files = str(exc), []
    fingerprint, count = tree_fingerprint(project, files, gitlinks, executables)
    if unlisted is not None:
        fingerprint, count = f"n/a (code state unavailable: cannot list {unlisted})", 0

    state: Dict[str, Any] = {
        "script": "code_state",
        "project": str(project),
        "git": in_git,
        "basis": basis,
        "tree_fingerprint": fingerprint,
        "files": count,
    }
    if unlisted is not None:
        state["unavailable"] = f"cannot list {unlisted}"
    if in_git:
        head = _text(_git(project, "rev-parse", "--verify", "--quiet", "HEAD"))
        changed = _changed(project, ignore_case) or []
        state.update({
            "head": head or "none",
            "branch": _text(_git(project, "branch", "--show-current")) or "n/a (detached HEAD)",
            "working_tree": "dirty" if changed else "clean",
            "changed_files": changed,
        })
    else:
        state.update({
            "head": "n/a (ignored by the enclosing git repository)" if enclosing_ignores else "n/a (not a git repository)",
            "branch": "n/a",
            "working_tree": "n/a",
            "changed_files": [],
        })
    return state


def normalize_fingerprint(value: str) -> str:
    text = value.strip().strip("`").strip().lower()
    return text if text.startswith(PREFIX) else PREFIX + text


def same_state(expected: str, current: str) -> bool:
    """True when both fingerprints are equal; an ``n/a`` one is never the same as anything."""
    return current.startswith(PREFIX) and expected == current


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
        state["same"] = same_state(expected, state["tree_fingerprint"])

    if args.json:
        print(json.dumps(state, indent=2, ensure_ascii=False))
    else:
        print_state(state)
        if args.expect is not None:
            print(f"Expected: {state['expected']}")
            unavailable = f" (code state unavailable: {state['unavailable']})" if state.get("unavailable") else ""
            print("Compare: SAME" if state["same"] else f"Compare: DIFFERENT{unavailable}")
    if args.expect is not None and not state["same"]:
        return EXIT_DIFFERENT
    return EXIT_SAME


if __name__ == "__main__":
    raise SystemExit(main())
