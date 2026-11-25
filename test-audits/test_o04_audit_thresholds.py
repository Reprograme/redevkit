"""O04: the threshold options of single audits are documented, validated and have an effect.

``bundle_analyzer.py`` (``--file-warn-kib``, ``--file-fail-kib``, ``--total-js-fail-kib``),
``lighthouse_audit.py`` (``--min-performance``, ``--min-accessibility``,
``--min-best-practices``, ``--min-seo``, ``--timeout``), ``i18n_checker.py`` (``--strict``)
and ``playwright_runner.py`` (``--timeout-ms``) had no documentation and no test; an
out-of-range value (a score of 101, a negative size, a time limit of 0) was accepted.
Lighthouse and Playwright are not needed: their runs are replaced by fakes.
"""
from __future__ import annotations

import json
import unittest
from unittest import mock

from audit_helpers import AUDITS_DIR, TempProject, load_audit, run_main

bundle_analyzer = load_audit("bundle_analyzer")
lighthouse_audit = load_audit("lighthouse_audit")
i18n_checker = load_audit("i18n_checker")
playwright_runner = load_audit("playwright_runner")

URL = "http://localhost:3000"
SCORES = {"performance": 60, "accessibility": 90, "best_practices": 90, "seo": 85}


class TestO04Documented(unittest.TestCase):
    def test_every_option_is_in_the_readme(self):
        readme = (AUDITS_DIR / "README.md").read_text(encoding="utf-8")
        for option in ("--file-warn-kib", "--file-fail-kib", "--total-js-fail-kib", "--min-performance",
                       "--min-accessibility", "--min-best-practices", "--min-seo", "--strict", "--timeout-ms"):
            with self.subTest(option):
                self.assertIn(f"`{option}", readme)


class TestO04BundleLimits(unittest.TestCase):
    def bundle(self, *options):
        with TempProject() as project:
            project.write("dist/app.js", "x" * 3 * 1024)  # 3 KiB of JavaScript
            code, out = run_main(bundle_analyzer, [str(project.root), "--output", "json", *options])
        return code, out

    def test_defaults_find_nothing_in_a_small_bundle(self):
        code, out = self.bundle()
        self.assertEqual(code, 0, out)
        self.assertEqual(json.loads(out)["findings"], [])

    def test_each_limit_changes_the_findings(self):
        code, out = self.bundle("--file-warn-kib", "2")
        self.assertEqual(code, 0, out)  # medium: below the default --fail-on high
        self.assertEqual([f["issue"] for f in json.loads(out)["findings"]], ["Large asset"])
        code, out = self.bundle("--file-fail-kib", "2")
        self.assertEqual(code, 1, out)
        self.assertEqual([f["issue"] for f in json.loads(out)["findings"]], ["Oversized asset"])
        code, out = self.bundle("--total-js-fail-kib", "2")
        self.assertEqual(code, 1, out)
        self.assertEqual([f["issue"] for f in json.loads(out)["findings"]], ["Large total JavaScript payload"])

    def test_invalid_limits_are_usage_errors(self):
        for option in ("--file-warn-kib", "--file-fail-kib", "--total-js-fail-kib"):
            for value in ("-1", "abc", "1.5"):
                with self.subTest(option=option, value=value):
                    self.assertEqual(self.bundle(option, value)[0], 2)


class TestO04Lighthouse(unittest.TestCase):
    def run_audit(self, *options):
        fake = {"url": URL, "status": "success", "scores": dict(SCORES), "metrics": {}}
        with mock.patch.object(lighthouse_audit, "run_lighthouse", return_value=fake) as run:
            code, out = run_main(lighthouse_audit, [URL, *options])
        return code, out, run

    def test_thresholds_decide(self):
        code, out, run = self.run_audit()
        self.assertEqual(code, 0, out)
        self.assertEqual(run.call_args.args, (URL, 180))
        code, out, _ = self.run_audit("--min-seo", "90", "--min-performance", "70")
        self.assertEqual(code, 1, out)
        self.assertEqual(json.loads(out)["failed_thresholds"], ["performance", "seo"])
        code, out, _ = self.run_audit("--min-accessibility", "0", "--min-best-practices", "100")
        self.assertEqual(json.loads(out)["failed_thresholds"], ["best_practices"])
        _, _, run = self.run_audit("--timeout", "240")
        self.assertEqual(run.call_args.args, (URL, 240))

    def test_invalid_values_are_usage_errors(self):
        for option in ("--min-performance", "--min-accessibility", "--min-best-practices", "--min-seo"):
            for value in ("101", "-1", "abc", "nan"):
                with self.subTest(option=option, value=value):
                    code, _, run = self.run_audit(option, value)
                    self.assertEqual(code, 2)
                    run.assert_not_called()
        for value in ("0", "-5", "inf"):
            with self.subTest(timeout=value):
                self.assertEqual(self.run_audit("--timeout", value)[0], 2)


class TestO04Playwright(unittest.TestCase):
    def test_timeout_is_passed_and_validated(self):
        fake = {"url": URL, "status": "success", "passed": True}
        with mock.patch.object(playwright_runner, "run_test", return_value=fake) as run:
            code, out = run_main(playwright_runner, [URL, "--timeout-ms", "45000"])
            self.assertEqual(code, 0, out)
            self.assertEqual(run.call_args.args[-1], 45000)
            run_main(playwright_runner, [URL])
            self.assertEqual(run.call_args.args[-1], 30000)
            for value in ("0", "-1", "abc", "1e999"):
                with self.subTest(value):
                    run.reset_mock()
                    self.assertEqual(run_main(playwright_runner, [URL, "--timeout-ms", value])[0], 2)
                    run.assert_not_called()


class TestO04I18nStrict(unittest.TestCase):
    def test_strict_scans_a_project_without_i18n(self):
        with TempProject() as project:
            project.write("src/App.jsx", "export const App = () => <button>Save changes</button>;\n")
            code, out = run_main(i18n_checker, [str(project.root), "--json"])
            self.assertEqual(code, 3, out)  # no i18n setup: SKIPPED
            self.assertIn("SKIPPED (no i18n framework or locale files detected)", out)
            code, out = run_main(i18n_checker, [str(project.root), "--json", "--strict"])
        self.assertEqual(code, 0, out)  # hard-coded strings are medium findings
        report = json.loads(out)
        self.assertTrue(report["applicable"])
        self.assertEqual([issue["text"] for issue in report["code_check"]["issues"]], ["Save changes"])


if __name__ == "__main__":
    unittest.main()
