"""S3: the "SQL string concatenation" rule must actually fire.

Bug: strings were stripped before the scan and the regex required quotes
around the concatenated operand, so ``"SELECT ... " + userId`` produced 0
findings (dead rule); splitlines() also ran twice per match.
"""
from __future__ import annotations

import unittest
from pathlib import Path
from unittest import mock

from audit_helpers import TempProject, load_audit

security_scan = load_audit("security_scan")


class CountingStr(str):
    calls = 0

    def splitlines(self, *args, **kwargs):  # type: ignore[override]
        CountingStr.calls += 1
        return super().splitlines(*args, **kwargs)


class TestS3SqlConcatenation(unittest.TestCase):
    def scan(self):
        with TempProject("S3") as project:
            return security_scan.scan_code_patterns(str(project.root))

    def test_concatenation_is_detected(self):
        findings = self.scan()["findings"]
        sql = {(f["file"], f["line"], f["pattern"]) for f in findings if f["category"] == "SQL injection risk"}
        self.assertIn(("src/users.js", 2, "SQL string concatenation"), sql)  # "SELECT ... " + userId
        self.assertIn(("src/users.js", 6, "SQL string concatenation"), sql)
        self.assertIn(("src/query.py", 2, "SQL string concatenation"), sql)
        self.assertIn(("src/query.py", 6, "SQL f-string"), sql)

    def test_comments_docstrings_and_parameters_are_not_findings(self):
        findings = self.scan()["findings"]
        self.assertEqual([f for f in findings if f["file"] == "src/safe.py"], [])

    def test_rule_works_without_quotes_around_operand(self):
        without_comments, _ = security_scan.code_views('run("SELECT id FROM t WHERE a = " + req.query.id)\n', ".js")
        self.assertEqual(len(security_scan.find_sql_injection(without_comments)), 1)

    def test_splitlines_once_per_file(self):
        content = CountingStr(
            'const a = "SELECT 1 FROM t WHERE x = " + a;\n'
            'const token = "abcdefghijklmnop1";\n'
            'const apiKey = "abcdefghijklmnop2";\n'
            'const password = "hunter2hunter2";\n'
        )
        with TempProject() as project:
            project.write("a.js", "placeholder\n")
            CountingStr.calls = 0
            with mock.patch.object(Path, "read_text", lambda self, *a, **k: content):
                secrets = security_scan.scan_secrets(str(project.root))
            self.assertEqual(len(secrets["findings"]), 3)
            self.assertEqual(CountingStr.calls, 1)
            CountingStr.calls = 0
            with mock.patch.object(Path, "read_text", lambda self, *a, **k: content):
                patterns = security_scan.scan_code_patterns(str(project.root))
            self.assertEqual(len(patterns["findings"]), 1)
            self.assertEqual(CountingStr.calls, 1)


if __name__ == "__main__":
    unittest.main()
