"""S18: an exclusion pattern that ``re`` cannot compile must not crash the audits.

Bug: git accepts ``*.[a-Z]`` in a ``.gitignore``; the translated regex has a reversed
character range, ``re.compile`` raised ``re.error`` and EVERY audit that scans files
ended with a traceback (exit 1), reported by the orchestrators as six failed checks.
The same happened with ``--exclude "[z-a]"``.
"""
from __future__ import annotations

import unittest

from audit_helpers import TempProject, load_audit, run_main

audit_common = load_audit("audit_common")
security_scan = load_audit("security_scan")
type_coverage = load_audit("type_coverage")
accessibility = load_audit("accessibility_checker")

BAD_GITIGNORE = "logs/\n*.[a-Z]\n[z-a]\nsecret.js\n"


class TestS18IgnorePatternErrors(unittest.TestCase):
    def test_uncompilable_pattern_is_ignored(self):
        self.assertIsNone(audit_common.compile_pattern("*.[a-Z]"))
        self.assertIsNone(audit_common.compile_pattern("[z-a]"))
        self.assertEqual(len(audit_common.compile_patterns(BAD_GITIGNORE.splitlines())), 2)
        self.assertIsNotNone(audit_common.compile_pattern("[Bb]in/"))  # valid classes still work

    def test_the_other_rules_of_the_file_still_apply(self):
        with TempProject() as project:
            project.write(".gitignore", BAD_GITIGNORE)
            project.write("logs/app.js", "x")
            project.write("secret.js", "x")
            project.write("src/app.js", "x")
            paths = audit_common.PathFilter(project.root)
            walked = sorted(paths.relative(path) for path in paths.walk())
        self.assertEqual(walked, [".gitignore", "src/app.js"])

    def test_audits_run_instead_of_crashing(self):
        with TempProject() as project:
            project.write(".gitignore", BAD_GITIGNORE)
            project.write("src/app.ts", "export const a: number = 1;\n")
            project.write("index.html", '<html lang="en"><head><title>t</title></head><body><h1>x</h1></body></html>\n')
            for module, argv in (
                (security_scan, ["--output", "summary"]),
                (type_coverage, []),
                (accessibility, []),
                (security_scan, ["--output", "summary", "--exclude", "[z-a]"]),
            ):
                with self.subTest(module.__name__, argv=argv):
                    code, out = run_main(module, [str(project.root), *argv])
                    self.assertIn(code, (0, 1, 3), out)
                    self.assertNotIn("Traceback", out)
                    self.assertTrue(out.strip())


if __name__ == "__main__":
    unittest.main()
