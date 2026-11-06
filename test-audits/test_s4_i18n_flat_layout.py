"""S4: i18n_checker.py must take the language from the file name in flat
layouts (messages/en.json, locales/pt-BR.json).

Bug: ``language = path.parent.name`` gave every flat file the language
"messages", so completeness was silently skipped (en.json with 3 keys vs
vi.json with 1 key produced 0 issues).
"""
from __future__ import annotations

import unittest
from pathlib import Path

from audit_helpers import TempProject, load_audit, run_main

i18n_checker = load_audit("i18n_checker")


class TestS4FlatLocaleLayout(unittest.TestCase):
    def test_language_from_file_name(self):
        root = Path("project")
        self.assertEqual(i18n_checker.locale_identity(root / "messages" / "en.json", root), ("en", "messages"))
        self.assertEqual(i18n_checker.locale_identity(root / "locales" / "pt-BR.json", root), ("pt-BR", "locales"))
        self.assertEqual(i18n_checker.locale_identity(root / "pt-BR.json", root), ("pt-BR", "."))
        self.assertEqual(
            i18n_checker.locale_identity(root / "locales" / "en" / "common.json", root), ("en", "locales/common")
        )
        # "app" is not a language code: the parent directory wins.
        self.assertEqual(i18n_checker.locale_identity(root / "locales" / "de" / "app.json", root), ("de", "locales/app"))

    def test_flat_layout_reports_missing_keys(self):
        with TempProject("S4") as project:
            report = i18n_checker.audit(project.root)
            code, out = run_main(i18n_checker, [str(project.root)])
        locale = report["locale_check"]
        self.assertEqual(locale["languages"], ["en", "pt-BR", "vi"])
        issues = {item["file"]: item["issue"] for item in locale["issues"]}
        self.assertIn("messages [vi]", issues)
        self.assertIn("Missing 2 key(s)", issues["messages [vi]"])
        self.assertIn("locales [pt-BR]", issues)
        self.assertIn("Missing 2 key(s)", issues["locales [pt-BR]"])
        self.assertEqual(code, 1)
        self.assertIn("[FAIL]", out)

    def test_nested_layout_still_works(self):
        with TempProject() as project:
            project.write("locales/en/common.json", '{"a": 1, "b": 2}')
            project.write("locales/de/common.json", '{"a": 1}')
            report = i18n_checker.audit(project.root)
        issues = report["locale_check"]["issues"]
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["file"], "locales/common [de]")

    def test_node_modules_locales_are_ignored(self):
        with TempProject() as project:
            project.write("node_modules/pkg/locales/en.json", '{"a": 1, "b": 2}')
            project.write("node_modules/pkg/locales/fr.json", '{"a": 1}')
            code, out = run_main(i18n_checker, [str(project.root)])
        self.assertEqual(code, i18n_checker.EXIT_SKIPPED)
        self.assertIn("SKIPPED (", out)


if __name__ == "__main__":
    unittest.main()
