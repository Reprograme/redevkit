"""S8: type_coverage.py must catch subprocess.TimeoutExpired from tsc.

Bug: a slow ``tsc --noEmit`` raised an uncaught TimeoutExpired and crashed
the audit.
"""
from __future__ import annotations

import subprocess
import unittest
from pathlib import Path
from unittest import mock

from audit_helpers import TempProject, load_audit, run_main

type_coverage = load_audit("type_coverage")


class TestS8TypeCoverageTimeout(unittest.TestCase):
    def test_tsc_timeout_is_caught_and_skipped(self):
        timeout = subprocess.TimeoutExpired(cmd="tsc", timeout=type_coverage.TSC_TIMEOUT)
        with TempProject("S8") as project, \
                mock.patch.object(type_coverage, "_local_tsc", return_value=Path("tsc")), \
                mock.patch.object(type_coverage.subprocess, "run", side_effect=timeout):
            runs = type_coverage._run_typescript_compilers(project.root)
            code, out = run_main(type_coverage, [str(project.root)])
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0]["status"], "skipped")
        self.assertIn("timed out", runs[0]["reason"])
        self.assertEqual(code, 0, out)
        self.assertIn("SKIPPED (tsc for tsconfig.json: tsc timed out", out)

    def test_missing_local_tsc_is_skipped_not_ok(self):
        with TempProject("S8") as project, mock.patch.object(type_coverage, "_local_tsc", return_value=None):
            code, out = run_main(type_coverage, [str(project.root)])
        self.assertIn("SKIPPED (tsc for tsconfig.json: local tsc not installed)", out)
        self.assertNotIn("[OK] Compiler check skipped", out)

    def test_no_sources_is_skipped(self):
        with TempProject() as project:
            code, out = run_main(type_coverage, [str(project.root)])
        self.assertEqual(code, type_coverage.EXIT_SKIPPED)
        self.assertIn("SKIPPED (no TypeScript or Python files found)", out)


if __name__ == "__main__":
    unittest.main()
