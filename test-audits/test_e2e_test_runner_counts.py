"""Found by the E2E run (scenario A, Codex): test_runner.py counted Vitest test FILES as tests.

Vitest prints "Test Files  3 passed (3)" before "Tests  22 passed (22)"; Jest prints
"Test Suites: 3 passed, 3 total" before "Tests: 22 passed, 22 total".
"""
from __future__ import annotations

import unittest

from audit_helpers import load_audit

test_runner = load_audit("test_runner")


def counts(output: str) -> dict:
    result = {"tests_passed": 0, "tests_failed": 0, "tests_run": 0}
    test_runner._parse_counts(output, result)
    return result


class TestRunnerCounts(unittest.TestCase):
    def test_vitest_counts_tests_not_files(self):
        out = " Test Files  3 passed (3)\n      Tests  22 passed (22)\n   Duration  700ms\n"
        self.assertEqual(counts(out)["tests_passed"], 22)

    def test_jest_counts_tests_not_suites(self):
        out = "Test Suites: 1 failed, 2 passed, 3 total\nTests:       2 failed, 20 passed, 22 total\n"
        r = counts(out)
        self.assertEqual((r["tests_passed"], r["tests_failed"], r["tests_run"]), (20, 2, 22))

    def test_pytest_summary_still_parsed(self):
        out = "===== 5 passed, 1 failed in 0.20s =====\n"
        r = counts(out)
        self.assertEqual((r["tests_passed"], r["tests_failed"]), (5, 1))


if __name__ == "__main__":
    unittest.main()
