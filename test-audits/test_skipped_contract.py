"""K12 / plan principle 8: an audit that cannot run or does not apply prints
``SKIPPED (<reason>)`` and exits 3; it never reports PASS.
"""
from __future__ import annotations

import os
import unittest
from unittest import mock

from audit_helpers import AUDITS_DIR, TempProject, load_audit, run_main

PROJECT_AUDITS = (
    "api_validator", "schema_validator", "accessibility_checker", "ux_audit", "geo_checker",
    "i18n_checker", "lint_runner", "type_coverage", "mobile_audit", "react_performance_checker",
    "bundle_analyzer", "seo_checker", "test_runner", "dependency_analyzer",
)
EXPECTED_SCRIPTS = set(PROJECT_AUDITS) | {
    "security_scan", "lighthouse_audit", "playwright_runner", "checklist", "verify_all", "validation_runner",
}


class TestSkippedContract(unittest.TestCase):
    def test_kit_ships_exactly_the_twenty_scripts(self):
        shipped = {path.stem for path in AUDITS_DIR.glob("*.py")}
        self.assertEqual(shipped, EXPECTED_SCRIPTS)
        self.assertFalse((AUDITS_DIR / "convert_rules.py").exists())  # S6

    def test_empty_project_is_skipped_never_passed(self):
        with TempProject() as project:
            for name in PROJECT_AUDITS:
                with self.subTest(name):
                    code, out = run_main(load_audit(name), [str(project.root)])
                    self.assertEqual(code, 3, out)
                    self.assertRegex(out, r"SKIPPED \([^)]+")
                    self.assertNotIn("[PASS]", out)

    def test_missing_lighthouse_is_skipped(self):
        lighthouse = load_audit("lighthouse_audit")
        with mock.patch.object(lighthouse.shutil, "which", return_value=None):
            code, out = run_main(lighthouse, ["http://localhost:9"])
        self.assertEqual(code, 3)
        self.assertIn("SKIPPED (Lighthouse CLI not found on PATH)", out)

    def test_missing_playwright_is_skipped(self):
        playwright = load_audit("playwright_runner")
        with mock.patch.object(playwright, "sync_playwright", None):
            code, out = run_main(playwright, ["http://localhost:9"])
        self.assertEqual(code, 3)
        self.assertIn("SKIPPED (Playwright is not installed", out)

    def test_sources_follow_portability_rules(self):
        for path in sorted(AUDITS_DIR.glob("*.py")):
            text = path.read_text(encoding="utf-8")
            with self.subTest(path.name):
                lowered = text.lower()
                for word in ("antigravity", "gemini", "ag kit", "agkit"):
                    self.assertNotIn(word, lowered)
                self.assertIn("from __future__ import annotations", text)
                if path.name != "security_scan.py":  # it only names the pattern it detects
                    self.assertNotIn("shell=True", text)
                if path.name not in {"checklist.py", "verify_all.py"}:  # they delegate to validation_runner
                    self.assertIn("reconfigure(encoding=\"utf-8\"", text)

    def test_no_bytecode_left_in_kit(self):
        self.assertFalse((AUDITS_DIR / "__pycache__").exists(), os.listdir(AUDITS_DIR))


if __name__ == "__main__":
    unittest.main()
