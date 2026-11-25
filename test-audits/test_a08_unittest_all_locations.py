"""A08: unittest discovery runs every supported location, each test once.

Bugs:

* a ``test*.py`` in the project root made the runner use plain ``discover`` from the root,
  which does not see ``tests/`` without ``__init__.py``: a green root test and a red
  ``tests/test_nested.py`` gave ``Ran 1 test``, PASS, exit 0;
* with ``tests/`` and ``test/`` (neither a package) only the first was discovered: a red
  ``test/`` was ignored.
"""
from __future__ import annotations

import unittest
from unittest import mock

from audit_helpers import TempProject, load_audit, run_main

test_runner = load_audit("test_runner")

GREEN = "import unittest\nclass G(unittest.TestCase):\n    def test_green(self):\n        self.assertTrue(True)\n"
RED = "import unittest\nclass R(unittest.TestCase):\n    def test_red(self):\n        self.assertEqual(1, 2)\n"


def run(project):
    with mock.patch.object(test_runner, "python_module_available", return_value=False):  # force unittest
        info = test_runner.detect_test_framework(project.root)
        code, out = run_main(test_runner, [str(project.root)])
    return info, code, out


class TestA08UnittestLocations(unittest.TestCase):
    def test_root_test_does_not_hide_a_failing_tests_folder(self):
        with TempProject() as project:
            project.write("requirements.txt", "")
            project.write("test_root.py", GREEN)
            project.write("tests/test_nested.py", RED)
            info, code, out = run(project)
        self.assertEqual(info["cmd"][-2:], [".", "tests"])
        self.assertEqual(code, 1, out)
        self.assertIn("Tests: 2 total, 1 passed, 1 failed", out)
        self.assertIn(f"-c {test_runner.UNITTEST_MULTI_LABEL} . tests", out)  # the Running line

    def test_both_conventional_folders_run(self):
        with TempProject() as project:
            project.write("requirements.txt", "")
            project.write("tests/test_a.py", GREEN)
            project.write("test/test_b.py", RED)
            info, code, out = run(project)
        self.assertEqual(info["cmd"][-2:], ["tests", "test"])
        self.assertEqual(code, 1, out)
        self.assertIn("Tests: 2 total, 1 passed, 1 failed", out)
        self.assertIn('"status": "failed"', out)

    def test_all_green_locations_pass_with_each_test_counted_once(self):
        with TempProject() as project:
            project.write("requirements.txt", "")
            project.write("test_root.py", GREEN)
            project.write("tests/test_a.py", GREEN)
            project.write("test/test_b.py", GREEN)
            project.write("pkg/__init__.py", "")
            project.write("pkg/test_pkg.py", GREEN)  # a package below the root: found by the root start
            info, code, out = run(project)
        self.assertEqual(info["cmd"][-3:], [".", "tests", "test"])
        self.assertEqual(code, 0, out)
        self.assertIn("Tests: 4 total, 4 passed, 0 failed", out)

    def test_same_file_names_in_two_folders_each_import_their_own_module(self):
        where = (
            "import unittest\nimport helpers\nclass W(unittest.TestCase):\n"
            "    def test_where(self):\n        self.assertEqual(helpers.WHERE, {expected!r})\n"
        )
        with TempProject() as project:
            project.write("requirements.txt", "")
            project.write("tests/helpers.py", "WHERE = 'tests'\n")
            project.write("test/helpers.py", "WHERE = 'test'\n")
            project.write("tests/test_where.py", where.format(expected="tests"))
            project.write("test/test_where.py", where.format(expected="test"))
            _, code, out = run(project)
        self.assertEqual(code, 0, out)
        self.assertIn("Tests: 2 total, 2 passed, 0 failed", out)

    def test_a_package_tests_folder_is_not_discovered_twice(self):
        with TempProject() as project:
            project.write("requirements.txt", "")
            project.write("test_root.py", GREEN)
            project.write("tests/__init__.py", "")
            project.write("tests/test_pkg.py", GREEN)
            info, code, out = run(project)
        self.assertEqual(info["cmd"][-2:], ["discover", "-v"])  # the root start finds the package
        self.assertEqual(code, 0, out)
        self.assertIn("Tests: 2 total, 2 passed, 0 failed", out)

    def test_no_test_in_any_location_is_skipped(self):
        with TempProject() as project:
            project.write("requirements.txt", "")
            project.write("tests/test_a.py", "")
            project.write("test/test_b.py", "")
            _, code, out = run(project)
        self.assertEqual(code, 3, out)
        self.assertNotIn("[PASS]", out)


if __name__ == "__main__":
    unittest.main()
