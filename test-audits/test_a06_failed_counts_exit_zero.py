"""A06: failed tests in a recognised summary make the run FAIL, even when the command exits 0.

Bug: ``run_tests`` decided ``passed`` from ``returncode == 0`` plus a recognised summary and
never looked at ``tests_failed``. A declared command that loses the exit code (a wrapper
script ending in ``sys.exit(0)``) printed ``FAILED (failures=1)``, then ``[PASS] All tests
passed`` and ``Tests: 1 total, 0 passed, 1 failed``, with exit 0.
"""
from __future__ import annotations

import sys
import unittest
from unittest import mock

from audit_helpers import TempProject, load_audit, run_main

audit_common = load_audit("audit_common")
test_runner = load_audit("test_runner")

FAILING_TEST = "import unittest\nclass T(unittest.TestCase):\n    def test_fail(self):\n        self.assertEqual(1, 2)\n"
WRAPPER = (
    "import subprocess, sys\n"
    "p = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-v'], capture_output=True, text=True)\n"
    "sys.stdout.write(p.stdout + p.stderr)\n"
    "sys.exit(0)\n"
)


def verdict(returncode: int, output: str, framework: str = "npm test"):
    done = audit_common.CommandResult(returncode, output, "", False)
    with TempProject() as project, mock.patch.object(test_runner, "run_external", return_value=done):
        result = test_runner.run_tests(["fake"], project.root, framework=framework)
    return result["status"], result["error"]


class TestA06FailuresTakePrecedence(unittest.TestCase):
    def test_wrapper_that_exits_0_after_a_failure_is_fail(self):
        with TempProject() as project:
            project.write("test_fail.py", FAILING_TEST)
            project.write("wrapper.py", WRAPPER)
            code, out = run_main(test_runner, [str(project.root), "--cmd", f'"{sys.executable}" wrapper.py'])
        self.assertEqual(code, 1, out)
        self.assertNotIn("[PASS]", out)
        self.assertIn("[FAIL] Some tests failed (1 failed test(s) in the summary although the command exited 0)", out)
        self.assertIn("Tests: 1 total, 0 passed, 1 failed", out)
        self.assertIn('"status": "failed"', out)

    def test_every_recognised_summary_with_failures_or_errors_fails_on_exit_0(self):
        outputs = {
            "unittest errors": ("Ran 2 tests in 0.01s\n\nFAILED (errors=1)\n", "unittest"),
            "pytest": ("===== 1 failed, 2 passed in 0.10s =====\n", "pytest"),
            "jest": ("Tests:       1 failed, 2 passed, 3 total\n", "jest"),
            "node --test": ("ℹ tests 2\nℹ pass 1\nℹ fail 1\nℹ cancelled 0\n", "node --test"),
            "PHPUnit": ("FAILURES!\nTests: 3, Assertions: 3, Errors: 1.\n", "phpunit"),
            "RSpec": ("3 examples, 1 failure\n", "rspec"),
            "Maven": ("[INFO] Tests run: 3, Failures: 0, Errors: 1, Skipped: 0\n", "maven"),
            "dotnet": ("Failed!  - Failed:     1, Passed:     1, Skipped:     0, Total:     2\n", "dotnet test"),
        }
        for name, (output, framework) in outputs.items():
            with self.subTest(name):
                status, reason = verdict(0, output, framework)
                self.assertEqual(status, "failed")
                self.assertIn("although the command exited 0", reason)

    def test_passing_summary_with_exit_0_still_passes(self):
        self.assertEqual(verdict(0, "Ran 2 tests in 0.01s\n\nOK\n", "unittest")[0], "passed")
        self.assertEqual(verdict(0, "Tests:       3 passed, 3 total\n", "jest")[0], "passed")


if __name__ == "__main__":
    unittest.main()
