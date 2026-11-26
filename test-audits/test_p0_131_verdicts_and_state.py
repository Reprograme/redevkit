"""1.3.1 P0: verdicts and code state that a production audit of 1.3.0 reproduced as wrong.

* TR1: only the last PHPUnit summary was read: "Tests: 4, ..., Failures: 1." then
  "OK (4 tests, 4 assertions)" with exit 0 was PASS. Every summary now adds up, and a failure
  line of any known runner makes a run that exited 0 FAIL.
* TR3: a check mark printed by npm's ``pretest`` build ("✓ 34 modules transformed.") counted as
  test evidence, so a test script that ran no test was PASS.
* TR4: ``unittest discover`` skipped ``tests/unit/`` without ``__init__.py``: its failing tests
  never ran and the suite was PASS.
* TR2: on Windows a ``.cmd``/``.bat`` test command received ``--paths`` unquoted: a file named
  ``t&ver`` ran ``ver`` and changed the exit code.
* CS1: a project inside another repository that ignores the project folder hashed 0 files (the
  sha256 of nothing), so an edit left the fingerprint unchanged and the deploy would accept
  untested code.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import unittest
from unittest import mock

from audit_helpers import TempProject, load_audit, run_main

audit_common = load_audit("audit_common")
test_runner = load_audit("test_runner")
code_state = load_audit("code_state")
GIT = shutil.which("git")
EMPTY_SHA256 = "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def verdict(returncode: int, output: str, framework: str = "npm test"):
    done = audit_common.CommandResult(returncode, output, "", False)
    with TempProject() as project, mock.patch.object(test_runner, "run_external", return_value=done):
        result = test_runner.run_tests(["fake"], project.root, framework=framework)
    return result["status"], result["error"]


class TestTR1EveryFailureCounts(unittest.TestCase):
    def test_red_phpunit_run_before_a_green_one_is_fail(self):
        output = "Tests: 4, Assertions: 4, Failures: 1.\nFAILURES!\nOK (4 tests, 4 assertions)\n"
        status, reason = verdict(0, output, "phpunit")
        self.assertEqual(status, "failed")
        self.assertIn("1 failed", reason)

    def test_rspec_and_minitest_summaries_add_up(self):
        rspec = "3 examples, 1 failure\n\n3 examples, 0 failures\n"
        self.assertEqual(verdict(0, rspec, "rspec")[0], "failed")
        minitest = ("2 runs, 2 assertions, 0 failures, 1 errors, 0 skips\n"
                    "2 runs, 2 assertions, 0 failures, 0 errors, 0 skips\n")
        self.assertEqual(verdict(0, minitest, "rails test")[0], "failed")

    def test_failure_of_another_runner_than_the_parsed_one_is_fail(self):
        # A wrapper that runs mocha (red) and then a jest suite (green), losing the exit code.
        output = "  2 passing\n  1 failing\n\nTests:       5 passed, 5 total\n"
        status, reason = verdict(0, output)
        self.assertEqual(status, "failed")
        self.assertIn("1 failing", reason)

    def test_failure_signals_of_known_runners(self):
        for line in ("FAILED (failures=1)", "=== 1 failed, 2 passed in 0.12s ===", "ℹ fail 2",
                     "test result: FAILED. 1 passed; 1 failed; 0 ignored", "not ok 3 - adds",
                     "--- FAIL: TestAdd (0.00s)", "FAIL src/a.test.js",
                     "Tests run: 4, Failures: 0, Errors: 1, Skipped: 0"):
            with self.subTest(line=line):
                self.assertIsNotNone(test_runner.failure_signal(f"noise\n{line}\nmore\n"))

    def test_green_output_has_no_failure_signal(self):
        for output in ("ℹ tests 2\nℹ pass 2\nℹ fail 0\n", "=== 3 passed, 1 xfailed in 0.1s ===",
                       "not ok 2 - later # TODO not built\nok 1\n", "FAILED (failures=0)x",
                       "Tests:       5 passed, 5 total\n", "  console.log\n    FAIL text logged by a test\n"):
            with self.subTest(output=output):
                self.assertIsNone(test_runner.failure_signal(output))

    def test_green_runs_stay_pass(self):
        self.assertEqual(verdict(0, "OK (4 tests, 4 assertions)\nOK (2 tests, 2 assertions)\n", "phpunit")[0], "passed")
        self.assertEqual(verdict(0, "ℹ tests 2\nℹ pass 2\nℹ fail 0\n", "node --test")[0], "passed")


class TestTR3PretestOutputIsNoEvidence(unittest.TestCase):
    def test_check_mark_of_the_pretest_build_is_not_a_test(self):
        output = ("> x@1.0.0 pretest\n> node build.js\n\n✓ 34 modules transformed.\n\n"
                  "> x@1.0.0 test\n> node run.js\n\nno test files matched\n")
        self.assertFalse(test_runner.has_test_evidence(output))
        self.assertEqual(verdict(0, output)[0], "skipped")

    def test_build_lines_with_a_check_mark_are_not_tests(self):
        for line in ("✓ 34 modules transformed.", "✓ built in 1.2s", "✔ Compiled successfully"):
            with self.subTest(line=line):
                self.assertFalse(test_runner.has_test_evidence(line + "\n"))

    def test_check_marks_of_the_test_script_still_count(self):
        output = ("> x@1.0.0 pretest\n> node build.js\nbuilt\n\n"
                  "> x@1.0.0 test\n> node run.js\n\n  ✓ adds two numbers\n")
        self.assertTrue(test_runner.has_test_evidence(output))

    def test_posttest_output_is_not_evidence(self):
        output = "> x@1.0.0 test\n> node run.js\nnothing\n\n> x@1.0.0 posttest\n> node report.js\n✓ adds\n"
        self.assertFalse(test_runner.has_test_evidence(output))


class TestTR4UnittestReachesEveryTestFolder(unittest.TestCase):
    def test_subfolder_without_init_becomes_a_start(self):
        with TempProject() as project:
            project.write("requirements.txt", "")
            project.write("tests/test_smoke.py", "")
            project.write("tests/unit/test_core.py", "")
            self.assertEqual(test_runner._unittest_start_dirs(project.root), ["tests", "tests/unit"])

    def test_package_chain_is_reached_by_its_start(self):
        with TempProject() as project:
            project.write("tests/test_a.py", "")
            project.write("tests/unit/__init__.py", "")
            project.write("tests/unit/test_b.py", "")
            project.write("tests/unit/deep/__init__.py", "")
            project.write("tests/unit/deep/test_c.py", "")
            self.assertEqual(test_runner._unittest_start_dirs(project.root), ["tests"])

    def test_root_package_with_a_plain_subfolder(self):
        with TempProject() as project:
            project.write("tests/__init__.py", "")
            project.write("tests/test_a.py", "")
            project.write("tests/integration/test_b.py", "")
            project.write("tests/fixtures/test_data.py", "")  # data, never a start
            self.assertEqual(test_runner._unittest_start_dirs(project.root), [".", "tests/integration"])

    def test_failing_test_in_the_subfolder_fails_the_run(self):
        ok = "import unittest\nclass T(unittest.TestCase):\n    def test_ok(self): pass\n"
        bad = "import unittest\nclass T(unittest.TestCase):\n    def test_bad(self): self.fail('red')\n"
        with TempProject() as project:
            project.write("requirements.txt", "")
            project.write("tests/test_smoke.py", ok)
            project.write("tests/unit/test_core.py", bad)
            with mock.patch.object(test_runner, "python_module_available", return_value=False), \
                    mock.patch.object(test_runner, "project_python", return_value=sys.executable):
                code, out = run_main(test_runner, [str(project.root)])
            self.assertEqual(code, test_runner.EXIT_FAIL, out)
            self.assertIn("test_bad", out)


class TestTR2BatchArguments(unittest.TestCase):
    def test_unquotable_arguments_are_found(self):
        self.assertEqual(audit_common.unsafe_batch_argument(["C:/x/run.cmd", "a.js", "t%PATH%x"]), "t%PATH%x")
        self.assertEqual(audit_common.unsafe_batch_argument(["run.BAT", 'say"hi']), 'say"hi')
        self.assertIsNone(audit_common.unsafe_batch_argument(["run.cmd", "t&ver", "a|b", "(x)"]))  # quoted
        self.assertIsNone(audit_common.unsafe_batch_argument(["node.exe", "t%PATH%x"]))  # no cmd.exe

    @unittest.skipUnless(os.name == "nt", "cmd.exe runs .cmd files on Windows only")
    def test_ampersand_in_a_path_reaches_the_script_quoted_and_runs_nothing(self):
        with TempProject() as project:
            project.write("runtests.cmd", "@echo off\r\necho args: %*\r\necho not ok 1 - fails\r\nexit /b 1\r\n")
            project.write("t&ver", "")
            code, out = run_main(test_runner, [str(project.root), "--cmd", "./runtests.cmd {paths}", "--paths", "t&ver"])
            self.assertEqual(code, test_runner.EXIT_FAIL, out)
            self.assertIn('args: "t&ver"', out)
            self.assertNotIn("Microsoft Windows", out)  # `ver` never ran

    @unittest.skipUnless(os.name == "nt", "cmd.exe runs .cmd files on Windows only")
    def test_percent_in_a_path_is_a_usage_error(self):
        with TempProject() as project:
            project.write("runtests.cmd", "@echo off\r\nexit /b 0\r\n")
            project.write("t%PATH%x", "")
            code, out = run_main(test_runner, [str(project.root), "--cmd", "./runtests.cmd {paths}", "--paths", "t%PATH%x"])
            self.assertEqual(code, test_runner.EXIT_USAGE, out)
            self.assertIn("cmd.exe expands", out)

    @unittest.skipUnless(os.name == "nt", "cmd.exe runs .cmd files on Windows only")
    def test_run_external_refuses_before_starting(self):
        with self.assertRaises(audit_common.UnsafeCommandLine):
            audit_common.run_external(["C:/nowhere/run.cmd", "50%"], timeout=5)


def git(cwd, *args: str) -> None:
    subprocess.run(
        [GIT, "-c", "user.name=test", "-c", "user.email=test@example.com", "-c", "commit.gpgsign=false", *args],
        cwd=str(cwd), stdin=subprocess.DEVNULL, capture_output=True, check=True, timeout=60,
    )


@unittest.skipUnless(GIT, "git is not installed")
class TestCS1ProjectIgnoredByAnEnclosingRepository(unittest.TestCase):
    def test_edit_changes_the_fingerprint(self):
        with TempProject() as outer:
            git(outer.root, "init", "-q", ".")
            outer.write(".gitignore", "temp/\n")
            outer.write("temp/proj/src/a.py", "x = 1\n")
            project = outer.root / "temp" / "proj"
            before = code_state.compute(project)
            self.assertEqual(before["basis"], "walk")
            self.assertEqual(before["files"], 1)
            self.assertNotEqual(before["tree_fingerprint"], EMPTY_SHA256)
            self.assertIn("ignored by the enclosing git repository", before["head"])
            (project / "src" / "a.py").write_text("x = 2\n", encoding="utf-8")
            self.assertNotEqual(code_state.compute(project)["tree_fingerprint"], before["tree_fingerprint"])

    def test_subfolder_of_a_repository_that_lists_it_keeps_the_git_basis(self):
        with TempProject() as outer:
            git(outer.root, "init", "-q", ".")
            outer.write("packages/app/src/a.py", "x = 1\n")
            state = code_state.compute(outer.root / "packages" / "app")
            self.assertEqual(state["basis"], "git")
            self.assertEqual(state["files"], 1)

    def test_subfolder_git_lists_nothing_of_falls_back_to_the_walk(self):
        with TempProject() as outer:
            git(outer.root, "init", "-q", ".")
            outer.write(".gitignore", "*.py\n")  # every file of the project is ignored, not the folder
            outer.write("app/src/a.py", "x = 1\n")
            state = code_state.compute(outer.root / "app")
            self.assertEqual(state["basis"], "walk")
            self.assertEqual(state["files"], 1)


if __name__ == "__main__":
    unittest.main()
