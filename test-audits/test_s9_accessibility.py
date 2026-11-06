"""S9: accessibility_checker.py must ignore comments and detect JSX tabIndex.

Bugs: ``<html\\b[^>]*>`` matched inside a comment ("// Keep <html lang> in
sync ...") and reported a missing lang; ``tabIndex={1}`` was not detected.
"""
from __future__ import annotations

import unittest

from audit_helpers import TempProject, load_audit, run_main

a11y = load_audit("accessibility_checker")


class TestS9Accessibility(unittest.TestCase):
    def test_tags_inside_comments_are_ignored(self):
        with TempProject("S9") as project:
            issues = a11y.check_accessibility(project.root / "src" / "i18n" / "provider.tsx")
        self.assertEqual(issues, [])

    def test_jsx_positive_tabindex_is_detected(self):
        with TempProject("S9") as project:
            issues = a11y.check_accessibility(project.root / "src" / "Tabs.tsx")
            code, out = run_main(a11y, [str(project.root)])
        self.assertEqual(issues, ["Avoid positive tabIndex values"])
        self.assertEqual(code, 1)
        self.assertIn("src/Tabs.tsx", out)
        self.assertNotIn("provider.tsx", out)

    def test_tabindex_variants(self):
        positives = ['<div tabIndex={1} />', '<div tabIndex={ 2 } />', '<div tabIndex={"3"} />', '<div tabindex="4">']
        negatives = ['<div tabIndex={0} />', '<div tabIndex={-1} />', '<div tabIndex="0">']
        for snippet in positives:
            self.assertIn("Avoid positive tabIndex values", a11y.check_content(snippet), snippet)
        for snippet in negatives:
            self.assertNotIn("Avoid positive tabIndex values", a11y.check_content(snippet), snippet)

    def test_real_html_without_lang_still_reported(self):
        self.assertIn("Missing lang attribute on <html>", a11y.check_content("<html><body></body></html>"))
        self.assertNotIn("Missing lang attribute on <html>", a11y.check_content('<html lang="en"></html>'))
        # URLs keep their "//" and the markup after them.
        self.assertIn(
            "Missing lang attribute on <html>",
            a11y.check_content('<a href="http://x.test">http://x.test</a>\n<html>'),
        )


if __name__ == "__main__":
    unittest.main()
