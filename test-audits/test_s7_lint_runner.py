"""S7: lint_runner.py must report a missing tool as SKIPPED, not FAIL.

Bug: any project with pyproject.toml queued ruff and mypy; when they were not
installed the Lint check (required=True) failed the whole suite.
"""
from __future__ import annotations

import sys
import unittest
from unittest import mock

from audit_helpers import TempProject, load_audit, run_main

lint_runner = load_audit("lint_runner")


class TestS7LintRunner(unittest.TestCase):
    def test_missing_ruff_and_mypy_are_skipped(self):
        with TempProject("S7") as project, mock.patch.object(lint_runner, "python_tool", return_value=None):
            info = lint_runner.detect_project_type(project.root)
            code, out = run_main(lint_runner, [str(project.root)])
        self.assertEqual([linter["name"] for linter in info["linters"]], ["ruff", "mypy"])
        self.assertEqual(code, lint_runner.EXIT_SKIPPED)
        self.assertIn("SKIPPED (ruff is not installed)", out)
        self.assertIn("SKIPPED (mypy is not installed)", out)
        self.assertNotIn("[FAIL]", out)
        self.assertNotIn("[PASS]", out)

    def test_command_not_found_at_runtime_is_skipped(self):
        linter = {"name": "ruff", "cmd": ["definitely-not-a-real-linter-xyz", "check", "."], "skip_reason": None}
        with TempProject("S7") as project:
            result = lint_runner.run_linter(linter, project.root)
        self.assertEqual(result["status"], "skipped")

    def test_one_tool_present_one_missing_passes_with_skip_note(self):
        def fake_tool(name):
            return [sys.executable, "-c", "pass", "--"] if name == "ruff" else None

        with TempProject("S7") as project, mock.patch.object(lint_runner, "python_tool", side_effect=fake_tool):
            code, out = run_main(lint_runner, [str(project.root)])
        self.assertEqual(code, 0, out)
        self.assertIn("[PASS] ruff", out)
        self.assertIn("SKIPPED (mypy is not installed)", out)

    def test_npm_lint_uses_which(self):
        with TempProject() as project:
            project.write("package.json", '{"scripts": {"lint": "eslint ."}}')
            with mock.patch.object(lint_runner.shutil, "which", return_value="/fake/npm.cmd"):
                info = lint_runner.detect_project_type(project.root)
        self.assertEqual(info["linters"][0]["cmd"], ["/fake/npm.cmd", "run", "lint"])


if __name__ == "__main__":
    unittest.main()
