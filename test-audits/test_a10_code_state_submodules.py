"""A10: a change inside a git submodule changes the code state.

Bug: ``git ls-files`` lists a submodule as one gitlink entry (mode 160000); its path is a
folder, so ``_file_digest`` returned None and the entry was dropped. Editing a file of the
submodule, or checking out another revision in it, kept ``Compare: SAME``.

Decision: a checked-out submodule counts with its own files (same rule, recursively, under
its path); a submodule that is not checked out counts with the commit the index records.
The recorded commit of a checked-out submodule is not hashed, so committing a submodule bump
after a run does not change the code state (the content already did).
"""
from __future__ import annotations

import shutil
import subprocess
import unittest
from pathlib import Path

from audit_helpers import TempProject, load_audit, run_main

code_state = load_audit("code_state")
GIT = shutil.which("git")


def git(cwd: Path, *args: str) -> str:
    done = subprocess.run(
        [GIT, "-c", "user.name=test", "-c", "user.email=test@example.com", "-c", "commit.gpgsign=false",
         "-c", "protocol.file.allow=always", "-c", "init.defaultBranch=main", *args],
        cwd=str(cwd), stdin=subprocess.DEVNULL, capture_output=True, check=True, timeout=60,
    )
    return done.stdout.decode("utf-8", "replace").strip()


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@unittest.skipUnless(GIT, "git is not installed")
class TestA10Submodules(unittest.TestCase):
    def setUp(self):
        self._project = TempProject()
        tmp = self._project.__enter__().root
        self.addCleanup(self._project.__exit__, None, None, None)
        self.lib = tmp / "lib"
        self.main = tmp / "main"
        write(self.lib / "mod.py", "value = 1\n")
        git(self.lib, "init", "-q", ".")
        git(self.lib, "add", "-A")
        git(self.lib, "commit", "-q", "-m", "lib v1")
        write(self.main / "app.py", "import vendorlib\n")
        git(self.main, "init", "-q", ".")
        git(self.main, "submodule", "add", "-q", self.lib.as_posix(), "vendorlib")
        git(self.main, "add", "-A")
        git(self.main, "commit", "-q", "-m", "main")
        self.base = code_state.compute(self.main)

    def compare(self):
        return run_main(code_state, [str(self.main), "--expect", self.base["tree_fingerprint"]])

    def test_the_submodule_files_are_hashed(self):
        self.assertEqual(self.base["files"], 3)  # .gitmodules, app.py, vendorlib/mod.py
        self.assertEqual(self.compare()[0], 0)

    def test_local_uncommitted_edit_inside_the_submodule(self):
        write(self.main / "vendorlib" / "mod.py", "value = 2\n")
        code, out = self.compare()
        self.assertEqual(code, 1, out)
        self.assertIn("Compare: DIFFERENT", out)

    def test_untracked_file_inside_the_submodule(self):
        write(self.main / "vendorlib" / "extra.py", "x = 1\n")
        self.assertEqual(self.compare()[0], 1)

    def test_checkout_of_another_revision_and_the_bump_commit(self):
        write(self.lib / "mod.py", "value = 3\n")
        git(self.lib, "commit", "-q", "-am", "lib v3")
        sub = self.main / "vendorlib"
        git(sub, "fetch", "-q", "origin")
        git(sub, "checkout", "-q", "FETCH_HEAD")
        code, out = self.compare()
        self.assertEqual(code, 1, out)  # another revision: different code
        moved = code_state.compute(self.main)["tree_fingerprint"]
        git(self.main, "add", "vendorlib")
        git(self.main, "commit", "-q", "-m", "bump vendorlib")
        self.assertEqual(code_state.compute(self.main)["tree_fingerprint"], moved)  # a commit after the run
        git(sub, "checkout", "-q", "HEAD~1")  # back to the first revision: the first content
        self.assertEqual(code_state.compute(self.main)["tree_fingerprint"], self.base["tree_fingerprint"])

    def test_submodule_not_checked_out_counts_with_its_recorded_commit(self):
        git(self.main, "submodule", "deinit", "-q", "-f", "vendorlib")
        not_checked_out = code_state.compute(self.main)
        self.assertEqual(not_checked_out["files"], 3)  # the gitlink entry stands for the submodule
        recorded = git(self.main, "rev-parse", "HEAD:vendorlib")
        other = git(self.main, "rev-parse", "HEAD")  # any other commit id
        self.assertNotEqual(recorded, other)
        git(self.main, "update-index", "--cacheinfo", f"160000,{other},vendorlib")
        self.assertNotEqual(code_state.compute(self.main)["tree_fingerprint"], not_checked_out["tree_fingerprint"])


if __name__ == "__main__":
    unittest.main()
