"""C1: the code state must change whenever the code changes, tracked or not.

Bug: the test and verify reports recorded two fingerprints built from
``git status --porcelain`` and ``git diff HEAD``. Neither reflects the content
of untracked files, so in a repository without commits (or for the new files
of a feature) an edit left both fingerprints unchanged: the verify command
reused a stale FAIL run after a debug fixed the code, and a stale PASS run
after the code changed. Piping git output also made the fingerprints differ
between shells, and a project without git had no code state at all.

``code_state.py`` hashes file contents instead.
"""
from __future__ import annotations

import json
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


def fingerprint(project) -> str:
    return code_state.compute(project.root)["tree_fingerprint"]


@unittest.skipUnless(GIT, "git is not installed")
class TestC1CodeStateGit(unittest.TestCase):
    def test_edit_of_untracked_file_changes_the_fingerprint_without_commits(self):
        with TempProject() as project:
            git(project, "init", "-q", ".")
            project.write("src/a.js", "export const add = (a, b) => a - b;\n")
            before = code_state.compute(project.root)
            project.write("src/a.js", "export const add = (a, b) => a + b;\n")
            after = code_state.compute(project.root)
        self.assertEqual(before["head"], "none")
        self.assertEqual(before["working_tree"], "dirty")
        self.assertNotEqual(before["tree_fingerprint"], after["tree_fingerprint"])

    def test_new_file_inside_an_untracked_folder_changes_the_fingerprint(self):
        with TempProject() as project:
            git(project, "init", "-q", ".")
            project.write("README.md", "base\n")
            git(project, "add", "-A")
            git(project, "commit", "-q", "-m", "base")
            project.write("src/feature/health.js", "bug\n")
            before = fingerprint(project)
            project.write("src/feature/other.js", "new\n")
            after = fingerprint(project)
        self.assertNotEqual(before, after)

    def test_commit_after_the_run_keeps_the_fingerprint(self):
        with TempProject() as project:
            git(project, "init", "-q", ".")
            project.write("src/a.js", "a\n")
            before = code_state.compute(project.root)
            git(project, "add", "-A")
            git(project, "commit", "-q", "-m", "after the test run")
            after = code_state.compute(project.root)
        self.assertEqual(before["tree_fingerprint"], after["tree_fingerprint"])
        self.assertNotEqual(before["head"], after["head"])
        self.assertEqual(after["working_tree"], "clean")

    def test_reports_memory_agent_folders_and_generated_output_are_not_code(self):
        with TempProject() as project:
            git(project, "init", "-q", ".")
            project.write("src/a.js", "a\n")
            before = fingerprint(project)
            project.write("specs/001-x/test-report.md", "run\n")
            project.write(".redevkit/memory/active.md", "state\n")
            project.write(".claude/settings.json", "{}\n")
            project.write(".agents/skills/x/SKILL.md", "x\n")
            project.write("node_modules/dep/index.js", "dep\n")
            project.write("dist/bundle.js", "built\n")
            project.write("coverage/lcov.info", "report\n")
            after = fingerprint(project)
        self.assertEqual(before, after)

    def test_tracked_file_in_a_build_named_folder_is_code(self):
        with TempProject() as project:
            git(project, "init", "-q", ".")
            project.write("build/webpack.config.js", "v1\n")
            git(project, "add", "-A")
            git(project, "commit", "-q", "-m", "base")
            before = fingerprint(project)
            project.write("build/webpack.config.js", "v2\n")
            after = fingerprint(project)
        self.assertNotEqual(before, after)

    def test_deleted_tracked_file_changes_the_fingerprint(self):
        with TempProject() as project:
            git(project, "init", "-q", ".")
            project.write("src/a.js", "a\n")
            project.write("src/b.js", "b\n")
            git(project, "add", "-A")
            git(project, "commit", "-q", "-m", "base")
            before = fingerprint(project)
            (project.root / "src" / "b.js").unlink()
            after = fingerprint(project)
        self.assertNotEqual(before, after)


class TestC1CodeStateWithoutGit(unittest.TestCase):
    def test_project_without_git_still_has_a_fingerprint(self):
        with TempProject() as project, mock.patch.object(code_state, "_git", return_value=None):
            project.write("src/a.py", "a = 1\n")
            project.write(".gitignore", "secret.txt\n")
            before = code_state.compute(project.root)
            project.write("secret.txt", "ignored\n")
            project.write("dist/out.js", "built\n")
            project.write("specs/001-x/verification.md", "run\n")
            same = code_state.compute(project.root)
            project.write("src/a.py", "a = 2\n")
            after = code_state.compute(project.root)
        self.assertEqual(before["head"], "n/a (not a git repository)")
        self.assertEqual(before["basis"], "walk")
        self.assertTrue(before["tree_fingerprint"].startswith("sha256:"))
        self.assertEqual(before["tree_fingerprint"], same["tree_fingerprint"])
        self.assertNotEqual(before["tree_fingerprint"], after["tree_fingerprint"])

    def test_expect_reports_same_and_different_with_exit_codes(self):
        with TempProject() as project, mock.patch.object(code_state, "_git", return_value=None):
            project.write("src/a.py", "a = 1\n")
            recorded = code_state.compute(project.root)["tree_fingerprint"]
            same_code, same_out = run_main(code_state, [str(project.root), "--expect", f"`{recorded}`"])
            project.write("src/a.py", "a = 2\n")
            diff_code, diff_out = run_main(code_state, [str(project.root), "--expect", recorded])
        self.assertEqual(same_code, 0)
        self.assertIn("Compare: SAME", same_out)
        self.assertEqual(diff_code, 1)
        self.assertIn("Compare: DIFFERENT", diff_out)

    def test_json_output_and_usage_error(self):
        with TempProject() as project, mock.patch.object(code_state, "_git", return_value=None):
            project.write("a.txt", "a\n")
            code, out = run_main(code_state, [str(project.root), "--json"])
            missing_code, _ = run_main(code_state, [str(project.root / "missing")])
        payload = json.loads(out)
        self.assertEqual(code, 0)
        self.assertEqual(payload["script"], "code_state")
        self.assertEqual(payload["files"], 1)
        self.assertEqual(missing_code, 2)


if __name__ == "__main__":
    unittest.main()
