"""S17: test_runner.py verdicts, counts and evidence.

Bugs, all reproduced on real projects:

* PASS although no test ran: ``node --test`` without test files ("tests 0", exit 0) and
  ``"test": "echo ok"`` were ``[PASS] All tests passed``.
* SKIPPED although a test failed: ``tests/test_x.py`` without ``tests/__init__.py`` is
  invisible to ``unittest discover`` from the project root ("no tests found").
* Exit code 5 of ANY command meant "no tests found" (a crashing ``npm test`` was SKIPPED).
* FAIL where nothing could be verified: declared framework not installed ("'vitest' is
  not recognized"), and vitest/jest "No test files found".
* ``--coverage`` failed a passing suite when the coverage provider was missing.
* Wrong counts: vitest colours its output on Windows even when piped (the file count was
  reported), pytest ``-v`` test names ending in digits ("test_case_10 PASSED"), node:test
  and unittest were not parsed.
* Only the FIRST 30 lines of output were shown: the failures and the summary are at the end.
* Python tests ran with the interpreter of the audit, never the project's ``.venv``.
"""
from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

from audit_helpers import TempProject, load_audit, run_main

audit_common = load_audit("audit_common")
test_runner = load_audit("test_runner")

NODE_TEST_EMPTY = "> x@1.0.0 test\n> node --test\n\nℹ tests 0\nℹ suites 0\nℹ pass 0\nℹ fail 0\nℹ cancelled 0\n"
NODE_TEST_SPEC = "✔ adds (0.4ms)\n✖ broken (0.5ms)\nℹ tests 2\nℹ suites 0\nℹ pass 1\nℹ fail 1\nℹ cancelled 0\n"
NODE_TEST_TAP = "TAP version 13\nok 1 - adds\n1..3\n# tests 3\n# pass 3\n# fail 0\n# cancelled 0\n"
VITEST_ANSI = (
    "\x1b[2m Test Files \x1b[22m \x1b[1m\x1b[32m3 passed\x1b[39m\x1b[22m\x1b[90m (3)\x1b[39m\n"
    "\x1b[2m      Tests \x1b[22m \x1b[1m\x1b[32m22 passed\x1b[39m\x1b[22m\x1b[90m (22)\x1b[39m\n"
)
VITEST_NO_FILES = "\x1b[31mNo test files found, exiting with code 1\x1b[39m\n\ninclude: **/*.{test,spec}.?(c|m)[jt]s?(x)\n"
JEST_NO_TESTS = "No tests found, exiting with code 1\nRun with `--passWithNoTests` to exit with code 0\n"
PYTEST_VERBOSE = (
    "test_calc.py::test_case_10 PASSED                                  [ 33%]\n"
    "test_calc.py::test_v3 FAILED                                       [ 66%]\n"
    "test_calc.py::test_plain PASSED                                    [100%]\n\n"
    "=================== 1 failed, 2 passed, 1 warning in 0.02s ===================\n"
)


def counts(output: str):
    result = {"tests_passed": 0, "tests_failed": 0, "tests_run": 0}
    parsed = test_runner._parse_counts(output, result)
    return parsed, result["tests_run"], result["tests_passed"], result["tests_failed"]


def verdict(returncode: int, output: str, framework: str = "npm test"):
    """Status and reason run_tests gives a finished command with this exit code and output."""
    done = audit_common.CommandResult(returncode, output, "", False)
    with TempProject() as project, mock.patch.object(test_runner, "run_external", return_value=done):
        result = test_runner.run_tests(["fake"], project.root, framework=framework)
    return result["status"], result["error"]


def json_tail(out: str) -> dict:
    return json.loads(out[out.rindex("\n{") + 1:])


def framework(cmd, coverage_cmd=None, reason="coverage provider not installed", name="vitest"):
    return {"type": "node", "framework": name, "cmd": cmd, "coverage_cmd": coverage_cmd,
            "coverage_skip_reason": reason, "skip_reason": None}


class TestS17ZeroTestsIsNeverPass(unittest.TestCase):
    def test_summary_with_zero_tests_and_exit_0_is_skipped(self):
        self.assertEqual(verdict(0, NODE_TEST_EMPTY), ("skipped", "no tests found"))
        self.assertEqual(verdict(0, "\nRan 0 tests in 0.000s\n\nOK\n", "unittest"), ("skipped", "no tests found"))
        self.assertEqual(verdict(0, "===== no tests ran in 0.01s =====\n", "pytest"), ("skipped", "no tests found"))

    def test_exit_0_without_any_test_result_is_skipped(self):
        echo = "> x@1.0.0 test\n> echo no tests yet\n\nno tests yet\n"
        self.assertEqual(verdict(0, echo), ("skipped", test_runner.NO_TEST_RESULT))
        self.assertEqual(verdict(0, ""), ("skipped", test_runner.NO_TEST_RESULT))
        # npm echoes the script: the words of the command line are not a test result
        self.assertEqual(verdict(0, "> x@1.0.0 test\n> run 12 tests --quiet\n\ndone\n")[0], "skipped")

    def test_recognised_summary_with_tests_is_pass(self):
        self.assertEqual(verdict(0, NODE_TEST_TAP)[0], "passed")
        self.assertEqual(verdict(0, VITEST_ANSI, "vitest")[0], "passed")
        self.assertEqual(verdict(0, "Ran 3 tests in 0.001s\n\nOK\n", "unittest")[0], "passed")

    def test_unknown_format_that_clearly_ran_tests_is_pass_not_skipped(self):
        # The rule: an output the runner cannot count still passes when it shows executed tests.
        for output in (
            "ok 1 - adds\nok 2 - subs\n",                           # TAP without a summary
            "5 specs, 0 failures\nFinished in 0.01 seconds\n",       # jasmine
            "OK (5 tests, 10 assertions)\n",                         # PHPUnit
            "ok  \texample.com/pkg\t0.012s\n",                       # go test
            "PASS src/a.test.js\n",                                  # a runner that only lists files
            "Passed!  - Failed: 0, Passed: 5, Skipped: 0, Total: 5\n",  # dotnet test
            "  ✓ adds two numbers\n  ✓ subtracts\n",                 # check marks only
            "All good: 14 checks passed\n",
        ):
            with self.subTest(output.strip()[:30]):
                self.assertTrue(test_runner.has_test_evidence(output))
                self.assertEqual(verdict(0, output)[0], "passed")
        for output in ("no tests yet\n", "ok\n", "done in 0 ms\n", "0 tests\n"):
            with self.subTest(output.strip()):
                self.assertFalse(test_runner.has_test_evidence(output))

    def test_real_unittest_project_passes_and_empty_one_is_skipped(self):
        with mock.patch.object(test_runner, "python_module_available", return_value=False):  # force unittest
            with TempProject("S17/root-tests") as project:
                code, out = run_main(test_runner, [str(project.root)])
            self.assertEqual(code, 0, out)
            self.assertIn("Tests: 2 total, 2 passed, 0 failed", out)
            with TempProject() as project:
                project.write("pyproject.toml", '[project]\nname = "empty"\nversion = "0"\n')
                code, out = run_main(test_runner, [str(project.root)])
            self.assertEqual(code, 3, out)
            self.assertNotIn("[PASS]", out)


class TestS17UnittestDiscovery(unittest.TestCase):
    def test_tests_folder_without_init_is_the_start_directory(self):
        with TempProject("S17/tests-dir") as project, \
                mock.patch.object(test_runner, "python_module_available", return_value=False):
            info = test_runner.detect_test_framework(project.root)
            code, out = run_main(test_runner, [str(project.root)])
        self.assertEqual(info["cmd"][-2:], ["-s", "tests"])
        self.assertEqual(code, 1, out)  # one test fails: FAIL, never "SKIPPED (no tests found)"
        self.assertIn("Tests: 2 total, 1 passed, 1 failed", out)
        self.assertEqual(json_tail(out)["status"], "failed")

    def test_other_layouts_keep_the_default_discovery(self):
        with TempProject("S17/root-tests") as project:
            self.assertEqual(test_runner._unittest_discover_args(project.root), [])  # test files in the root
            project.write("tests/test_more.py", "")
            self.assertEqual(test_runner._unittest_discover_args(project.root), [])
        with TempProject() as project:
            project.write("tests/__init__.py", "")
            project.write("tests/test_pkg.py", "")
            self.assertEqual(test_runner._unittest_discover_args(project.root), [])  # a package: found from the root
            (project.root / "tests" / "__init__.py").unlink()
            self.assertEqual(test_runner._unittest_discover_args(project.root), ["-s", "tests"])
        with TempProject() as project:
            project.write("test/test_x.py", "")
            self.assertEqual(test_runner._unittest_discover_args(project.root), ["-s", "test"])


class TestS17ExitCodes(unittest.TestCase):
    def test_exit_5_means_no_tests_only_for_pytest_and_unittest(self):
        self.assertEqual(verdict(5, "boom: crashed\n", "npm test"), ("failed", "exit code 5"))
        self.assertEqual(verdict(5, "boom: crashed\n", "vitest")[0], "failed")
        self.assertEqual(verdict(5, "collected 0 items\n\n=== no tests ran in 0.01s ===\n", "pytest"), ("skipped", "no tests found"))
        self.assertEqual(verdict(5, "\nRan 0 tests in 0.000s\n\nNO TESTS RAN\n", "unittest"), ("skipped", "no tests found"))

    def test_runner_that_found_no_test_file_is_skipped(self):
        self.assertEqual(verdict(1, VITEST_NO_FILES, "vitest"), ("skipped", "no tests found"))
        self.assertEqual(verdict(1, JEST_NO_TESTS, "jest"), ("skipped", "no tests found"))

    def test_failures_stay_failures(self):
        self.assertEqual(verdict(1, NODE_TEST_SPEC), ("failed", "exit code 1"))
        self.assertEqual(verdict(1, "Tests:       1 failed, 2 passed, 3 total\nNo tests found, exiting with code 1\n", "jest")[0], "failed")
        self.assertEqual(verdict(1, "'vitest' is not recognized as an internal or external command\n")[0], "failed")


class TestS17FrameworkNotInstalled(unittest.TestCase):
    PACKAGE = '{"scripts": {"test": "vitest run"}, "devDependencies": {"vitest": "^3.0.0"}}'

    def test_declared_framework_without_binary_is_skipped(self):
        with TempProject() as project, mock.patch.object(test_runner, "local_bin", return_value=None), \
                mock.patch.object(test_runner, "run_external") as run:
            project.write("package.json", self.PACKAGE)
            info = test_runner.detect_test_framework(project.root)
            code, out = run_main(test_runner, [str(project.root)])
        run.assert_not_called()
        self.assertIsNone(info["cmd"])
        self.assertEqual(code, 3, out)
        self.assertIn("SKIPPED (vitest is not installed in node_modules/.bin (run the package install first))", out)

    def test_installed_framework_runs_the_project_script(self):
        with TempProject() as project, mock.patch.object(test_runner, "local_bin", return_value="vitest.cmd"), \
                mock.patch.object(test_runner.shutil, "which", return_value="npm.cmd"):
            project.write("package.json", self.PACKAGE)
            info = test_runner.detect_test_framework(project.root)
        self.assertEqual((info["framework"], info["cmd"]), ("vitest", ["npm.cmd", "test"]))

    def test_local_bin_looks_in_parent_folders(self):
        # Workspaces hoist dependencies: the binary is in the root node_modules/.bin.
        name = "vitest.cmd" if os.name == "nt" else "vitest"
        with TempProject() as project:
            binary = project.write(f"node_modules/.bin/{name}", "@echo off\r\n" if os.name == "nt" else "#!/bin/sh\n")
            binary.chmod(0o755)
            package = project.root / "packages" / "app"
            package.mkdir(parents=True)
            found = test_runner.local_bin(package, "vitest")
        self.assertIsNotNone(found)
        self.assertEqual(Path(found).name.lower(), name)


class TestS17Coverage(unittest.TestCase):
    PASSING = audit_common.CommandResult(0, " Test Files  1 passed (1)\n      Tests  2 passed (2)\n", "", False)

    def test_vitest_coverage_needs_its_provider(self):
        package = '{"scripts": {"test": "vitest run"}, "devDependencies": {"vitest": "^3.0.0"}}'
        with TempProject() as project, mock.patch.object(test_runner, "local_bin", return_value="vitest.cmd"), \
                mock.patch.object(test_runner.shutil, "which", return_value="npm.cmd"):
            project.write("package.json", package)
            missing = test_runner.detect_test_framework(project.root)
            project.write("node_modules/@vitest/coverage-v8/package.json", "{}")
            installed = test_runner.detect_test_framework(project.root)
        self.assertIsNone(missing["coverage_cmd"])
        self.assertEqual(missing["coverage_skip_reason"], "coverage provider not installed")
        self.assertEqual(installed["coverage_cmd"], ["vitest.cmd", "run", "--coverage"])

    def test_missing_provider_runs_the_suite_and_says_coverage_was_skipped(self):
        info = framework(["npm.cmd", "test"])
        with TempProject() as project, mock.patch.object(test_runner, "detect_test_framework", return_value=info), \
                mock.patch.object(test_runner, "run_external", return_value=self.PASSING) as run:
            code, out = run_main(test_runner, [str(project.root), "--coverage"])
        self.assertEqual(run.call_args.args[0], ["npm.cmd", "test"])  # the normal command, not `--coverage`
        self.assertEqual(code, 0, out)  # passing tests stay PASS
        self.assertIn("SKIPPED (coverage provider not installed)", out)
        self.assertIn("[PASS] All tests passed", out)
        self.assertEqual(json_tail(out)["coverage"], "skipped (coverage provider not installed)")

    def test_installed_provider_runs_the_coverage_command(self):
        info = framework(["npm.cmd", "test"], coverage_cmd=["vitest.cmd", "run", "--coverage"])
        with TempProject() as project, mock.patch.object(test_runner, "detect_test_framework", return_value=info), \
                mock.patch.object(test_runner, "run_external", return_value=self.PASSING) as run:
            code, out = run_main(test_runner, [str(project.root), "--coverage"])
            self.assertEqual(run.call_args.args[0], ["vitest.cmd", "run", "--coverage"])
            self.assertNotIn("SKIPPED", out)
            self.assertEqual((code, json_tail(out)["coverage"]), (0, "collected"))
            code, out = run_main(test_runner, [str(project.root)])
            self.assertEqual(json_tail(out)["coverage"], "not requested")

    def test_pytest_coverage_needs_pytest_cov(self):
        def available(module, python=None):
            return module == "pytest"

        with TempProject() as project, mock.patch.object(test_runner, "python_module_available", side_effect=available):
            project.write("pytest.ini", "[pytest]\n")
            info = test_runner.detect_test_framework(project.root)
        self.assertEqual(info["cmd"][1:], ["-m", "pytest", "-v"])
        self.assertIsNone(info["coverage_cmd"])
        self.assertEqual(info["coverage_skip_reason"], "coverage provider not installed")


class TestS17Counts(unittest.TestCase):
    def test_vitest_colour_codes_do_not_hide_the_tests_line(self):
        self.assertEqual(counts(VITEST_ANSI), (True, 22, 22, 0))

    def test_pytest_counts_come_from_the_summary_not_from_test_names(self):
        self.assertEqual(counts(PYTEST_VERBOSE), (True, 3, 2, 1))
        self.assertEqual(counts("3 passed in 0.01s\n"), (True, 3, 3, 0))
        self.assertEqual(counts("===== 2 passed, 1 error in 1.50s (0:00:01) =====\n"), (True, 3, 2, 1))

    def test_node_test_reporters(self):
        self.assertEqual(counts(NODE_TEST_SPEC), (True, 2, 1, 1))
        self.assertEqual(counts(NODE_TEST_TAP), (True, 3, 3, 0))
        self.assertEqual(counts(NODE_TEST_EMPTY), (True, 0, 0, 0))

    def test_unittest_results(self):
        self.assertEqual(counts("Ran 3 tests in 0.001s\n\nOK\n"), (True, 3, 3, 0))
        self.assertEqual(counts("Ran 6 tests in 0.001s\n\nFAILED (failures=2, errors=1, skipped=1)\n"), (True, 6, 2, 3))
        self.assertEqual(counts("Ran 4 tests in 0.001s\n\nOK (skipped=1, expected failures=1)\n"), (True, 4, 2, 0))

    def test_other_runners(self):
        self.assertEqual(counts("  5 passing (12ms)\n  1 failing\n"), (True, 6, 5, 1))
        self.assertEqual(counts("test result: ok. 7 passed; 0 failed; 0 ignored\n"), (True, 7, 7, 0))
        self.assertEqual(counts("Tests:       2 failed, 20 passed, 22 total\n"), (True, 22, 20, 2))
        self.assertEqual(counts("nothing that looks like a summary\n"), (False, 0, 0, 0))


class TestS17Evidence(unittest.TestCase):
    LONG = "".join(f"line {number}\n" for number in range(1, 101)) + "FAIL last-line-with-the-failure\nRan 1 test in 0.1s\n\nFAILED (failures=1)\n"

    def run_long(self, extra=()):
        done = audit_common.CommandResult(1, self.LONG, "", False)
        with TempProject() as project, \
                mock.patch.object(test_runner, "detect_test_framework", return_value=framework(["fake"], name="unittest")), \
                mock.patch.object(test_runner, "run_external", return_value=done):
            log = project.root / "logs" / "test-output.log"
            argv = [str(project.root), *(["--log", str(log)] if extra else [])]
            code, out = run_main(test_runner, argv)
            written = log.read_text(encoding="utf-8") if log.exists() else None
        return code, out, written

    def test_the_end_of_the_output_is_shown(self):
        code, out, _ = self.run_long()
        self.assertEqual(code, 1)
        self.assertIn("FAIL last-line-with-the-failure", out)  # the failure is at the end
        self.assertIn("line 100\n", out)
        self.assertNotIn("line 1\n", out)
        omitted = len(self.LONG.rstrip("\n").split("\n")) - test_runner.TAIL_LINES
        self.assertIn(f"... ({omitted} earlier lines omitted; --log FILE keeps the full output)", out)

    def test_log_option_writes_the_full_output(self):
        code, out, written = self.run_long(extra=True)
        self.assertEqual(written, self.LONG)
        self.assertIn("Log: ", out)
        self.assertTrue(json_tail(out)["log"].endswith("test-output.log"))


class TestS17ProjectInterpreter(unittest.TestCase):
    def venv_python(self, project, folder=".venv") -> Path:
        relative = f"{folder}/Scripts/python.exe" if os.name == "nt" else f"{folder}/bin/python"
        return project.write(relative, "")

    def test_project_virtual_environment_is_used(self):
        with TempProject() as project:
            self.assertEqual(test_runner.project_python(project.root), sys.executable)
            other = self.venv_python(project, "venv")
            self.assertEqual(test_runner.project_python(project.root), str(other))
            preferred = self.venv_python(project, ".venv")
            self.assertEqual(test_runner.project_python(project.root), str(preferred))
            project.write("requirements.txt", "requests==2.0.0\n")
            with mock.patch.object(test_runner, "python_module_available", return_value=True) as available:
                info = test_runner.detect_test_framework(project.root)
            self.assertEqual(info["cmd"][:3], [str(preferred), "-m", "pytest"])
            available.assert_any_call("pytest", str(preferred))
            with mock.patch.object(test_runner, "python_module_available", return_value=False):
                info = test_runner.detect_test_framework(project.root)
            self.assertEqual(info["cmd"][:4], [str(preferred), "-m", "unittest", "discover"])

    def test_modules_of_another_interpreter_are_probed_by_running_it(self):
        found = audit_common.CommandResult(0, "", "", False)
        missing = audit_common.CommandResult(1, "", "", False)
        with mock.patch.object(test_runner, "run_external", return_value=found) as run:
            self.assertTrue(test_runner.python_module_available("pytest", "/project/.venv/bin/python"))
        self.assertEqual(run.call_args.args[0][:2], ["/project/.venv/bin/python", "-c"])
        with mock.patch.object(test_runner, "run_external", return_value=missing):
            self.assertFalse(test_runner.python_module_available("pytest", "/project/.venv/bin/python"))
        with mock.patch.object(test_runner, "run_external", side_effect=OSError("cannot start")):
            self.assertFalse(test_runner.python_module_available("pytest", "/project/.venv/bin/python"))
        with mock.patch.object(test_runner, "run_external") as run:
            self.assertTrue(test_runner.python_module_available("unittest"))  # the current interpreter: no process
        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
