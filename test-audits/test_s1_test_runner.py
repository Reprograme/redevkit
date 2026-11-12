"""S1: test_runner.py must resolve npm with shutil.which (npm.cmd on Windows)
and call Python through sys.executable.

Bug: it ran ["npm", "test"] without shell/.cmd resolution, which raises
FileNotFoundError on Windows ("Command not found: npm"), and used "python"
instead of sys.executable.
"""
from __future__ import annotations

import os
import stat
import sys
import unittest
from pathlib import Path
from unittest import mock

from audit_helpers import TempProject, load_audit, run_main

test_runner = load_audit("test_runner")


def make_fake_npm(folder) -> None:
    """A fake npm on PATH: npm.cmd on Windows, an executable script elsewhere.

    It prints a test summary: a command whose output shows no test result is SKIPPED (S17).
    """
    if os.name == "nt":
        (folder / "npm.cmd").write_text(
            "@echo off\r\necho s1-tests-ok\r\necho Tests  2 passed (2)\r\nexit /b 0\r\n", encoding="utf-8")
    else:
        script = folder / "npm"
        script.write_text("#!/bin/sh\necho s1-tests-ok\necho 'Tests  2 passed (2)'\nexit 0\n", encoding="utf-8")
        script.chmod(script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


class TestS1TestRunner(unittest.TestCase):
    def test_npm_command_comes_from_shutil_which(self):
        fake = os.path.join("fake-bin", "npm.cmd")
        with TempProject("S1") as project, mock.patch.object(test_runner.shutil, "which", return_value=fake) as which:
            info = test_runner.detect_test_framework(project.root)
        which.assert_any_call("npm")
        self.assertEqual(info["cmd"], [fake, "test"])
        self.assertNotEqual(info["cmd"][0], "npm")

    def test_fake_npm_on_path_runs_without_shell(self):
        with TempProject("S1") as project:
            bin_dir = project.root / "fake-bin"
            bin_dir.mkdir()
            make_fake_npm(bin_dir)
            with mock.patch.dict(os.environ, {"PATH": str(bin_dir)}):
                code, out = run_main(test_runner, [str(project.root)])
        self.assertEqual(code, 0, out)
        self.assertIn("s1-tests-ok", out)
        self.assertIn("[PASS]", out)

    def test_python_project_uses_sys_executable(self):
        with TempProject() as project:
            project.write("requirements.txt", "requests==2.0.0\n")
            with mock.patch.object(test_runner, "python_module_available", return_value=True):
                info = test_runner.detect_test_framework(project.root)
            self.assertEqual(info["cmd"][:3], [sys.executable, "-m", "pytest"])
            with mock.patch.object(test_runner, "python_module_available", return_value=False):
                info = test_runner.detect_test_framework(project.root)
            self.assertEqual(info["cmd"][:3], [sys.executable, "-m", "unittest"])
        self.assertNotIn("python", [info["cmd"][0]])

    def test_missing_npm_is_skipped_not_passed(self):
        with TempProject("S1") as project, mock.patch.object(test_runner.shutil, "which", return_value=None):
            code, out = run_main(test_runner, [str(project.root)])
        self.assertEqual(code, test_runner.EXIT_SKIPPED)
        self.assertIn("SKIPPED (npm not found on PATH)", out)
        self.assertNotIn("[PASS]", out)

    def test_configured_pytest_missing_is_skipped(self):
        with TempProject() as project:
            project.write("pytest.ini", "[pytest]\n")
            with mock.patch.object(test_runner, "python_module_available", return_value=False):
                code, out = run_main(test_runner, [str(project.root)])
        self.assertEqual(code, test_runner.EXIT_SKIPPED)
        self.assertIn("SKIPPED (pytest is not installed", out)

    def test_no_shell_true_in_source(self):
        source = Path(test_runner.__file__).read_text(encoding="utf-8")
        self.assertNotIn("shell=True", source)


if __name__ == "__main__":
    unittest.main()
