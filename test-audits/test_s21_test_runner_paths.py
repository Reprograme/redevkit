"""S21: test_runner.py --paths (spec scope of redevkit-test, kit 1.2.0).

redevkit-test runs only the tests of the active spec; redevkit-verify runs the whole
suite. The runner restricts the command to the given test files when the framework takes
files (vitest, jest, pytest, unittest, also through ``npm test --``) and otherwise runs the
whole suite and says so, so the report can record ``Scope: spec (full suite)``.
"""
from __future__ import annotations

import json
import unittest
from unittest import mock

from audit_helpers import TempProject, load_audit, run_main

audit_common = load_audit("audit_common")
test_runner = load_audit("test_runner")

PASSING = audit_common.CommandResult(0, "Ran 2 tests in 0.01s\n\nOK\n", "", False)


def json_tail(out: str) -> dict:
    return json.loads(out[out.rindex("\n{") + 1:])


def info(cmd, name):
    return {"type": "node", "framework": name, "cmd": cmd, "coverage_cmd": None,
            "coverage_skip_reason": "x", "skip_reason": None}


class TestS21ScopedCommand(unittest.TestCase):
    def test_frameworks_that_take_files(self):
        paths = ["tests/a.test.ts", "tests/b.test.ts"]
        self.assertEqual(test_runner.scoped_command(["vitest", "run"], "vitest", paths), ["vitest", "run", *paths])
        self.assertEqual(test_runner.scoped_command(["jest"], "jest", paths), ["jest", "--runTestsByPath", *paths])
        self.assertEqual(
            test_runner.scoped_command(["py", "-m", "pytest", "-v"], "pytest", ["tests/test_a.py"]),
            ["py", "-m", "pytest", "-v", "tests/test_a.py"],
        )
        self.assertEqual(
            test_runner.scoped_command(["py", "-m", "unittest", "discover", "-v", "-s", "tests"], "unittest", ["tests/test_a.py"]),
            ["py", "-m", "unittest", "-v", "tests/test_a.py"],
        )

    def test_npm_test_passes_files_after_double_dash_only_for_known_frameworks(self):
        self.assertEqual(test_runner.scoped_command(["npm", "test"], "vitest", ["a.test.js"]), ["npm", "test", "--", "a.test.js"])
        self.assertEqual(
            test_runner.scoped_command(["npm", "test"], "jest", ["a.test.js"]),
            ["npm", "test", "--", "--runTestsByPath", "a.test.js"],
        )
        self.assertIsNone(test_runner.scoped_command(["npm", "test"], "npm test", ["a.test.js"]))


class TestS21NodeTestScript(unittest.TestCase):
    def detect(self, script):
        with TempProject() as project, mock.patch.object(test_runner, "which", return_value="npm"):
            project.write("package.json", json.dumps({"name": "x", "scripts": {"test": script}}))
            return test_runner.detect_test_framework(project.root)

    def test_bare_node_test_script_takes_files(self):
        for script in ("node --test", "node --test --test-reporter=spec"):
            found = self.detect(script)
            self.assertEqual(found["framework"], "node --test", script)
            self.assertEqual(
                test_runner.scoped_command(found["cmd"], found["framework"], ["test/a.test.js"]),
                ["npm", "test", "--", "test/a.test.js"],
            )

    def test_node_test_with_a_folder_or_another_script_does_not(self):
        for script in ("node --test test/", "node --test && eslint .", "mocha"):
            found = self.detect(script)
            self.assertEqual(found["framework"], "npm test", script)
            self.assertIsNone(test_runner.scoped_command(found["cmd"], found["framework"], ["test/a.test.js"]))


class TestS21Main(unittest.TestCase):
    def run_with(self, project, argv, framework_info, done=PASSING):
        with mock.patch.object(test_runner, "detect_test_framework", return_value=framework_info), \
                mock.patch.object(test_runner, "run_external", return_value=done) as runner:
            code, out = run_main(test_runner, [str(project.root), *argv])
        return code, out, runner

    def test_paths_restrict_the_command(self):
        with TempProject() as project:
            project.write("tests/test_a.py", "")
            code, out, runner = self.run_with(
                project, ["--paths", "tests/test_a.py"],
                info(["py", "-m", "pytest", "-v"], "pytest"),
            )
            self.assertEqual(code, 0)
            self.assertEqual(runner.call_args.args[0], ["py", "-m", "pytest", "-v", "tests/test_a.py"])
            self.assertIn("Scope: paths (1)", out)
            data = json_tail(out)
            self.assertEqual(data["scope"], "paths")
            self.assertEqual(data["paths"], ["tests/test_a.py"])
            self.assertNotIn("paths_ignored", data)

    def test_runner_without_file_support_runs_the_full_suite_and_says_so(self):
        with TempProject() as project:
            project.write("tests/a.test.js", "")
            code, out, runner = self.run_with(project, ["--paths", "tests/a.test.js"], info(["npm", "test"], "npm test"))
            self.assertEqual(code, 0)
            self.assertEqual(runner.call_args.args[0], ["npm", "test"])
            self.assertIn("Scope: full suite (npm test cannot run selected test files)", out)
            data = json_tail(out)
            self.assertEqual(data["scope"], "full suite")
            self.assertEqual(data["paths_ignored"], "npm test cannot run selected test files")

    def test_without_paths_the_scope_is_the_full_suite(self):
        with TempProject() as project:
            code, out, runner = self.run_with(project, [], info(["py", "-m", "pytest", "-v"], "pytest"))
            self.assertEqual(runner.call_args.args[0], ["py", "-m", "pytest", "-v"])
            self.assertEqual(json_tail(out)["scope"], "full suite")

    def test_missing_or_outside_paths_are_a_usage_error(self):
        with TempProject() as project:
            code, out, runner = self.run_with(project, ["--paths", "tests/missing.py"], info(["py"], "pytest"))
            self.assertEqual(code, 2)
            self.assertIn("tests/missing.py (not found)", out)
            runner.assert_not_called()
            code, out, runner = self.run_with(project, ["--paths", "../elsewhere.py"], info(["py"], "pytest"))
            self.assertEqual(code, 2)
            self.assertIn("outside the project", out)


if __name__ == "__main__":
    unittest.main()
