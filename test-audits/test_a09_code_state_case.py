"""A09: the specs folder is excluded from the code state in any case where the volume ignores case.

Bug: ``_reserved`` compared the first path segment with ``specs`` literally, and ``_changed``
used the case-sensitive pathspec ``:(exclude)specs``. A project whose root folder is spelled
``SPECs/`` (Windows, macOS by default) hashed every spec and report: writing the test report
(``specs/001-one/test-report.md``, which lands in ``SPECs/``) made the code state DIFFERENT
right after it was recorded.

Decision: the names match in any case only when the project folder's file system ignores
case (probed with ``ignores_case``). On a case-sensitive volume ``Specs/`` is a different
folder from the ``specs/`` the kit writes, and it may hold code.
"""
from __future__ import annotations

import shutil
import subprocess
import unittest
from unittest import mock

from audit_helpers import TempProject, load_audit, run_main

code_state = load_audit("code_state")
GIT = shutil.which("git")


def git(project, *args: str) -> None:
    subprocess.run(
        [GIT, "-c", "user.name=test", "-c", "user.email=test@example.com", "-c", "commit.gpgsign=false", *args],
        cwd=str(project.root), stdin=subprocess.DEVNULL, capture_output=True, check=True, timeout=60,
    )


def case_insensitive_volume() -> bool:
    with TempProject() as project:
        project.write("Probe.txt", "x")
        return code_state.ignores_case(project.root)


IGNORES_CASE = case_insensitive_volume()


class TestA09ReservedNames(unittest.TestCase):
    def test_reserved_matching_follows_the_volume(self):
        for rel in ("SPECs/001/spec.md", "Specs/x.md", ".Claude/settings.json", ".REDEVKIT/memory/a.md"):
            with self.subTest(rel):
                self.assertTrue(code_state._reserved(rel, ignore_case=True))
                self.assertFalse(code_state._reserved(rel, ignore_case=False))
        self.assertTrue(code_state._reserved("specs/001/spec.md", ignore_case=False))
        self.assertFalse(code_state._reserved("src/specs/a.md", ignore_case=True))  # only at the root

    def test_probe_matches_the_file_system(self):
        with TempProject() as project:
            project.write("Probe.txt", "x")
            expected = (project.root / "pROBE.TXT").exists()
            self.assertEqual(code_state.ignores_case(project.root), expected)
        with TempProject() as project:
            self.assertFalse(code_state.ignores_case(project.root))  # nothing to probe
            project.write("123", "x")
            self.assertFalse(code_state.ignores_case(project.root))  # no letter to swap


@unittest.skipUnless(IGNORES_CASE, "the temporary folder is on a case-sensitive file system")
class TestA09CaseInsensitiveVolume(unittest.TestCase):
    @unittest.skipUnless(GIT, "git is not installed")
    def test_report_in_a_mixed_case_specs_folder_keeps_the_code_state(self):
        with TempProject() as project:
            git(project, "init", "-q", ".")
            project.write("app.py", "x = 1\n")
            project.write("SPECs/001-one/spec.md", "spec\n")
            git(project, "add", "-A")
            git(project, "commit", "-q", "-m", "base")
            before = code_state.compute(project.root)
            project.write("specs/001-one/test-report.md", "run\n")  # lands in SPECs/
            project.write("SPECs/001-one/verification.md", "run\n")
            after = code_state.compute(project.root)
            code, out = run_main(code_state, [str(project.root), "--expect", before["tree_fingerprint"]])
        self.assertEqual(before["files"], 1)  # app.py only
        self.assertEqual(before["tree_fingerprint"], after["tree_fingerprint"])
        self.assertEqual(after["changed_files"], [])  # :(exclude,icase) leaves the reports out
        self.assertEqual(code, 0, out)
        self.assertIn("Compare: SAME", out)

    def test_no_git_walk_excludes_the_mixed_case_specs_folder(self):
        with TempProject() as project:
            project.write("app.py", "x = 1\n")
            project.write("Specs/001-one/spec.md", "spec\n")
            before = code_state.compute(project.root)
            project.write("specs/001-one/test-report.md", "run\n")
            after = code_state.compute(project.root)
        self.assertEqual(before["basis"], "walk")
        self.assertEqual(before["files"], 1)
        self.assertEqual(before["tree_fingerprint"], after["tree_fingerprint"])

    def test_code_still_changes_the_code_state(self):
        with TempProject() as project:
            project.write("app.py", "x = 1\n")
            project.write("SPECs/001-one/spec.md", "spec\n")
            before = code_state.compute(project.root)["tree_fingerprint"]
            project.write("app.py", "x = 2\n")
            self.assertNotEqual(before, code_state.compute(project.root)["tree_fingerprint"])


class TestA09CaseSensitiveVolume(unittest.TestCase):
    def test_other_spelling_is_code_on_a_case_sensitive_volume(self):
        # Simulated: on such a volume Specs/ is not the folder the kit writes to.
        with TempProject() as project, mock.patch.object(code_state, "ignores_case", return_value=False):
            project.write("app.py", "x = 1\n")
            project.write("Specs/a_spec.rb", "it 'works'\n")
            before = code_state.compute(project.root)
            project.write("Specs/a_spec.rb", "it 'still works'\n")
            after = code_state.compute(project.root)
        self.assertEqual(before["files"], 2)
        self.assertNotEqual(before["tree_fingerprint"], after["tree_fingerprint"])


if __name__ == "__main__":
    unittest.main()
