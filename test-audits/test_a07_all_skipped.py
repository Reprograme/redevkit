"""A07: a run in which every executed test was skipped is SKIPPED (exit 3), never PASS.

Bug: the parsers counted skipped tests in the total and left them out of ``passed`` without
keeping their number; the verdict only checked ``tests_run == 0``. A suite with one
``@unittest.skip`` test printed ``OK (skipped=1)``, ``[PASS]`` and ``1 total, 0 passed,
0 failed`` with exit 0. PHPUnit (skipped/incomplete), RSpec (pending), minitest (skips),
Maven Surefire (skipped), Jest/Vitest (skipped/todo), node:test, Mocha (pending), cargo
(ignored) and dotnet behaved the same. A mixed run (one passed, one skipped) stays PASS.
"""
from __future__ import annotations

import unittest
from unittest import mock

from audit_helpers import TempProject, load_audit, run_main

audit_common = load_audit("audit_common")
test_runner = load_audit("test_runner")

SKIP_ONLY = (
    "import unittest\nclass T(unittest.TestCase):\n"
    "    @unittest.skip('later')\n    def test_skip(self):\n        pass\n"
)
MIXED = SKIP_ONLY + "    def test_ok(self):\n        self.assertTrue(True)\n"

ALL_SKIPPED = {
    "unittest": ("Ran 1 test in 0.000s\n\nOK (skipped=1)\n", "unittest", 1),
    "PHPUnit skipped": ("OK, but incomplete, skipped, or risky tests!\nTests: 2, Assertions: 0, Skipped: 1, Incomplete: 1.\n", "phpunit", 2),
    "RSpec pending": ("Finished in 0.1 seconds\n2 examples, 0 failures, 2 pending\n", "rspec", 2),
    "minitest": ("3 runs, 0 assertions, 0 failures, 0 errors, 3 skips\n", "rails test", 3),
    "Maven Surefire": ("[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 2\n", "maven", 2),
    "Jest": ("Tests:       1 skipped, 1 todo, 2 total\n", "jest", 2),
    "Vitest": (" Test Files  1 skipped (1)\n      Tests  3 skipped (3)\n", "vitest", 3),
    "node --test": ("ℹ tests 1\nℹ suites 0\nℹ pass 0\nℹ fail 0\nℹ cancelled 0\nℹ skipped 1\nℹ todo 0\n", "node --test", 1),
    "pytest": ("===== 2 skipped in 0.01s =====\n", "pytest", 2),
    "Mocha": ("  0 passing (2ms)\n  4 pending\n", "npm test", 4),
    "cargo": ("test result: ok. 0 passed; 0 failed; 1 ignored; 0 measured; 0 filtered out\n", "cargo test", 1),
    "dotnet": ("Passed!  - Failed:     0, Passed:     0, Skipped:     2, Total:     2, Duration: 3 ms\n", "dotnet test", 2),
    "dotnet summary": ("Test summary: total: 2, failed: 0, succeeded: 0, skipped: 2, duration: 1.0s\n", "dotnet test", 2),
}


def run_result(returncode: int, output: str, framework: str):
    done = audit_common.CommandResult(returncode, output, "", False)
    with TempProject() as project, mock.patch.object(test_runner, "run_external", return_value=done):
        return test_runner.run_tests(["fake"], project.root, framework=framework)


class TestA07AllSkipped(unittest.TestCase):
    def test_every_parser_keeps_the_skipped_count_and_skips_the_run(self):
        for name, (output, framework, skipped) in ALL_SKIPPED.items():
            with self.subTest(name):
                result = run_result(0, output, framework)
                self.assertEqual(result["tests_skipped"], skipped)
                self.assertEqual((result["tests_passed"], result["tests_failed"]), (0, 0))
                self.assertEqual(result["status"], "skipped")
                self.assertEqual(result["error"], f"all tests were skipped ({skipped} skipped, 0 passed)")

    def test_mixed_runs_still_pass(self):
        mixed = {
            "unittest": ("Ran 2 tests in 0.000s\n\nOK (skipped=1)\n", "unittest"),
            "RSpec": ("2 examples, 0 failures, 1 pending\n", "rspec"),
            "Maven": ("[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 1\n", "maven"),
            "Jest": ("Tests:       1 skipped, 1 passed, 2 total\n", "jest"),
            "pytest": ("===== 1 passed, 1 skipped in 0.01s =====\n", "pytest"),
        }
        for name, (output, framework) in mixed.items():
            with self.subTest(name):
                result = run_result(0, output, framework)
                self.assertEqual(result["status"], "passed")
                self.assertEqual((result["tests_passed"], result["tests_skipped"]), (1, 1))

    def test_real_unittest_suite_with_only_a_skipped_test_is_skipped(self):
        with mock.patch.object(test_runner, "python_module_available", return_value=False), TempProject() as project:
            project.write("requirements.txt", "")
            project.write("test_skip.py", SKIP_ONLY)
            code, out = run_main(test_runner, [str(project.root)])
        self.assertEqual(code, 3, out)
        self.assertNotIn("[PASS]", out)
        self.assertIn("SKIPPED (all tests were skipped (1 skipped, 0 passed))", out)
        self.assertIn("Tests: 1 total, 0 passed, 0 failed, 1 skipped", out)
        self.assertIn('"tests_skipped": 1', out)

    def test_real_mixed_unittest_suite_passes_and_reports_the_skipped_test(self):
        with mock.patch.object(test_runner, "python_module_available", return_value=False), TempProject() as project:
            project.write("requirements.txt", "")
            project.write("test_mix.py", MIXED)
            code, out = run_main(test_runner, [str(project.root)])
        self.assertEqual(code, 0, out)
        self.assertIn("[PASS] All tests passed", out)
        self.assertIn("Tests: 2 total, 1 passed, 0 failed, 1 skipped", out)


if __name__ == "__main__":
    unittest.main()
