"""S5: react_performance_checker.py.

Bugs: any pair of consecutive awaits (even dependent ones) became CRITICAL
and made run() return False (blocking verify_all); the whole tree was walked
again for every large file (O(n^2)); the component regex matched
``const API_URL``.
"""
from __future__ import annotations

import unittest
from unittest import mock

from audit_helpers import TempProject, load_audit, run_main

react = load_audit("react_performance_checker")


class TestS5ReactPerformance(unittest.TestCase):
    def test_consecutive_awaits_are_only_a_warning(self):
        with TempProject("S5") as project:
            checker = react.PerformanceChecker(str(project.root))
            with mock.patch("sys.stdout"):
                passed = checker.run()
            code, _ = run_main(react, [str(project.root)])
            strict_code, _ = run_main(react, [str(project.root), "--fail-on-warnings"])
        self.assertTrue(passed)
        self.assertEqual(checker.issues, [])
        waterfalls = [w for w in checker.warnings if "await" in w["issue"]]
        self.assertEqual(len(waterfalls), 1)
        self.assertEqual(waterfalls[0]["type"], "WARNING")
        self.assertEqual(code, 0)
        self.assertEqual(strict_code, 1)

    def test_one_tree_walk_per_scan_root(self):
        big = "export default function Big() { return null }\n" + ("// filler\n" * 1200)
        with TempProject() as project:
            project.write("package.json", '{"dependencies": {"react": "18.3.1"}}')
            for index in range(4):
                project.write(f"src/Big{index}.tsx", big)
                imports = "".join(f"import Big{j} from './Big{j}';\n" for j in range(4) if j != index)
                project.write(f"src/User{index}.tsx", imports + "export const x = 1;\n")
            checker = react.PerformanceChecker(str(project.root))
            real_walk = react.os.walk
            with mock.patch.object(react.os, "walk", side_effect=real_walk) as walk, mock.patch("sys.stdout"):
                checker.run()
        self.assertEqual(len(checker.scan_roots), 1)
        self.assertEqual(checker.walk_count, 1)
        self.assertEqual(walk.call_count, 1)
        self.assertTrue(any("imported statically" in w["issue"] for w in checker.warnings))

    def test_component_regex_ignores_constants(self):
        self.assertEqual(react.find_components('export const API_URL = "x";\nconst MAX = 3;\n'), [])
        self.assertEqual(
            react.find_components("export const Card = ({ title }: CardProps) => null;\nfunction Button() {}\n"),
            ["Card", "Button"],
        )
        with TempProject("S5") as project:
            checker = react.PerformanceChecker(str(project.root))
            with mock.patch("sys.stdout"):
                checker.check_missing_memoization()
        self.assertEqual([w for w in checker.warnings if "memoized" in w["issue"]], [])

    def test_non_react_project_is_skipped(self):
        with TempProject() as project:
            project.write("server.py", "print('hi')\n")
            code, out = run_main(react, [str(project.root)])
        self.assertEqual(code, react.EXIT_SKIPPED)
        self.assertIn("SKIPPED (", out)


if __name__ == "__main__":
    unittest.main()
