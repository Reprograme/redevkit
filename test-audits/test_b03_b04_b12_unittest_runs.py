"""B03, B04 and B12: every unittest location runs, isolated, and every summary counts.

Bugs, all reproduced on real projects:

* B03: the root was a discovery start only when it held a ``test*.py``. With a ``tests/``
  package (``tests/__init__.py``) that failed and a green ``test/`` folder that is not a
  package, the runner ran only ``discover -s test``: PASS, exit 0. The same with a failing
  ``mypkg/tests/`` package below the root and a green ``tests/`` folder.
* B12: several starts ran in one process. ``tests/helpers.py`` and ``test/helpers.py``
  imported inside a test (not at the top of the module) resolved to the module of the first
  start: a false FAIL (``'test' != 'tests'``).
* B04: only the LAST unittest summary of the output was read. A wrapper that runs a red
  suite and then a green one (``FAILED (failures=1)`` then ``OK``) and exits 0 was PASS,
  ``1 total, 1 passed, 0 failed``; in the other order FAIL, but with ``1 total`` for two
  tests. pytest (one summary line per session) and Jest/Vitest (one ``Tests:`` line per
  run) had the same "last summary wins" defect.

Decisions: the root is a start when it holds a ``test*.py`` or a package below it does (as
unittest discovery reaches it: through packages only); each start runs in its own process
(its own ``sys.modules`` and ``sys.path``); the parser adds up every summary of the output.
"""
from __future__ import annotations

import sys
import unittest
from unittest import mock

from audit_helpers import TempProject, load_audit, run_main

audit_common = load_audit("audit_common")
test_runner = load_audit("test_runner")

GREEN = "import unittest\nclass G(unittest.TestCase):\n    def test_green(self):\n        self.assertTrue(True)\n"
RED = "import unittest\nclass R(unittest.TestCase):\n    def test_red(self):\n        self.assertEqual(1, 2)\n"


def run(project, *argv: str):
    with mock.patch.object(test_runner, "python_module_available", return_value=False):  # force unittest
        info = test_runner.detect_test_framework(project.root)
        code, out = run_main(test_runner, [str(project.root), *argv])
    return info, code, out


def counts(output: str):
    result = {"tests_passed": 0, "tests_failed": 0, "tests_run": 0, "tests_skipped": 0}
    parsed = test_runner._parse_counts(output, result)
    return parsed, result["tests_run"], result["tests_passed"], result["tests_failed"], result["tests_skipped"]


def verdict(returncode: int, output: str, framework=None):
    done = audit_common.CommandResult(returncode, output, "", False)
    with TempProject() as project, mock.patch.object(test_runner, "run_external", return_value=done):
        result = test_runner.run_tests(["fake"], project.root, framework=framework)
    return result["status"], result["tests_run"], result["tests_passed"], result["tests_failed"]


class TestB03PackagesBelowTheRoot(unittest.TestCase):
    def test_failing_tests_package_with_a_green_test_folder_fails(self):
        with TempProject() as project:
            project.write("requirements.txt", "")
            project.write("tests/__init__.py", "")
            project.write("tests/test_red.py", RED)
            project.write("test/test_green.py", GREEN)
            info, code, out = run(project)
        self.assertEqual(info["cmd"][-2:], [".", "test"])
        self.assertEqual(code, 1, out)
        self.assertIn("[FAIL]", out)
        self.assertIn("Tests: 2 total, 1 passed, 1 failed", out)

    def test_failing_nested_package_with_a_green_tests_folder_fails(self):
        with TempProject() as project:
            project.write("requirements.txt", "")
            project.write("mypkg/__init__.py", "")
            project.write("mypkg/tests/__init__.py", "")
            project.write("mypkg/tests/test_red.py", RED)
            project.write("tests/test_green.py", GREEN)
            info, code, out = run(project)
        self.assertEqual(info["cmd"][-2:], [".", "tests"])
        self.assertEqual(code, 1, out)
        self.assertIn("Tests: 2 total, 1 passed, 1 failed", out)

    def test_root_start_follows_unittest_discovery(self):
        with TempProject() as project:
            project.write("deep/inner/__init__.py", "")
            project.write("deep/inner/test_x.py", GREEN)  # deep/ is not a package: unittest never gets there
            self.assertEqual(test_runner._unittest_start_dirs(project.root), [])
            project.write("deep/__init__.py", "")
            self.assertEqual(test_runner._unittest_start_dirs(project.root), ["."])
            project.write("tests/test_y.py", GREEN)
            self.assertEqual(test_runner._unittest_start_dirs(project.root), [".", "tests"])

    def test_every_test_runs_once(self):
        with TempProject() as project:
            project.write("requirements.txt", "")
            project.write("tests/__init__.py", "")
            project.write("tests/test_pkg.py", GREEN)
            project.write("mypkg/__init__.py", "")
            project.write("mypkg/tests/__init__.py", "")
            project.write("mypkg/tests/test_deep.py", GREEN)
            project.write("test/test_loose.py", GREEN)
            info, code, out = run(project)
        self.assertEqual(info["cmd"][-2:], [".", "test"])
        self.assertEqual(code, 0, out)
        self.assertIn("Tests: 3 total, 3 passed, 0 failed", out)


class TestB12StartsRunIsolated(unittest.TestCase):
    def test_helpers_imported_inside_a_test_are_the_ones_of_its_folder(self):
        where = (
            "import unittest\nclass W(unittest.TestCase):\n    def test_where(self):\n"
            "        import helpers\n        self.assertEqual(helpers.WHERE, {expected!r})\n"
        )
        with TempProject() as project:
            project.write("requirements.txt", "")
            project.write("tests/helpers.py", "WHERE = 'tests'\n")
            project.write("test/helpers.py", "WHERE = 'test'\n")
            project.write("tests/test_where_tests.py", where.format(expected="tests"))
            project.write("test/test_where_test.py", where.format(expected="test"))
            info, code, out = run(project)
        self.assertEqual(info["cmd"][-2:], ["tests", "test"])
        self.assertEqual(code, 0, out)
        self.assertIn("Tests: 2 total, 2 passed, 0 failed", out)

    def test_each_start_has_its_own_process(self):
        check = (
            "import os, unittest\nclass P(unittest.TestCase):\n    def test_pid(self):\n"
            "        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'pids.txt')\n"
            "        with open(path, 'a') as handle:\n            handle.write(str(os.getpid()) + '\\n')\n"
        )
        with TempProject() as project:
            project.write("requirements.txt", "")
            project.write("tests/test_p.py", check)
            project.write("test/test_p.py", check)
            _, code, out = run(project)
            pids = (project.root / "pids.txt").read_text(encoding="utf-8").split()
        self.assertEqual(code, 0, out)
        self.assertEqual(len(pids), 2)
        self.assertNotEqual(pids[0], pids[1])

    def test_a_start_without_tests_does_not_hide_the_others(self):
        with TempProject() as project:
            project.write("requirements.txt", "")
            project.write("tests/test_empty.py", "")  # a start with no test
            project.write("test/test_green.py", GREEN)
            _, code, out = run(project)
        self.assertEqual(code, 0, out)
        self.assertIn("Tests: 1 total, 1 passed, 0 failed", out)

    def test_running_line_names_the_starts(self):
        with TempProject() as project:
            project.write("requirements.txt", "")
            project.write("tests/test_a.py", GREEN)
            project.write("test/test_b.py", GREEN)
            _, code, out = run(project)
        self.assertEqual(code, 0, out)
        self.assertIn(f"-c {test_runner.UNITTEST_MULTI_LABEL} tests test", out)
        running = next(line for line in out.splitlines() if line.startswith("Running: "))
        self.assertNotIn("import subprocess", running)  # the label replaces the script
        self.assertIn("[unittest] discover -s tests", out)


WRAPPER = (
    "import subprocess, sys\n"
    "for folder in sys.argv[1:]:\n"
    "    done = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-v', '-s', folder],\n"
    "                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)\n"
    "    print(done.stdout, flush=True)\n"
    "sys.exit(0)  # a wrapper that loses the exit code\n"
)


class TestB04EverySummaryCounts(unittest.TestCase):
    def test_wrapper_red_then_green_fails_in_both_orders(self):
        for order in ("red green", "green red"):
            with self.subTest(order=order), TempProject() as project:
                project.write("red/test_red.py", RED)
                project.write("green/test_green.py", GREEN)
                project.write("wrapper.py", WRAPPER)
                code, out = run_main(test_runner, [str(project.root), "--cmd", f'"{sys.executable}" wrapper.py {order}'])
                self.assertEqual(code, 1, out)
                self.assertIn("[FAIL]", out)
                self.assertIn("Tests: 2 total, 1 passed, 1 failed", out)

    def test_unittest_summaries_are_added_up(self):
        red_then_green = (
            "test_red ... FAIL\n\n" + "-" * 70 + "\nRan 1 test in 0.001s\n\nFAILED (failures=1)\n"
            "test_green ... ok\n\n" + "-" * 70 + "\nRan 1 test in 0.000s\n\nOK\n"
        )
        green_then_red = (
            "Ran 3 tests in 0.001s\n\nOK (skipped=1)\n"
            "Ran 2 tests in 0.001s\n\nFAILED (failures=1, errors=1)\n"
        )
        self.assertEqual(counts(red_then_green), (True, 2, 1, 1, 0))
        self.assertEqual(counts(green_then_red), (True, 5, 2, 2, 1))
        self.assertEqual(verdict(0, red_then_green), ("failed", 2, 1, 1))

    def test_a_result_line_before_any_summary_is_not_counted(self):
        output = "FAILED (failures=9)\nRan 1 test in 0.001s\n\nOK\n"  # printed by a test, not a summary
        self.assertEqual(counts(output), (True, 1, 1, 0, 0))

    def test_pytest_sessions_are_added_up(self):
        red_then_green = (
            "========================= 1 failed in 0.05s =========================\n"
            "========================= 1 passed in 0.01s =========================\n"
        )
        green_then_red = "".join(reversed(red_then_green.splitlines(keepends=True)))
        quiet = "1 passed, 1 skipped in 0.01s\n2 failed, 3 passed in 0.10s\n"
        self.assertEqual(counts(red_then_green), (True, 2, 1, 1, 0))
        self.assertEqual(counts(quiet), (True, 6, 4, 2, 1))
        self.assertEqual(verdict(0, red_then_green, "pytest"), ("failed", 2, 1, 1))
        self.assertEqual(verdict(0, green_then_red, "pytest"), ("failed", 2, 1, 1))

    def test_jest_and_vitest_runs_are_added_up(self):
        jest = (
            "Tests:       1 failed, 1 total\nTime:        0.5 s\n"
            "Tests:       1 passed, 1 total\nTime:        0.4 s\n"
        )
        vitest = " Test Files  1 passed (1)\n      Tests  1 passed (1)\n Test Files  1 failed (1)\n      Tests  1 failed (1)\n"
        self.assertEqual(counts(jest), (True, 2, 1, 1, 0))
        self.assertEqual(counts(vitest), (True, 2, 1, 1, 0))
        self.assertEqual(verdict(0, jest, "jest"), ("failed", 2, 1, 1))
        self.assertEqual(verdict(0, vitest, "vitest"), ("failed", 2, 1, 1))

    def test_one_summary_is_counted_once(self):
        self.assertEqual(counts("Tests:       1 failed, 2 passed, 1 skipped, 4 total\n"), (True, 4, 2, 1, 1))
        self.assertEqual(counts("=== 1 failed, 2 passed, 1 skipped in 0.02s ===\n"), (True, 3, 2, 1, 1))
        self.assertEqual(counts("Ran 4 tests in 0.002s\n\nFAILED (failures=1, skipped=1)\n"), (True, 4, 2, 1, 1))

    def test_cargo_surefire_and_dotnet_already_add_up(self):
        cargo = (
            "test result: FAILED. 1 passed; 1 failed; 0 ignored; 0 measured; 0 filtered out\n"
            "test result: ok. 2 passed; 0 failed; 1 ignored; 0 measured; 0 filtered out\n"
        )
        surefire = "[INFO] Tests run: 2, Failures: 1, Errors: 0, Skipped: 0\n[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 1\n"
        dotnet = (
            "Failed!  - Failed:     1, Passed:     1, Skipped:     0, Total:     2, Duration: 5 ms - a.dll\n"
            "Passed!  - Failed:     0, Passed:     3, Skipped:     1, Total:     4, Duration: 5 ms - b.dll\n"
        )
        self.assertEqual(counts(cargo), (True, 4, 3, 1, 1))
        self.assertEqual(counts(surefire), (True, 5, 3, 1, 1))
        self.assertEqual(counts(dotnet), (True, 6, 4, 1, 1))


if __name__ == "__main__":
    unittest.main()
