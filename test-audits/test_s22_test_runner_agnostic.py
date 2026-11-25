"""S22: test_runner.py is agnostic of the test suite.

Found in a PHP project: the runner only knew Node and Python, so PHPUnit ended as
``SKIPPED (no test framework detected)`` with ``Type: node`` (the front end's package.json
without a test script). Now:

* ``--cmd COMMAND`` runs the project's declared test command (``tech.md`` > Test), any
  suite, with the same time limit, log and verdict; ``{paths}`` marks where test files go.
* Detection, used when no command is declared, also covers PHP (Pest, PHPUnit, composer
  test), Go, Rust, .NET, Ruby and Maven, and a stack without tests lets the next one try.
* The counts of PHPUnit, RSpec, minitest, cargo, Maven Surefire and dotnet are parsed.
"""
from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

from audit_helpers import TempProject, load_audit, run_main

test_runner = load_audit("test_runner")

FAKE_RUNNER = """import os, sys
print("args:" + "|".join(sys.argv[1:]))
print("env:" + os.environ.get("APP_ENV", "-"))
print(os.environ.get("FAKE_OUTPUT", "OK (3 tests, 4 assertions)"))
sys.exit(int(os.environ.get("FAKE_EXIT", "0")))
"""


def json_tail(out: str) -> dict:
    return json.loads(out[out.rindex("\n{") + 1:])


def quoted_python() -> str:
    return f'"{sys.executable}"'


def fake_which(*available: str):
    return lambda name: f"/bin/{name}" if name in available else None


def counts(output: str):
    result = {"tests_run": 0, "tests_passed": 0, "tests_failed": 0}
    parsed = test_runner._parse_counts(output, result)
    return parsed, (result["tests_run"], result["tests_passed"], result["tests_failed"])


class TestS22DeclaredCommand(unittest.TestCase):
    def run_declared(self, command, *extra, env=None):
        with TempProject() as project:
            project.write("fake_runner.py", FAKE_RUNNER)
            project.write("tests/a_test.php", "<?php\n")
            project.write("tests/b_test.php", "<?php\n")
            with mock.patch.dict(os.environ, env or {}):
                code, out = run_main(test_runner, [str(project.root), "--cmd", command, *extra])
        return code, out

    def test_any_command_runs_with_the_shared_verdict(self):
        code, out = self.run_declared(f"{quoted_python()} fake_runner.py")
        self.assertEqual(code, 0, out)
        data = json_tail(out)
        self.assertEqual((data["command_source"], data["type"], data["status"]), ("declared", "declared", "passed"))
        self.assertEqual((data["tests_run"], data["tests_passed"]), (3, 3))
        self.assertIn("Command source: declared (--cmd)", out)

    def test_paths_token_takes_the_files(self):
        code, out = self.run_declared(f"{quoted_python()} fake_runner.py {{paths}} --stop",
                                      "--paths", "tests/a_test.php", "tests/b_test.php")
        self.assertEqual(code, 0, out)
        self.assertIn("args:tests/a_test.php|tests/b_test.php|--stop", out)
        self.assertEqual(json_tail(out)["scope"], "paths")
        self.assertIn("Scope: paths (2)", out)

    def test_paths_token_is_removed_without_paths(self):
        code, out = self.run_declared(f"{quoted_python()} fake_runner.py {{paths}}")
        self.assertIn("args:\n", out)
        self.assertEqual(json_tail(out)["scope"], "full suite")

    def test_without_paths_token_the_whole_suite_runs(self):
        code, out = self.run_declared(f"{quoted_python()} fake_runner.py", "--paths", "tests/a_test.php")
        self.assertEqual(code, 0, out)
        data = json_tail(out)
        self.assertEqual(data["scope"], "full suite")
        self.assertEqual(data["paths_ignored"], test_runner.NO_PATHS_TOKEN)
        self.assertIn("args:\n", out)

    def test_leading_assignments_become_environment(self):
        code, out = self.run_declared(f"APP_ENV=testing {quoted_python()} fake_runner.py")
        self.assertEqual(code, 0, out)
        self.assertIn("env:testing", out)

    def test_failures_and_no_tests_keep_their_verdicts(self):
        code, out = self.run_declared(f"{quoted_python()} fake_runner.py",
                                      env={"FAKE_OUTPUT": "Tests: 3, Assertions: 3, Failures: 1.", "FAKE_EXIT": "1"})
        self.assertEqual(code, 1, out)
        self.assertEqual((json_tail(out)["tests_passed"], json_tail(out)["tests_failed"]), (2, 1))
        code, out = self.run_declared(f"{quoted_python()} fake_runner.py", env={"FAKE_OUTPUT": "No tests executed!"})
        self.assertEqual((code, json_tail(out)["reason"]), (3, "no tests found"))

    def test_missing_executable_is_skipped(self):
        code, out = self.run_declared("definitely-not-a-test-runner-xyz {paths}")
        self.assertEqual(code, 3, out)
        self.assertEqual(json_tail(out)["reason"], "command not found: definitely-not-a-test-runner-xyz")

    def test_shell_operators_and_empty_commands_are_usage_errors(self):
        for command in ("composer install && phpunit", "phpunit | tee out.log", "phpunit > out.log",
                        "phpunit 2>err.log", "a; b", "", "APP_ENV=x", 'phpunit "unclosed'):
            with self.subTest(command=command):
                code, out = self.run_declared(command)
                self.assertEqual(code, 2, out)
                self.assertIn("invalid --cmd", out)
                self.assertNotIn("[TEST RUNNER]", out)  # refused before the run starts

    def test_parse_keeps_quotes_and_windows_paths(self):
        env, argv = test_runner.parse_command('CI=1 "C:\\Program Files\\php\\php.exe" vendor\\bin\\phpunit --filter "a b" {paths}')
        self.assertEqual(env, {"CI": "1"})
        if os.name == "nt":
            self.assertEqual(argv, ["C:\\Program Files\\php\\php.exe", "vendor\\bin\\phpunit", "--filter", "a b", "{paths}"])
        self.assertEqual(argv[-3:], ["--filter", "a b", "{paths}"])

    def test_declared_python_runner_keeps_exit_5_rule(self):
        self.assertEqual(test_runner._framework_of(["py", "-m", "pytest", "-q"]), "pytest")
        self.assertEqual(test_runner._framework_of(["php", "vendor/bin/phpunit"]), "phpunit")
        self.assertIsNone(test_runner._framework_of(["make", "test"]))

    def test_coverage_with_a_declared_command_is_skipped_but_the_suite_runs(self):
        code, out = self.run_declared(f"{quoted_python()} fake_runner.py", "--coverage")
        self.assertEqual(code, 0, out)
        self.assertIn(test_runner.COVERAGE_DECLARED, json_tail(out)["coverage"])


class TestS22PhpDetection(unittest.TestCase):
    def detect(self, project, *tools):
        with mock.patch.object(test_runner, "which", side_effect=fake_which(*tools)):
            return test_runner.detect_test_framework(project.root)

    def test_laravel_like_project_runs_phpunit_not_node(self):
        with TempProject() as project:
            project.write("package.json", json.dumps({"private": True, "scripts": {"dev": "vite", "build": "vite build"}}))
            project.write("composer.json", json.dumps({"require-dev": {"phpunit/phpunit": "^11"}}))
            project.write("vendor/bin/phpunit", "<?php\n")
            info = self.detect(project, "php", "npm")
        self.assertEqual((info["type"], info["framework"], info["cmd"]), ("php", "phpunit", ["/bin/php", "vendor/bin/phpunit"]))

    def test_pest_wins_over_phpunit_and_bin_dir_is_honoured(self):
        with TempProject() as project:
            project.write("composer.json", json.dumps({"require-dev": {"pestphp/pest": "^3"}, "config": {"bin-dir": "bin"}}))
            project.write("bin/pest", "<?php\n")
            project.write("bin/phpunit", "<?php\n")
            info = self.detect(project, "php")
        self.assertEqual(info["cmd"], ["/bin/php", "bin/pest"])

    def test_declared_but_not_installed_is_skipped(self):
        with TempProject() as project:
            project.write("composer.json", json.dumps({"require-dev": {"phpunit/phpunit": "^11"}}))
            info = self.detect(project, "php")
        self.assertIsNone(info["cmd"])
        self.assertEqual(info["skip_reason"], "phpunit is not installed in vendor/bin (run composer install first)")

    def test_php_missing_is_skipped(self):
        with TempProject() as project:
            project.write("composer.json", "{}")
            project.write("vendor/bin/phpunit", "<?php\n")
            info = self.detect(project)
        self.assertEqual(info["skip_reason"], "php not found on PATH")

    def test_composer_test_script(self):
        with TempProject() as project:
            project.write("composer.json", json.dumps({"scripts": {"test": "@php artisan test"}}))
            info = self.detect(project, "composer")
        self.assertEqual((info["framework"], info["cmd"]), ("composer test", ["/bin/composer", "test"]))

    def test_phpunit_takes_several_files_from_version_10(self):
        paths = ["tests/AT.php", "tests/BT.php"]
        with TempProject() as project:
            project.write("vendor/composer/installed.json",
                          json.dumps({"packages": [{"name": "phpunit/phpunit", "version": "9.6.20"}]}))
            self.assertIsNone(test_runner.scoped_command(["php", "vendor/bin/phpunit"], "phpunit", paths, project.root))
            self.assertEqual(test_runner.scoped_command(["php", "vendor/bin/phpunit"], "phpunit", paths[:1], project.root),
                             ["php", "vendor/bin/phpunit", "tests/AT.php"])
            project.write("vendor/composer/installed.json",
                          json.dumps({"packages": [{"name": "phpunit/phpunit", "version": "11.5.58"}]}))
            self.assertEqual(test_runner.scoped_command(["php", "vendor/bin/phpunit"], "phpunit", paths, project.root),
                             ["php", "vendor/bin/phpunit", *paths])
        self.assertEqual(test_runner.scoped_command(["php", "vendor/bin/pest"], "pest", paths), ["php", "vendor/bin/pest", *paths])
        self.assertIsNone(test_runner.scoped_command(["composer", "test"], "composer test", paths))


class TestS22OtherStacks(unittest.TestCase):
    def detect(self, files, *tools):
        with TempProject() as project, mock.patch.object(test_runner, "which", side_effect=fake_which(*tools)):
            for name, content in files.items():
                project.write(name, content)
            return test_runner.detect_test_framework(project.root)

    def test_each_stack_gets_its_command(self):
        cases = [
            ({"go.mod": "module x\n"}, ("go",), "go", ["/bin/go", "test", "./..."]),
            ({"Cargo.toml": "[package]\n"}, ("cargo",), "rust", ["/bin/cargo", "test"]),
            ({"App.sln": ""}, ("dotnet",), "dotnet", ["/bin/dotnet", "test", "App.sln"]),
            ({"App.csproj": "<Project/>"}, ("dotnet",), "dotnet", ["/bin/dotnet", "test"]),
            ({"Gemfile": "gem 'rspec'\n"}, ("bundle",), "ruby", ["/bin/bundle", "exec", "rspec"]),
            ({"Gemfile": "gem 'rails'\n", "bin/rails": "", "test/x_test.rb": ""}, ("ruby",), "ruby",
             ["/bin/ruby", "bin/rails", "test"]),
            ({"pom.xml": "<project/>"}, ("mvn",), "java", ["/bin/mvn", "-B", "test"]),
        ]
        for files, tools, kind, cmd in cases:
            with self.subTest(files=list(files)):
                info = self.detect(files, *tools)
                self.assertEqual((info["type"], info["cmd"]), (kind, cmd))
                self.assertIsNone(info["skip_reason"])

    def test_missing_tool_and_ambiguous_projects_are_skipped(self):
        self.assertEqual(self.detect({"go.mod": ""})["skip_reason"], "go not found on PATH")
        self.assertIn("several .NET", self.detect({"A.sln": "", "B.sln": ""}, "dotnet")["skip_reason"])
        self.assertIn("Gradle prints no test result", self.detect({"build.gradle.kts": ""})["skip_reason"])

    def test_python_helper_files_do_not_hide_another_stack(self):
        info = self.detect({"go.mod": "", "requirements.txt": "mkdocs\n"}, "go")
        self.assertEqual(info["type"], "go")

    def test_python_tests_claim_the_project_first(self):
        with mock.patch.object(test_runner, "python_module_available", return_value=True):
            info = self.detect({"Cargo.toml": "", "pyproject.toml": "[tool.pytest.ini_options]\n"}, "cargo")
        self.assertEqual((info["type"], info["framework"]), ("python", "pytest"))

    def test_node_project_with_tests_is_unchanged(self):
        info = self.detect({"package.json": json.dumps({"scripts": {"test": "mocha"}}), "composer.json": "{}"}, "npm")
        self.assertEqual((info["type"], info["cmd"]), ("node", ["/bin/npm", "test"]))

    def test_go_scope_runs_the_packages_of_the_files(self):
        cmd = test_runner.scoped_command(["go", "test", "./..."], "go test", ["pkg/a/a_test.go", "pkg/a/b_test.go", "main_test.go"])
        self.assertEqual(cmd, ["go", "test", ".", "./pkg/a"])
        self.assertIsNone(test_runner.scoped_command(["cargo", "test"], "cargo test", ["tests/a.rs"]))


class TestS22Counts(unittest.TestCase):
    def test_formats(self):
        cases = {
            "PHPUnit ok": ("Time: 00:00.005\n\nOK (3 tests, 3 assertions)\n", (3, 3, 0)),
            "PHPUnit failures": ("FAILURES!\nTests: 5, Assertions: 9, Failures: 1, Errors: 1, Skipped: 1.\n", (5, 2, 2)),
            "PHPUnit issues": ("OK, but there were issues!\nTests: 4, Assertions: 4, Deprecations: 1.\n", (4, 4, 0)),
            "Pest": ("  Tests:    1 failed, 2 passed (5 assertions)\n  Duration: 0.10s\n", (3, 2, 1)),
            "RSpec": ("Finished in 0.1 seconds\n7 examples, 1 failure, 2 pending\n", (7, 4, 1)),
            "minitest": ("10 runs, 20 assertions, 1 failures, 1 errors, 2 skips\n", (10, 6, 2)),
            "cargo": ("test result: ok. 3 passed; 0 failed; 0 ignored\n\ntest result: ok. 2 passed; 1 failed; 0 ignored\n"
                      "   Doc-tests x\n\nrunning 0 tests\n\ntest result: ok. 0 passed; 0 failed; 0 ignored\n", (6, 5, 1)),
            "Maven": ("[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0, Time elapsed: 0.1 s -- in a.ATest\n"
                      "[INFO] Results:\n[INFO] Tests run: 5, Failures: 1, Errors: 0, Skipped: 1\n"
                      "[INFO] Tests run: 3, Failures: 0, Errors: 1, Skipped: 0\n", (8, 5, 2)),
            "dotnet": ("Passed!  - Failed:     0, Passed:     2, Skipped:     0, Total:     2, Duration: 3 ms - a.dll\n"
                       "Failed!  - Failed:     1, Passed:     3, Skipped:     1, Total:     5, Duration: 3 ms - b.dll\n", (7, 5, 1)),
            "dotnet 10 (en dash)": ("Passed!  – Failed:     0, Passed:     1, Skipped:     0, Total:     1, Duration: 4 ms\n",
                                    (1, 1, 0)),
            "dotnet summary": ("Test summary: total: 4, failed: 1, succeeded: 3, skipped: 0, duration: 1.0s\n", (4, 3, 1)),
        }
        for name, (output, expected) in cases.items():
            with self.subTest(name):
                parsed, got = counts(output)
                self.assertTrue(parsed)
                self.assertEqual(got, expected)

    def test_unittest_ok_line_is_not_phpunit(self):
        self.assertEqual(counts("Ran 2 tests in 0.01s\n\nOK (skipped=1)\n")[1], (2, 1, 0))

    def test_dotnet_output_is_forced_to_english_unless_declared_otherwise(self):
        audit_common = load_audit("audit_common")
        done = audit_common.CommandResult(0, "Passed!  - Failed: 0, Passed: 1, Skipped: 0, Total: 1\n", "", False)
        with TempProject() as project, mock.patch.object(test_runner, "run_external", return_value=done) as run:
            test_runner.run_tests(["dotnet", "test"], project.root)
            self.assertEqual(run.call_args.kwargs["env"]["DOTNET_CLI_UI_LANGUAGE"], "en")
            test_runner.run_tests(["dotnet", "test"], project.root, env={"DOTNET_CLI_UI_LANGUAGE": "pt-BR"})
            self.assertEqual(run.call_args.kwargs["env"]["DOTNET_CLI_UI_LANGUAGE"], "pt-BR")

    def test_maven_success_is_evidence(self):
        self.assertTrue(test_runner.has_test_evidence("[INFO] Tests run: 4, Failures: 0, Errors: 0, Skipped: 0, Time elapsed: 1 s"))


if __name__ == "__main__":
    unittest.main()
