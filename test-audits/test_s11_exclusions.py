"""S11: one exclusion policy for every audit that scans files.

Bugs (real PHP/CodeIgniter project with Playwright): each script had its own
SKIP_DIRS (``vendor`` missing from accessibility, SEO, GEO, UX, mobile, i18n,
type coverage), nothing read ``.gitignore``, there was no way to exclude a
folder, and minified third-party assets (``htmx.min.js``) and generated
reports (``playwright-report/``) were audited as product code.

Fix: ``audit_common.PathFilter`` = shared defaults + ``.gitignore`` (root and
nested, ``--no-gitignore`` to disable) + ``.redevkit/audit-ignore`` +
``--exclude PATTERN``, gitignore syntax, last match wins, evaluated on the
path relative to the project root. The orchestrators forward ``--exclude`` /
``--no-gitignore`` to the audits that scan files.
"""
from __future__ import annotations

import os
import subprocess
import sys
import unittest

from audit_helpers import AUDITS_DIR, TempProject, load_audit, run_main

common = load_audit("audit_common")
validation_runner = load_audit("validation_runner")
checklist = load_audit("checklist")
verify_all = load_audit("verify_all")

FILE_SCANNING_AUDITS = (
    "security_scan", "dependency_analyzer", "type_coverage", "schema_validator", "ux_audit",
    "accessibility_checker", "seo_checker", "geo_checker", "bundle_analyzer",
    "react_performance_checker", "mobile_audit", "i18n_checker", "api_validator",
)

BAD_PAGE = "<html><head></head><body><nav></nav><h1>a</h1><h1>b</h1><img src='x.png'><button></button></body></html>\n"
GOOD_PAGE = (
    '<!doctype html><html lang="en"><head><title>Home</title><meta name="description" content="d">'
    '<meta property="og:title" content="t"></head><body><main id="main"><h1>Home</h1>'
    "<h2>One</h2><h2>Two</h2><p>According to the data, 10% more.</p></main></body></html>\n"
)


def rels(project, paths):
    root = project.root.resolve()  # PathFilter.walk() yields paths under the resolved root
    return sorted(path.relative_to(root).as_posix() for path in paths)


def seed_noise(project) -> None:
    """Everything the user's report found findings in, none of it product code."""
    project.write("vendor/codeigniter4/framework/system/Views/errors/html/error_404.php", BAD_PAGE)
    project.write("vendor/acme/util.js", "el.innerHTML = html;\nconst password = 'abcdefgh12';\n")
    project.write("public/js/htmx.min.js", "var token='abcdefghijklmnopqrstuvwxyz';el.innerHTML=x;\n")
    project.write("public/css/bootstrap.min.css", ".a{color:purple}\n")
    project.write("playwright-report/index.html", BAD_PAGE)
    project.write("test-results/run/trace.html", BAD_PAGE)
    project.write("coverage/lcov-report/index.html", BAD_PAGE)


class TestPatternTranslation(unittest.TestCase):
    def match(self, pattern, rel, is_dir=False):
        rule = common.compile_pattern(pattern)
        return rule is not None and rule.matches(rel, is_dir)

    def test_gitignore_syntax(self):
        cases = [
            ("vendor/", "vendor", True, True),
            ("vendor/", "app/vendor", True, True),        # unanchored: any level
            ("vendor/", "vendor", False, False),         # dir-only pattern, file named vendor
            ("vendor/", "vendors", True, False),         # segment, never substring
            ("build", "app-builder", True, False),
            ("/build", "build", True, True),
            ("/build", "src/build", True, False),        # anchored to the root
            ("*.min.js", "public/js/htmx.min.js", False, True),
            ("*.min.js", "public/js/htmx.js", False, False),
            ("SPECs/Funil*", "SPECs/Funil-v2", True, True),
            ("specs/funil*", "SPECs/Funil-v2", True, True),  # case-insensitive
            ("SPECs/Funil*", "app/SPECs/Funil-v2", True, False),  # middle slash anchors
            ("docs/**", "docs/a/b.html", False, True),
            ("docs/**", "docs", True, False),
            ("a/**/b", "a/b", True, True),
            ("a/**/b", "a/x/y/b", True, True),
            ("**/legacy", "src/legacy", True, True),
            ("file[0-9].php", "file7.php", False, True),
            ("file[!0-9].php", "filex.php", False, True),
            ("\\#notes", "#notes", False, True),
        ]
        for pattern, rel, is_dir, expected in cases:
            with self.subTest(pattern=pattern, rel=rel):
                self.assertEqual(self.match(pattern, rel, is_dir), expected)
        self.assertIsNone(common.compile_pattern("# comment"))
        self.assertIsNone(common.compile_pattern("   "))


class TestPathFilter(unittest.TestCase):
    def test_defaults_cover_dependencies_reports_and_minified_assets(self):
        with TempProject() as project:
            seed_noise(project)
            project.write("app/Views/home.php", GOOD_PAGE)
            project.write("public/js/app.js", "console.log(1);\n")
            files = rels(project, common.PathFilter(project.root).walk())
        self.assertEqual(files, ["app/Views/home.php", "public/js/app.js"])

    def test_gitignore_root_nested_negation_and_opt_out(self):
        with TempProject() as project:
            project.write(".gitignore", "generated/\n*.log\n!keep.log\n")
            project.write("generated/page.html", BAD_PAGE)
            project.write("a.log", "x")
            project.write("keep.log", "x")
            project.write("writable/.gitignore", "*\n!.gitignore\n")
            project.write("writable/debugbar/report.html", BAD_PAGE)
            project.write("src/page.html", GOOD_PAGE)
            honoured = rels(project, common.PathFilter(project.root).walk())
            ignored = rels(project, common.PathFilter(project.root, gitignore=False).walk())
        self.assertEqual(honoured, [".gitignore", "keep.log", "src/page.html", "writable/.gitignore"])
        self.assertIn("generated/page.html", ignored)
        self.assertIn("writable/debugbar/report.html", ignored)

    def test_user_ignore_file_cli_patterns_and_reinclude(self):
        with TempProject() as project:
            project.write(".redevkit/audit-ignore", "# prototypes, not product\nSPECs/Funil*/\n!vendor/\n")
            project.write("SPECs/Funil-v1/index.html", BAD_PAGE)
            project.write("SPECs/notes.html", GOOD_PAGE)
            project.write("vendor/acme/page.html", GOOD_PAGE)
            project.write("legacy/old.html", BAD_PAGE)
            path_filter = common.PathFilter(project.root, user_patterns=["legacy/"])
            files = rels(project, path_filter.walk())
            self.assertTrue(path_filter.is_excluded(project.root / "SPECs" / "Funil-v1" / "index.html"))
            self.assertIn(".redevkit/audit-ignore", path_filter.describe())
        self.assertEqual(files, ["SPECs/notes.html", "vendor/acme/page.html"])

    def test_project_location_never_matters(self):
        for subdir in ("build/site", "vendor/pkg/site", "node_modules/x/site"):
            with self.subTest(subdir), TempProject(subdir=subdir) as project:
                project.write("index.html", GOOD_PAGE)
                files = rels(project, common.PathFilter(project.root).walk())
            self.assertEqual(files, ["index.html"])


class TestEveryScanningAuditUsesThePolicy(unittest.TestCase):
    def test_noise_only_project_is_skipped_by_every_page_audit(self):
        # Before: accessibility/SEO/GEO/UX failed on vendor/, playwright-report/ and *.min.* files.
        with TempProject() as project:
            seed_noise(project)
            for name in ("accessibility_checker", "seo_checker", "geo_checker", "ux_audit", "i18n_checker"):
                with self.subTest(name):
                    code, out = run_main(load_audit(name), [str(project.root)])
                    self.assertEqual(code, 3, out)

    def test_security_scan_ignores_vendor_and_minified_code(self):
        security_scan = load_audit("security_scan")
        with TempProject() as project:
            seed_noise(project)
            project.write("app/Controllers/Home.php", "<?php\nclass Home {}\n")
            secrets = security_scan.scan_secrets(str(project.root))
            patterns = security_scan.scan_code_patterns(str(project.root))
        self.assertEqual(secrets["findings"], [])
        self.assertEqual(patterns["findings"], [])
        self.assertEqual(patterns["scanned_files"], 1)

    def test_every_scanning_audit_accepts_the_exclusion_options(self):
        with TempProject() as project:
            for name in FILE_SCANNING_AUDITS:
                with self.subTest(name):
                    code, out = run_main(load_audit(name), [str(project.root), "--exclude=legacy/", "--exclude", "x/**", "--no-gitignore"])
                    self.assertIn(code, (0, 3), out)  # never 2 (usage error)

    def test_per_script_exclude_removes_findings(self):
        a11y = load_audit("accessibility_checker")
        with TempProject() as project:
            project.write("index.html", GOOD_PAGE)
            project.write("SPECs/Funil-v1/index.html", BAD_PAGE)
            failing, _ = run_main(a11y, [str(project.root)])
            passing, out = run_main(a11y, [str(project.root), "--exclude", "SPECs/Funil*/"])
            project.write(".redevkit/audit-ignore", "SPECs/Funil*/\n")
            from_file, _ = run_main(a11y, [str(project.root)])
        self.assertEqual(failing, 1)
        self.assertEqual(passing, 0, out)
        self.assertEqual(from_file, 0)

    def test_bundle_analyzer_measures_build_output_but_honours_user_patterns(self):
        bundle = load_audit("bundle_analyzer")
        with TempProject() as project:
            project.write(".gitignore", "dist/\n")
            project.write("dist/app.js", "x" * 10)
            project.write("dist/legacy/old.js", "x" * 10)
            report = bundle.analyze(project.root, 250, 750, 2048, bundle.bundle_filter(project.root, ["dist/legacy/"]))
        self.assertEqual([asset["file"] for asset in report["largest_assets"]], ["dist/app.js"])


class TestOrchestratorsForwardExclusions(unittest.TestCase):
    def test_flags_reach_only_file_scanning_audits(self):
        scanning = {spec.script[:-3] for suite in (checklist.SUITE, verify_all.SUITE) for spec in suite if spec.excludes}
        self.assertEqual(scanning, set(FILE_SCANNING_AUDITS))
        for suite in (checklist.SUITE, verify_all.SUITE):
            for spec in suite:
                command = validation_runner._command_for(spec, AUDITS_DIR / spec.script, AUDITS_DIR, "http://x.test",
                                                         ["SPECs/", "-odd"], True)
                with self.subTest(spec.script):
                    if spec.excludes:
                        self.assertEqual(command[-3:], ["--exclude=SPECs/", "--exclude=-odd", "--no-gitignore"])
                    else:
                        self.assertNotIn("--no-gitignore", command)
                        self.assertFalse(any(part.startswith("--exclude") for part in command))

    def test_checklist_with_exclude_end_to_end(self):
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PATH="")
        with TempProject("P4") as project:
            project.write("SPECs/Funil-v1/index.html", BAD_PAGE)
            base = [sys.executable, str(AUDITS_DIR / "checklist.py"), str(project.root), "--no-runtime"]

            def run(extra):
                return subprocess.run(
                    base + extra, capture_output=True, text=True, encoding="utf-8", errors="replace",
                    timeout=300, env=env, check=False,
                )

            failing = run([])
            passing = run(["--exclude", "SPECs/Funil*/"])
        self.assertEqual(failing.returncode, 1, failing.stdout[-2000:])
        self.assertEqual(passing.returncode, 0, passing.stdout[-3000:] + passing.stderr[-2000:])
        self.assertIn("--exclude=SPECs/Funil*/", passing.stdout)
        self.assertNotIn("Traceback", passing.stdout + passing.stderr)


if __name__ == "__main__":
    unittest.main()
