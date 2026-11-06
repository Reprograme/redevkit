"""S2: security_scan.py must resolve npm with shutil.which and report a
failing npm audit as SKIPPED, never swallow it.

Bug: ["npm", "audit", "--json"] raised FileNotFoundError on Windows and the
exception was turned into a silent note, so the dependency audit never ran
and nothing said so.
"""
from __future__ import annotations

import json
import subprocess
import unittest
from unittest import mock

from audit_helpers import TempProject, load_audit, run_main

security_scan = load_audit("security_scan")


def completed(stdout: str, returncode: int = 0) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=["npm"], returncode=returncode, stdout=stdout, stderr="")


class TestS2NpmAudit(unittest.TestCase):
    def test_npm_resolved_with_which_and_no_shell(self):
        fake = "C:/fake/npm.cmd"
        audit_json = json.dumps({"metadata": {"vulnerabilities": {"critical": 0, "high": 2, "moderate": 0, "low": 0}}})
        with TempProject("S2") as project, \
                mock.patch.object(security_scan.shutil, "which", return_value=fake), \
                mock.patch.object(security_scan.subprocess, "run", return_value=completed(audit_json, 1)) as run:
            result = security_scan.scan_dependencies(str(project.root))
        command = run.call_args.args[0]
        self.assertEqual(command, [fake, "audit", "--json"])
        self.assertNotIn("shell", run.call_args.kwargs)
        self.assertEqual(result["npm_audit"]["high"], 2)
        self.assertEqual(result["skipped"], [])
        self.assertTrue(any(f["type"] == "npm audit" for f in result["findings"]))

    def test_missing_npm_is_reported_as_skipped(self):
        with TempProject("S2") as project, mock.patch.object(security_scan.shutil, "which", return_value=None):
            result = security_scan.scan_dependencies(str(project.root))
            code, out = run_main(security_scan, [str(project.root), "--output", "summary", "--scan-type", "deps"])
        self.assertEqual(result["skipped"], ["npm audit: npm not found on PATH"])
        self.assertIn("SKIPPED (npm audit: npm not found on PATH)", out)
        self.assertEqual(code, 0)  # the lock-file check ran and passed; the skip is visible

    def test_subprocess_failure_is_skipped_not_swallowed(self):
        cases = {
            "oserror": mock.Mock(side_effect=OSError("access denied")),
            "timeout": mock.Mock(side_effect=subprocess.TimeoutExpired(cmd="npm", timeout=90)),
            "not-json": mock.Mock(return_value=completed("npm ERR! something broke", 1)),
            "error-json": mock.Mock(return_value=completed(json.dumps({"error": {"code": "ENOLOCK", "summary": "requires a lockfile"}}), 1)),
            "empty": mock.Mock(return_value=completed("", 1)),
        }
        for label, fake_run in cases.items():
            with self.subTest(label), TempProject("S2") as project, \
                    mock.patch.object(security_scan.shutil, "which", return_value="npm"), \
                    mock.patch.object(security_scan.subprocess, "run", fake_run):
                result = security_scan.scan_dependencies(str(project.root))
                report = security_scan.run_full_scan(str(project.root), "deps")
            self.assertEqual(len(result["skipped"]), 1, label)
            self.assertTrue(result["skipped"][0].startswith("npm audit: "), result["skipped"])
            self.assertNotIn("npm_audit", result)
            self.assertNotIn("notes", result)
            self.assertEqual(report["summary"]["skipped"], result["skipped"])


if __name__ == "__main__":
    unittest.main()
