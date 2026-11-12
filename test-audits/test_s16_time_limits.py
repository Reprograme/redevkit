"""S16: time limits are ordered, configurable and visible.

Bugs:

* The orchestrators gave the Test Runner check 300 s, exactly the limit test_runner.py
  gave the test command (and Lighthouse 180 s for 180 s; lint up to 4 x 120 s inside
  300 s). The outer limit always fired first: the audit was killed before it could
  report, and the check carried no output at all.
* A timeout of the test command was reported as ``[FAIL] Some tests failed`` with
  ``"status": "failed"``: nothing told a timeout from failing tests.

Now the limit of a check is the worst case of its audit plus a margin, test_runner.py
has ``--timeout SECONDS`` and reports ``[TIMEOUT]`` / ``"status": "timeout"`` (exit code
1, the 0/1/2/3 contract is unchanged), and a check killed by the orchestrator keeps the
output printed so far.

Every process these tests start ends by itself within a few seconds.
"""
from __future__ import annotations

import inspect
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from audit_helpers import FIXTURES_DIR, TempProject, load_audit, run_main

audit_common = load_audit("audit_common")
test_runner = load_audit("test_runner")
lint_runner = load_audit("lint_runner")
type_coverage = load_audit("type_coverage")
security_scan = load_audit("security_scan")
lighthouse = load_audit("lighthouse_audit")
validation_runner = load_audit("validation_runner")
checklist = load_audit("checklist")
verify_all = load_audit("verify_all")

SLOW = str(FIXTURES_DIR / "S14" / "slow.py")
LIFETIME = 8
FAKE_AUDITS = {
    "slow.py": "import sys, time\nprint('partial-evidence', flush=True)\ntime.sleep(8)\n",
    "own_timeout.py": "import sys\nprint('[TIMEOUT] Test command timed out after 4s and the process tree was killed')\nsys.exit(1)\n",
    "pass.py": "print('ok')\n",
}


def json_tail(out: str) -> dict:
    return json.loads(out[out.rindex("\n{") + 1:])


def slow_framework(seconds: int = LIFETIME) -> dict:
    return {"type": "python", "framework": "unittest", "cmd": [sys.executable, SLOW, str(seconds)],
            "coverage_cmd": None, "coverage_skip_reason": "x", "skip_reason": None}


class TestS16OuterLimitsExceedInnerLimits(unittest.TestCase):
    def spec(self, suite, script):
        return next(spec for spec in suite if spec.script == script)

    def test_orchestrator_limits_cover_the_worst_case_of_each_audit(self):
        margin = validation_runner.TIMEOUT_MARGIN
        self.assertGreaterEqual(margin, 30)
        lighthouse_default = inspect.signature(lighthouse.run_lighthouse).parameters["timeout"].default
        for suite in (checklist.SUITE, verify_all.SUITE):
            with self.subTest(suite=len(suite)):
                self.assertGreaterEqual(self.spec(suite, "test_runner.py").timeout, test_runner.TIMEOUT_SECONDS + margin)
                self.assertGreaterEqual(
                    self.spec(suite, "lint_runner.py").timeout,
                    lint_runner.MAX_LINTERS * lint_runner.TIMEOUT_SECONDS + margin,
                )
                self.assertGreaterEqual(self.spec(suite, "lighthouse_audit.py").timeout, lighthouse_default + margin)
                self.assertGreaterEqual(self.spec(suite, "type_coverage.py").timeout, type_coverage.TSC_TOTAL_BUDGET + margin)
                self.assertGreater(self.spec(suite, "security_scan.py").timeout, security_scan.NPM_AUDIT_TIMEOUT + margin)

    def test_lint_runner_never_queues_more_linters_than_the_limit_assumes(self):
        with TempProject() as project, mock.patch.object(lint_runner, "python_tool", return_value=["tool"]), \
                mock.patch.object(lint_runner.shutil, "which", return_value="npm"):
            project.write("package.json", '{"scripts": {"lint": "eslint ."}, "devDependencies": {"eslint": "9", "typescript": "5"}}')
            project.write("tsconfig.json", "{}")
            project.write("pyproject.toml", "[tool.mypy]\n")
            project.write("mypy.ini", "[mypy]\n")
            linters = lint_runner.detect_project_type(project.root)["linters"]
        self.assertEqual(len(linters), lint_runner.MAX_LINTERS)

    def test_tsc_runs_share_one_budget(self):
        done = audit_common.CommandResult(0, "", "", False)
        with TempProject() as project, mock.patch.object(type_coverage, "_local_tsc", return_value=Path("tsc")), \
                mock.patch.object(type_coverage, "run_external", return_value=done) as run, \
                mock.patch.object(type_coverage, "TSC_TOTAL_BUDGET", 0):
            project.write("tsconfig.json", "{}")
            project.write("packages/a/tsconfig.json", "{}")
            runs = type_coverage._run_typescript_compilers(project.root)
        run.assert_not_called()
        self.assertEqual([r["status"] for r in runs], ["skipped", "skipped"])
        self.assertIn("budget", runs[0]["reason"])


class TestS16TestRunnerTimeout(unittest.TestCase):
    def test_default_limit_is_unchanged_and_option_is_validated(self):
        self.assertEqual(test_runner.TIMEOUT_SECONDS, 300)
        with TempProject() as project:
            for bad in ("0", "-5", "soon"):
                with self.subTest(bad):
                    code, _ = run_main(test_runner, [str(project.root), "--timeout", bad])
                    self.assertEqual(code, 2)

    def test_timeout_option_reaches_the_command(self):
        done = audit_common.CommandResult(0, "Ran 2 tests in 0.001s\n\nOK\n", "", False)
        with TempProject() as project, mock.patch.object(test_runner, "detect_test_framework", return_value=slow_framework()), \
                mock.patch.object(test_runner, "run_external", return_value=done) as run:
            run_main(test_runner, [str(project.root), "--timeout", "45"])
            self.assertEqual(run.call_args.kwargs["timeout"], 45)
            run_main(test_runner, [str(project.root)])
            self.assertEqual(run.call_args.kwargs["timeout"], test_runner.TIMEOUT_SECONDS)

    def test_timeout_is_distinguishable_and_still_exit_1(self):
        with TempProject() as project, mock.patch.object(test_runner, "detect_test_framework", return_value=slow_framework()):
            started = time.monotonic()
            code, out = run_main(test_runner, [str(project.root), "--timeout", "1"])
            elapsed = time.monotonic() - started
        self.assertEqual(code, 1, out)  # the exit-code contract (0/1/2/3) does not change
        self.assertLess(elapsed, LIFETIME - 1, "the test command was not killed at its limit")
        self.assertRegex(out, r"(?m)^\[TIMEOUT\] Test command timed out after 1s")
        self.assertNotIn("Some tests failed", out)
        self.assertIn("started-before-timeout", out)  # what the command printed before the limit
        self.assertNotIn("finished-in-time", out)
        payload = json_tail(out)
        self.assertEqual((payload["status"], payload["timed_out"]), ("timeout", True))
        self.assertIn("timed out after 1s", payload["reason"])

    def test_other_results_say_timed_out_false(self):
        done = audit_common.CommandResult(1, "Ran 2 tests in 0.001s\n\nFAILED (failures=1)\n", "", False)
        with TempProject() as project, mock.patch.object(test_runner, "detect_test_framework", return_value=slow_framework()), \
                mock.patch.object(test_runner, "run_external", return_value=done):
            code, out = run_main(test_runner, [str(project.root)])
        payload = json_tail(out)
        self.assertEqual((code, payload["status"], payload["timed_out"], payload["reason"]), (1, "failed", False, "exit code 1"))
        self.assertNotIn("[TIMEOUT]", out)
        with TempProject() as project:
            code, out = run_main(test_runner, [str(project.root)])
        self.assertEqual((code, json_tail(out)["timed_out"]), (3, False))

    def test_lint_runner_prints_the_timeout(self):
        linters = {"type": "python", "linters": [{"name": "slow", "cmd": [sys.executable, SLOW, str(LIFETIME)], "skip_reason": None}]}
        with TempProject() as project, mock.patch.object(lint_runner, "detect_project_type", return_value=linters), \
                mock.patch.object(lint_runner, "TIMEOUT_SECONDS", 1):
            code, out = run_main(lint_runner, [str(project.root)])
        self.assertEqual(code, 1, out)
        self.assertRegex(out, r"(?m)^\[TIMEOUT\] slow - timeout after 1s")
        check = json_tail(out)["checks"][0]
        self.assertEqual((check["status"], check["timed_out"]), ("failed", True))


class TestS16OrchestratorTimeout(unittest.TestCase):
    def run_fake_suite(self, specs):
        with tempfile.TemporaryDirectory(prefix="redevkit-fake-audits-") as audits, TempProject() as project:
            for name, body in FAKE_AUDITS.items():
                (Path(audits) / name).write_text(body, encoding="utf-8")
            report = project.root / "report.json"
            with mock.patch.object(validation_runner, "AUDITS_DIR", Path(audits)):
                runner = type("Runner", (), {
                    "main": staticmethod(lambda argv: validation_runner.run_suite("T", "S", "d", specs, argv)),
                })
                started = time.monotonic()
                code, out = run_main(runner, [str(project.root), "--report", str(report)])
                elapsed = time.monotonic() - started
            payload = json.loads(report.read_text(encoding="utf-8"))
        return code, out, payload, elapsed

    def test_check_killed_at_its_limit_is_an_error_that_keeps_the_output(self):
        specs = (
            validation_runner.CheckSpec("Slow", "slow.py", "Fake", timeout=1),
            validation_runner.CheckSpec("Next", "pass.py", "Fake"),
        )
        code, out, payload, elapsed = self.run_fake_suite(specs)
        self.assertEqual(code, 1, out)
        self.assertLess(elapsed, 7, "the orchestrator waited for the audit instead of killing it")
        slow, following = payload["results"]
        self.assertEqual((slow["status"], slow["reason"]), ("error", "timed out after 1s"))
        self.assertIn("partial-evidence", slow["stdout"])
        self.assertIn("[ERROR] Fake / Slow - timed out after 1s", out)
        self.assertEqual(following["status"], "passed")  # the suite goes on

    def test_the_audits_own_timeout_reaches_the_summary(self):
        specs = (validation_runner.CheckSpec("Tests", "own_timeout.py", "Fake"),)
        code, out, payload, _ = self.run_fake_suite(specs)
        self.assertEqual(code, 1, out)
        result = payload["results"][0]
        self.assertEqual(result["status"], "failed")
        self.assertIn("exit code 1; Test command timed out after 4s", result["reason"])

    def test_progress_line_names_the_running_check_and_its_limit(self):
        specs = (validation_runner.CheckSpec("Next", "pass.py", "Fake", timeout=77),)
        _, out, _, _ = self.run_fake_suite(specs)
        self.assertIn("[RUN]  Next (time limit 77s)", out)


if __name__ == "__main__":
    unittest.main()
