"""B08 and B09: nested repositories and the executable bit count in the code state.

Bugs:

* B08: ``git ls-files --others`` lists an untracked folder with its own ``.git`` (a nested
  repository that is not a submodule, such as a clone never added) as one ``lib/`` entry.
  ``_file_digest`` returned None for the folder and it was dropped: editing
  ``lib/component.py`` kept ``Files hashed: 1`` and ``Compare: SAME``.
* B09: each line was ``<sha256>  <path>``, without the mode: ``git update-index
  --chmod=+x run.sh`` (100644 -> 100755) kept ``Compare: SAME``, before and after the commit.

Decisions: a nested repository counts with its own files (tracked plus untracked, not
ignored), under its path, like a checked-out submodule; a folder that cannot be listed makes
the fingerprint ``n/a`` (never SAME) instead of being dropped. An executable file (index
mode 100755; the execute bit for untracked files and without git, on POSIX only) gets
``+x`` after its hash; every other line is unchanged, so a project without executable files
keeps the fingerprint the previous version computed.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import unittest
from pathlib import Path
from unittest import mock

from audit_helpers import TempProject, load_audit, run_main

code_state = load_audit("code_state")
GIT = shutil.which("git")


def git(cwd: Path, *args: str) -> str:
    done = subprocess.run(
        [GIT, "-c", "user.name=test", "-c", "user.email=test@example.com", "-c", "commit.gpgsign=false",
         "-c", "init.defaultBranch=main", "-c", "core.autocrlf=false", *args],
        cwd=str(cwd), stdin=subprocess.DEVNULL, capture_output=True, check=True, timeout=60,
    )
    return done.stdout.decode("utf-8", "replace").strip()


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))


def plain_fingerprint(root: Path, files) -> str:
    """The fingerprint formula of the previous version: no mode in any line."""
    total = hashlib.sha256()
    for rel in sorted(files):
        total.update(f"{hashlib.sha256((root / rel).read_bytes()).hexdigest()}  {rel}\n".encode("utf-8"))
    return "sha256:" + total.hexdigest()


def compare(root: Path, expected: str):
    return run_main(code_state, [str(root), "--expect", expected])


@unittest.skipUnless(GIT, "git is not installed")
class TestB08NestedRepository(unittest.TestCase):
    def setUp(self):
        self._project = TempProject()
        self.root = self._project.__enter__().root
        self.addCleanup(self._project.__exit__, None, None, None)
        write(self.root / "app.py", "import lib\n")
        git(self.root, "init", "-q", ".")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "app")
        self.lib = self.root / "lib"
        write(self.lib / "component.py", "value = 1\n")
        write(self.lib / ".gitignore", "*.log\n")
        git(self.lib, "init", "-q", ".")
        git(self.lib, "add", "-A")
        git(self.lib, "commit", "-q", "-m", "lib")
        self.base = code_state.compute(self.root)

    def test_nested_repository_files_are_hashed_under_its_path(self):
        self.assertEqual(self.base["files"], 3)  # app.py, lib/.gitignore, lib/component.py
        files = code_state.git_files(self.root)
        self.assertEqual(files, ["app.py", "lib/.gitignore", "lib/component.py"])
        self.assertEqual(self.base["tree_fingerprint"], plain_fingerprint(self.root, files))

    def test_edit_inside_the_nested_repository_changes_the_fingerprint(self):
        write(self.lib / "component.py", "value = 2\n")
        code, out = compare(self.root, self.base["tree_fingerprint"])
        self.assertEqual(code, 1, out)
        self.assertIn("Compare: DIFFERENT", out)
        write(self.lib / "component.py", "value = 1\n")
        self.assertEqual(compare(self.root, self.base["tree_fingerprint"])[0], 0)

    def test_untracked_and_ignored_files_of_the_nested_repository(self):
        write(self.lib / "debug.log", "ignored by lib/.gitignore\n")
        self.assertEqual(code_state.compute(self.root)["tree_fingerprint"], self.base["tree_fingerprint"])
        write(self.lib / "new.py", "x = 1\n")
        self.assertNotEqual(code_state.compute(self.root)["tree_fingerprint"], self.base["tree_fingerprint"])

    def test_nested_repository_without_commits(self):
        other = self.root / "tool"
        write(other / "main.py", "print(1)\n")
        git(other, "init", "-q", ".")
        state = code_state.compute(self.root)
        self.assertEqual(state["files"], 4)
        write(other / "main.py", "print(2)\n")
        self.assertNotEqual(code_state.compute(self.root)["tree_fingerprint"], state["tree_fingerprint"])

    def test_nested_repository_git_cannot_read_makes_the_state_unavailable(self):
        (self.lib / ".git" / "index").write_bytes(b"garbage")  # git ls-files fails inside lib/
        state = code_state.compute(self.root)
        self.assertTrue(state["tree_fingerprint"].startswith("n/a (code state unavailable: cannot list lib/"))
        self.assertIn("lib/", state["unavailable"])
        code, out = compare(self.root, self.base["tree_fingerprint"])
        self.assertEqual(code, 1, out)
        self.assertIn("Compare: DIFFERENT (code state unavailable: cannot list lib/", out)
        code, out = compare(self.root, state["tree_fingerprint"])  # n/a is never the same, not even as itself
        self.assertEqual(code, 1, out)


class TestB08UnlistedFolderWithoutGit(unittest.TestCase):
    def test_folder_the_walk_cannot_open_makes_the_state_unavailable(self):
        real_walk = os.walk

        def walk(top, *args, onerror=None, **kwargs):
            if onerror is not None:
                onerror(PermissionError(13, "Permission denied", os.path.join(str(top), "secret")))
            return real_walk(top, *args, onerror=onerror, **kwargs)

        with TempProject() as project:
            write(project.root / "a.py", "a = 1\n")
            with mock.patch("os.walk", walk):
                state = code_state.compute(project.root)
        self.assertEqual(state["basis"], "walk")
        self.assertEqual(state["tree_fingerprint"], "n/a (code state unavailable: cannot list secret/ (Permission denied))")


@unittest.skipUnless(GIT, "git is not installed")
class TestB09ExecutableBit(unittest.TestCase):
    def test_chmod_in_the_index_changes_the_fingerprint(self):
        with TempProject() as project:
            write(project.root / "run.sh", "#!/bin/sh\necho ok\n")
            git(project.root, "init", "-q", ".")
            git(project.root, "add", "-A")
            git(project.root, "commit", "-q", "-m", "run")
            base = code_state.compute(project.root)["tree_fingerprint"]
            self.assertEqual(base, plain_fingerprint(project.root, ["run.sh"]))
            git(project.root, "update-index", "--chmod=+x", "run.sh")
            executable = code_state.compute(project.root)["tree_fingerprint"]
            code, out = compare(project.root, base)
            self.assertEqual(code, 1, out)
            git(project.root, "commit", "-q", "-m", "chmod")
            self.assertEqual(code_state.compute(project.root)["tree_fingerprint"], executable)  # a commit after the run
            self.assertNotEqual(executable, base)
            git(project.root, "update-index", "--chmod=-x", "run.sh")
            self.assertEqual(code_state.compute(project.root)["tree_fingerprint"], base)

    def test_executable_file_of_a_nested_repository(self):
        with TempProject() as project:
            write(project.root / "app.py", "x = 1\n")
            git(project.root, "init", "-q", ".")
            lib = project.root / "lib"
            write(lib / "tool.sh", "#!/bin/sh\n")
            git(lib, "init", "-q", ".")
            git(lib, "add", "-A")
            base = code_state.compute(project.root)["tree_fingerprint"]
            git(lib, "update-index", "--chmod=+x", "tool.sh")
            self.assertNotEqual(code_state.compute(project.root)["tree_fingerprint"], base)

    @unittest.skipUnless(os.name != "nt", "the execute bit of the file system exists on POSIX only")
    def test_untracked_and_walked_files_use_the_posix_execute_bit(self):
        with TempProject() as project:
            write(project.root / "run.sh", "#!/bin/sh\n")
            walked = code_state.compute(project.root)["tree_fingerprint"]
            (project.root / "run.sh").chmod(0o755)
            self.assertNotEqual(code_state.compute(project.root)["tree_fingerprint"], walked)
            git(project.root, "init", "-q", ".")
            untracked = code_state.compute(project.root)["tree_fingerprint"]
            (project.root / "run.sh").chmod(0o644)
            self.assertNotEqual(code_state.compute(project.root)["tree_fingerprint"], untracked)

    def test_untracked_and_walked_files_ask_for_the_execute_bit(self):
        # Any OS: the file system answer is simulated (on Windows it is always "no").
        executable = mock.patch.object(code_state, "_posix_executable", side_effect=lambda path: path.name == "run.sh")
        with TempProject() as project:
            write(project.root / "run.sh", "#!/bin/sh\n")
            plain = plain_fingerprint(project.root, ["run.sh"])
            with executable:
                walked = code_state.compute(project.root)["tree_fingerprint"]
            self.assertNotEqual(walked, plain)
            if GIT:
                git(project.root, "init", "-q", ".")
                with executable:
                    self.assertEqual(code_state.compute(project.root)["tree_fingerprint"], walked)  # untracked
                git(project.root, "add", "run.sh")  # tracked: the index mode (100644) decides
                with executable:
                    self.assertEqual(code_state.compute(project.root)["tree_fingerprint"], plain)

    @unittest.skipUnless(os.name == "nt", "Windows has no execute bit")
    def test_windows_file_system_has_no_execute_bit(self):
        with TempProject() as project:
            write(project.root / "run.sh", "#!/bin/sh\n")
            self.assertFalse(code_state._posix_executable(project.root / "run.sh"))


class TestB09SameFingerprintWithoutExecutables(unittest.TestCase):
    def test_walk_fingerprint_keeps_the_previous_formula(self):
        with TempProject() as project:
            write(project.root / "src/a.py", "a = 1\n")
            write(project.root / "README.md", "# x\n")
            state = code_state.compute(project.root)
            self.assertEqual(state["basis"], "walk")
            self.assertEqual(state["tree_fingerprint"], plain_fingerprint(project.root, ["README.md", "src/a.py"]))

    @unittest.skipUnless(GIT, "git is not installed")
    def test_git_fingerprint_keeps_the_previous_formula(self):
        with TempProject() as project:
            write(project.root / "src/a.py", "a = 1\n")
            write(project.root / "notes.txt", "untracked\n")
            git(project.root, "init", "-q", ".")
            git(project.root, "add", "src/a.py")
            self.assertEqual(code_state.compute(project.root)["tree_fingerprint"],
                             plain_fingerprint(project.root, ["notes.txt", "src/a.py"]))


if __name__ == "__main__":
    unittest.main()
