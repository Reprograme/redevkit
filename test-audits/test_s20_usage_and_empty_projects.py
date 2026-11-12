"""S20: usage errors, "nothing scanned" and the Lighthouse URL.

Bugs:

* A bad ``--url`` (``localhost:3000`` without a scheme) reached the runtime audits, which
  each exited 2: the orchestrator reported two FAILED checks (exit 1) instead of its own
  usage error (exit 2).
* security_scan.py reported ``[OK] SECURE`` (exit 0) for a project with nothing it can
  scan, so an orchestrator run on an empty folder was PASS and its documented exit 3
  ("every check skipped") could not happen.
* A URL with ``&`` given to ``lighthouse.cmd`` was cut by cmd.exe at the ``&``: Lighthouse
  got half the URL and none of its options, and the rest ran as a second command.
"""
from __future__ import annotations

import os
import unittest
from unittest import mock

from audit_helpers import TempProject, load_audit, run_main

audit_common = load_audit("audit_common")
security_scan = load_audit("security_scan")
lighthouse = load_audit("lighthouse_audit")
validation_runner = load_audit("validation_runner")
checklist = load_audit("checklist")
verify_all = load_audit("verify_all")


class TestS20BadUrlIsAUsageError(unittest.TestCase):
    def test_orchestrators_exit_2_and_run_nothing(self):
        for module in (checklist, verify_all):
            for url in ("localhost:3000", "ftp://example.com", "http://", 'http://localhost/?q="x"'):
                with self.subTest(module.__name__, url=url), TempProject() as project, \
                        mock.patch.object(validation_runner, "run_external") as run:
                    code, out = run_main(module, [str(project.root), "--url", url, "--no-tests"])
                    self.assertEqual(code, 2, out)
                    run.assert_not_called()

    def test_valid_urls_are_accepted(self):
        parser = validation_runner.build_parser("x")
        for url in ("http://localhost:3000", "https://example.com/path?a=1&b=2"):
            self.assertEqual(parser.parse_args(["--url", url]).url, url)
        self.assertIsNone(parser.parse_args([]).url)


class TestS20NothingScannedIsSkipped(unittest.TestCase):
    def test_empty_project_is_skipped_in_both_output_modes(self):
        with TempProject() as project:
            code, out = run_main(security_scan, [str(project.root), "--output", "summary"])
            self.assertEqual(code, 3, out)
            self.assertIn("SKIPPED (no source, configuration or dependency file to scan)", out)
            self.assertNotIn("[OK] SECURE", out)
            code, out = run_main(security_scan, [str(project.root)])
            self.assertEqual(code, 3, out)
            self.assertIn("SKIPPED (no source, configuration or dependency file to scan)", out)

    def test_files_only_of_kinds_the_scanner_does_not_read_are_skipped_too(self):
        with TempProject() as project:
            project.write("notes.txt", "hello\n")
            project.write("Main.kt", "fun main() {}\n")
            code, out = run_main(security_scan, [str(project.root), "--output", "summary"])
        self.assertEqual(code, 3, out)

    def test_anything_scanned_is_a_real_result(self):
        with TempProject() as project, mock.patch.object(security_scan.shutil, "which", return_value=None):
            project.write("src/app.py", "print('hello')\n")
            code, out = run_main(security_scan, [str(project.root), "--output", "summary"])
            self.assertEqual(code, 0, out)
            self.assertIn("[OK] SECURE", out)
        with TempProject() as project, mock.patch.object(security_scan.shutil, "which", return_value=None):
            project.write("package.json", '{"name": "only-a-manifest"}\n')
            code, out = run_main(security_scan, [str(project.root), "--output", "summary", "--scan-type", "deps"])
            self.assertEqual(code, 0, out)  # a manifest was checked
        with TempProject() as project:
            project.write("src/app.js", "eval(input);\n")
            code, _ = run_main(security_scan, [str(project.root), "--output", "summary"])
            self.assertEqual(code, 1)

    def test_orchestrator_on_an_empty_project_is_skipped_not_passed(self):
        with TempProject() as project:
            code, out = run_main(checklist, [str(project.root), "--no-runtime"])
        self.assertEqual(code, 3, out)
        self.assertIn("nothing was verified", out)


class TestS20LighthouseCommandLine(unittest.TestCase):
    def test_cmd_metacharacters_are_quoted(self):
        line = audit_common.windows_command_line(
            [r"C:\Program Files\nodejs\lighthouse.cmd", "http://h/?a=1&b=2", "--chrome-flags=--headless --no-sandbox", "--quiet"]
        )
        self.assertEqual(
            line,
            r'"C:\Program Files\nodejs\lighthouse.cmd" "http://h/?a=1&b=2" "--chrome-flags=--headless --no-sandbox" --quiet',
        )
        self.assertEqual(audit_common.windows_command_line(["a|b", "c>d", "plain"]), '"a|b" "c>d" plain')

    def test_urls_that_cannot_be_quoted_are_rejected(self):
        for url in ('http://localhost/?q="x"', "http://localhost/a b"):
            with self.subTest(url):
                code, _ = run_main(lighthouse, [url])
                self.assertEqual(code, 2)

    @unittest.skipUnless(os.name == "nt", "cmd.exe shims exist only on Windows")
    def test_url_with_ampersand_reaches_the_lighthouse_shim_whole(self):
        with TempProject() as project:
            shim = project.write("fake bin/lighthouse.cmd", "@echo off\r\necho ARGV: %* 1>&2\r\nexit /b 1\r\n")
            with mock.patch.object(lighthouse.shutil, "which", return_value=str(shim)):
                result = lighthouse.run_lighthouse("http://localhost:9/?a=1&b=2", timeout=30)
        self.assertEqual(result["status"], "error")  # the fake CLI exits 1 without a report
        self.assertIn("http://localhost:9/?a=1&b=2", result["stderr"])
        self.assertIn("--quiet", result["stderr"])  # the options after the URL were not cut off


if __name__ == "__main__":
    unittest.main()
