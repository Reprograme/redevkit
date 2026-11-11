"""S13: defects found by reviewing every audit script (beyond the S11/S12 report).

Each test names the bug it pins down. Runner option ``--no-tests`` (the
verify command already ran the suite in its step 1) is covered at the end.
"""
from __future__ import annotations

import json
import subprocess
import unittest
from unittest import mock

from audit_helpers import TempProject, load_audit, run_main

security_scan = load_audit("security_scan")
a11y = load_audit("accessibility_checker")
seo = load_audit("seo_checker")
ux_audit = load_audit("ux_audit")
mobile_audit = load_audit("mobile_audit")
i18n_checker = load_audit("i18n_checker")
api_validator = load_audit("api_validator")
dependency_analyzer = load_audit("dependency_analyzer")
bundle_analyzer = load_audit("bundle_analyzer")
react = load_audit("react_performance_checker")
test_runner = load_audit("test_runner")
type_coverage = load_audit("type_coverage")
validation_runner = load_audit("validation_runner")
checklist = load_audit("checklist")
verify_all = load_audit("verify_all")


def pattern_names(project, rel, text):
    project.write(rel, text)
    return [f["pattern"] for f in security_scan.scan_code_patterns(str(project.root))["findings"] if f["file"] == rel]


class TestSecurityScan(unittest.TestCase):
    def test_method_calls_named_exec_or_eval_are_not_the_builtins(self):
        # Bug: \bexec\s*\( flagged RegExp.prototype.exec, PDO->exec and model.eval() as critical.
        with TempProject() as project:
            self.assertEqual(pattern_names(project, "a.js", "const m = re.exec(s);\n"), [])
            self.assertEqual(pattern_names(project, "b.php", "<?php $pdo->exec($sql);\n"), [])
            self.assertEqual(pattern_names(project, "c.py", "model.eval()\n"), [])
            self.assertEqual(pattern_names(project, "d.py", "exec(code)\n"), ["exec() usage"])
            self.assertEqual(pattern_names(project, "e.js", "eval(code);\n"), ["eval() usage"])

    def test_php_hash_comments_are_comments(self):
        with TempProject() as project:
            self.assertEqual(pattern_names(project, "f.php", "<?php\n# never eval(input) here\n#[Attr]\n"), [])

    def test_tool_only_pyproject_needs_no_lock_file(self):
        # Bug: a pyproject.toml holding only [tool.ruff] made "Missing lock file" (high) fail the scan.
        with TempProject() as project, mock.patch.object(security_scan.shutil, "which", return_value=None):
            project.write("pyproject.toml", "[tool.ruff]\nline-length = 100\n")
            clean = security_scan.scan_dependencies(str(project.root))["findings"]
            project.write("pyproject.toml", '[project]\nname = "x"\ndependencies = ["requests>=2"]\n')
            locked = security_scan.scan_dependencies(str(project.root))["findings"]
        self.assertEqual(clean, [])
        self.assertTrue(any(f["type"] == "Missing lock file" for f in locked))


class TestAccessibility(unittest.TestCase):
    def test_onclick_check_no_longer_crashes(self):
        # Bug: the loop unpacked re.Match objects, so any <div onClick=...> raised TypeError.
        self.assertIn(
            "Non-interactive element with onClick lacks role, tabIndex, or keyboard handler",
            a11y.check_content('<div onClick={() => go()}>x</div>'),
        )
        self.assertIn(
            "Non-interactive element with onClick lacks role, tabIndex, or keyboard handler",
            a11y.check_content('<div onclick="go()">x</div>'),  # HTML attribute spelling
        )
        ok = '<div role="button" tabIndex={0} onKeyDown={k} onClick={go}>x</div>'
        self.assertEqual(a11y.check_content(ok), [])

    def test_self_labelled_inputs(self):
        for snippet in ('<input type="submit">', '<input type="reset">', '<input type="button" value="Go">',
                        '<input type="image" src="a.png" alt="Go">', '<input type="hidden">'):
            self.assertEqual(a11y.check_content(snippet), [], snippet)
        self.assertEqual(a11y.check_content('<input type="text">'),
                         ["Native input without id, name, aria-label, or aria-labelledby"])
        self.assertEqual(a11y.check_content("<Input />"), [])  # a component, not a native input

    def test_skip_link_only_when_there_are_blocks_to_skip(self):
        message = "Document body is missing a skip-to-main-content link"
        self.assertNotIn(message, a11y.check_content('<html lang="en"><body><h1>Not found</h1></body></html>'))
        self.assertIn(message, a11y.check_content('<html lang="en"><body><nav>m</nav><main></main></body></html>'))
        for link in ('<a href="#content">Skip</a>', '<a href="#conteudo">Pular para o conteudo</a>',
                     '<a class="skip-link" href="#x">x</a>'):
            page = f'<html lang="en"><body>{link}<header>h</header><main></main></body></html>'
            self.assertNotIn(message, a11y.check_content(page), link)


class TestSeo(unittest.TestCase):
    def test_header_element_is_not_a_document_head(self):
        # Bug: "<Head" in content matched <Header>, so every component with a <Header> needed a <title>.
        self.assertEqual(seo.check_content("<Header><h1>Shop</h1></Header>"), [])
        self.assertEqual(seo.check_content("<header><h1>Shop</h1></header>"), [])
        self.assertIn("Missing <title> tag", seo.check_content("<Head></Head>"))

    def test_error_pages_are_not_pages(self):
        for name in ("error_404.php", "404.tsx", "_error.tsx", "exception.html"):
            self.assertFalse(seo.is_page_file(seo.Path(f"app/Views/{name}")), name)


class TestUxAudit(unittest.TestCase):
    def audit(self, content, name="page.html"):
        with TempProject() as project:
            project.write(name, content)
            auditor = ux_audit.UXAuditor()
            auditor.audit_file(str(project.root / name))
        return auditor

    def test_purple_rule_matches_colors_not_words(self):
        # Bug: substring search failed pages on "violeta", "Magenta Ltda" or "ultraviolet" in copy.
        purple = "PURPLE DETECTED"
        self.assertFalse(any(purple in i for i in self.audit("<p>Camisa violeta da Magenta Ltda, ultraviolet</p>").issues))
        for snippet in ('<div class="bg-purple-500">', ".a { color: purple; }", ".b { background: #8B5CF6; }"):
            self.assertTrue(any(purple in i for i in self.audit(snippet).issues), snippet)

    def test_odd_numeric_values_do_not_crash(self):
        auditor = self.audit("<h1 class='text-xl'>T</h1><style>h1{line-height: .;} .s{box-shadow: 0 1px rgba(0,0,0,.)}</style>")
        self.assertEqual(auditor.files_checked, 1)


class TestMobileAudit(unittest.TestCase):
    def test_touch_target_size_is_a_whole_number(self):
        # Bug: "width: 100" was read as 10 and "maxWidth: 30%" style values counted as targets.
        rn = "import { View } from 'react-native';\nconst s = { width: 100, height: 300, minWidth: 20 };\n"
        auditor = mobile_audit.MobileAuditor()
        with TempProject() as project:
            project.write("a.tsx", rn)
            auditor.audit_file(str(project.root / "a.tsx"))
            project.write("b.tsx", "import { View } from 'react-native';\nconst s = { width: 30 };\n")
            auditor.audit_file(str(project.root / "b.tsx"))
        targets = [i for i in auditor.issues if "[Touch Target]" in i]
        self.assertEqual(targets, ["[Touch Target] b.tsx: Touch target size 30px < 44px minimum (iOS: 44pt, Android: 48dp)"])


class TestI18n(unittest.TestCase):
    def test_bom_and_invalid_utf8_locale_files(self):
        # Bug: a UTF-8 BOM made valid JSON "invalid" (high); invalid UTF-8 raised UnicodeDecodeError.
        with TempProject() as project:
            (project.root / "locales").mkdir()
            (project.root / "locales" / "en.json").write_bytes(b'\xef\xbb\xbf{"a": "A"}')
            (project.root / "locales" / "pt-BR.json").write_bytes(b'{"a": "\xe7\xe3o"}')
            report = i18n_checker.audit(project.root)
        issues = report["locale_check"]["issues"]
        self.assertEqual([i["file"] for i in issues], ["locales/pt-BR.json"])
        self.assertIn("Invalid locale JSON", issues[0]["issue"])


class TestApiValidator(unittest.TestCase):
    def test_only_named_specs_are_validated_as_specs(self):
        # Bug: any file with "openapi" in its name (openapi-client.ts) was parsed as a YAML spec.
        with TempProject() as project:
            project.write("api/openapi-client.ts", "export async function get() { try { return 1 } catch (e) { throw e } }\n")
            code, out = run_main(api_validator, [str(project.root)])
        self.assertIn("api/openapi-client.ts [code]", out)
        self.assertNotIn("No OpenAPI version found", out)


class TestDependencyAnalyzer(unittest.TestCase):
    def test_workspaces_bom_and_dependency_free_manifests(self):
        with TempProject() as project:
            project.write("package.json", json.dumps({"private": True, "workspaces": ["packages/*"]}))
            project.write("package-lock.json", "{}")
            project.write("packages/web/package.json", json.dumps({"dependencies": {"react": "18.3.1"}}))
            project.write("tools/package.json", json.dumps({"name": "scripts-only", "scripts": {"x": "node x"}}))
            (project.root / "bom").mkdir()
            (project.root / "bom" / "package.json").write_bytes(b'\xef\xbb\xbf{"name": "bom"}')
            report = dependency_analyzer.analyze(project.root)
        self.assertEqual(report["findings"], [])


class TestBundleAnalyzer(unittest.TestCase):
    def test_build_output_without_assets_is_skipped(self):
        # Bug: a Python dist/ with only a wheel PASSED with "Assets: 0".
        with TempProject() as project:
            project.write("dist/pkg-1.0-py3-none-any.whl", "x")
            code, out = run_main(bundle_analyzer, [str(project.root)])
        self.assertEqual(code, 3, out)
        self.assertIn("SKIPPED (no JavaScript or CSS asset in dist", out)


class TestReactPerformance(unittest.TestCase):
    def warnings_for(self, package):
        with TempProject() as project:
            project.write("package.json", package)
            project.write("src/Logo.tsx", "export function Logo() { return <img src='/l.png' alt='' /> }\n")
            checker = react.PerformanceChecker(str(project.root))
            with mock.patch("sys.stdout"):
                checker.check_image_optimization()
        return [w["issue"] for w in checker.warnings]

    def test_next_image_advice_only_for_next_projects(self):
        self.assertEqual(self.warnings_for('{"dependencies": {"react": "18.3.1", "vite": "5"}}'), [])
        self.assertEqual(self.warnings_for('{"dependencies": {"react": "18.3.1", "next": "14"}}'),
                         ["Using <img> instead of next/image"])


class TestTestRunner(unittest.TestCase):
    def test_npm_placeholder_script_is_not_a_test_suite(self):
        with TempProject() as project:
            project.write("package.json", json.dumps({"scripts": {"test": 'echo "Error: no test specified" && exit 1'}}))
            code, out = run_main(test_runner, [str(project.root)])
        self.assertEqual(code, 3, out)
        self.assertIn("SKIPPED (package.json test script is the npm placeholder", out)

    def test_zero_tests_with_exit_zero_is_skipped(self):
        # unittest before Python 3.12 exits 0 with "Ran 0 tests": nothing was verified.
        done = subprocess.CompletedProcess(["py"], 0, stdout="", stderr="\nRan 0 tests in 0.000s\n\nOK\n")
        with TempProject() as project, mock.patch.object(test_runner.subprocess, "run", return_value=done):
            result = test_runner.run_tests(["py", "-m", "unittest"], project.root)
        self.assertEqual((result["status"], result["error"]), ("skipped", "no tests found"))

    def test_bom_package_json_is_read(self):
        with TempProject() as project, mock.patch.object(test_runner.shutil, "which", return_value="npm.cmd"):
            (project.root / "package.json").write_bytes(b'\xef\xbb\xbf{"scripts": {"test": "vitest run"}}')
            info = test_runner.detect_test_framework(project.root)
        self.assertEqual(info["cmd"], ["npm.cmd", "test"])


class TestTypeCoverage(unittest.TestCase):
    def test_null_bytes_count_as_parse_errors(self):
        # Bug: ast.parse raises ValueError (not SyntaxError) for NUL bytes on Python < 3.12.
        with TempProject() as project:
            (project.root / "utf16.py").write_bytes("x = 1\n".encode("utf-16"))
            project.write("ok.py", "def f(a: int) -> int:\n    return a\n")
            result = type_coverage.check_python_coverage(project.root)
        self.assertEqual(result["stats"]["parse_errors"], 1)


class TestRunnerNoTests(unittest.TestCase):
    def test_test_runner_is_skipped_with_a_reason(self):
        for suite in (checklist.SUITE, verify_all.SUITE):
            self.assertEqual([spec.script for spec in suite if spec.tests], ["test_runner.py"])
        spec = next(spec for spec in checklist.SUITE if spec.tests)
        with TempProject() as project, mock.patch.object(validation_runner.subprocess, "run") as run, \
                mock.patch("sys.stdout"):
            skipped = validation_runner.run_check(spec, validation_runner.AUDITS_DIR, project.root, None, no_tests=True)
        run.assert_not_called()
        self.assertEqual(skipped.status, "skipped")
        self.assertEqual(skipped.reason, validation_runner.NO_TESTS_REASON)
        self.assertIn("--no-tests", skipped.reason)

    def test_default_still_runs_the_tests(self):
        spec = next(spec for spec in verify_all.SUITE if spec.tests)
        done = subprocess.CompletedProcess(["x"], 0, stdout="ok", stderr="")
        with TempProject() as project, mock.patch.object(validation_runner.subprocess, "run", return_value=done) as run, \
                mock.patch("sys.stdout"):
            result = validation_runner.run_check(spec, validation_runner.AUDITS_DIR, project.root, None)
        run.assert_called_once()
        self.assertEqual(result.status, "passed")

    def test_parser_flag(self):
        parser = validation_runner.build_parser("x")
        self.assertTrue(parser.parse_args(["--no-tests"]).no_tests)
        self.assertFalse(parser.parse_args([]).no_tests)


if __name__ == "__main__":
    unittest.main()
