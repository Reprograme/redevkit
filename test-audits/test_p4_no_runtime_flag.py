"""P4: checklist.py and verify_all.py share one flag, --no-runtime.

Bug: checklist.py used --skip-runtime while verify_all.py used --no-runtime
(plus --no-e2e), so the same instruction worked on one runner only.
"""
from __future__ import annotations

import os
import subprocess
import sys
import unittest

from audit_helpers import AUDITS_DIR, TempProject, load_audit

validation_runner = load_audit("validation_runner")
checklist = load_audit("checklist")
verify_all = load_audit("verify_all")


def option_strings(parser) -> set:
    return {option for action in parser._actions for option in action.option_strings}


class TestP4NoRuntimeFlag(unittest.TestCase):
    def test_both_runners_accept_only_no_runtime(self):
        for module in (checklist, verify_all):
            with self.subTest(module.__name__):
                parser = validation_runner.build_parser("x")
                self.assertTrue(parser.parse_args(["--no-runtime"]).no_runtime)
                for legacy in ("--skip-runtime", "--no-e2e"):
                    with self.assertRaises(SystemExit):
                        with open(os.devnull, "w") as devnull:
                            stderr, sys.stderr = sys.stderr, devnull
                            try:
                                parser.parse_args([legacy])
                            finally:
                                sys.stderr = stderr
        self.assertEqual(
            option_strings(validation_runner.build_parser("a")),
            # --no-tests, --exclude and --no-gitignore: see test_s11_exclusions / test_s12_runner_options
            {"-h", "--help", "--url", "--no-runtime", "--no-tests", "--stop-on-fail", "--report",
             "--exclude", "--no-gitignore"},
        )

    def test_no_runtime_drops_url_checks_in_both_suites(self):
        for suite in (checklist.SUITE, verify_all.SUITE):
            self.assertTrue(any(spec.target == "url" for spec in suite))
            selected = validation_runner.select_specs(suite, no_runtime=True)
            self.assertTrue(selected)
            self.assertFalse(any(spec.target == "url" for spec in selected))
            self.assertEqual(len(validation_runner.select_specs(suite, no_runtime=False)), len(suite))

    def test_scripts_resolve_next_to_the_runner(self):
        self.assertEqual(validation_runner.AUDITS_DIR, AUDITS_DIR.resolve())
        for suite in (checklist.SUITE, verify_all.SUITE):
            for spec in suite:
                self.assertNotIn("/", spec.script)
                self.assertTrue((AUDITS_DIR / spec.script).is_file(), spec.script)

    def test_runners_run_with_no_runtime(self):
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PATH="")
        for script in ("checklist.py", "verify_all.py"):
            with self.subTest(script), TempProject("P4") as project:
                proc = subprocess.run(
                    [sys.executable, str(AUDITS_DIR / script), str(project.root), "--no-runtime"],
                    capture_output=True, text=True, encoding="utf-8", errors="replace",
                    timeout=300, env=env, check=False,
                )
                self.assertEqual(proc.returncode, 0, proc.stdout[-2000:] + proc.stderr[-2000:])
                self.assertIn("Runtime checks: disabled (--no-runtime)", proc.stdout)
                self.assertNotIn("Lighthouse", proc.stdout)
                self.assertNotIn("Playwright", proc.stdout)
                self.assertNotIn("Traceback", proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
