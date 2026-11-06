"""S10: globs must not enter node_modules, exclusions are by path segment
(not substring), SKIP_DIRS is really applied, and the page title is detected
only from a <title> element.

Bugs: schema_validator/api_validator/seo_checker globs walked node_modules;
'build' excluded app-builder/*, 'api' excluded capital.tsx; bundle_analyzer
defined SKIP_DIRS and never used it; any title= attribute counted as a title.
"""
from __future__ import annotations

import unittest

from audit_helpers import TempProject, load_audit, run_main

schema_validator = load_audit("schema_validator")
api_validator = load_audit("api_validator")
seo_checker = load_audit("seo_checker")
bundle_analyzer = load_audit("bundle_analyzer")
geo_checker = load_audit("geo_checker")
dependency_analyzer = load_audit("dependency_analyzer")


def seed_node_modules(project) -> None:
    project.write("node_modules/some-pkg/prisma/schema.prisma", "model leaked {\n  name String\n}\n")
    project.write("node_modules/some-pkg/api.ts", "export const x = 1;\n")
    project.write("node_modules/some-pkg/pages/index.html", "<html><head></head><body><h1>a</h1><h1>b</h1></body></html>\n")
    project.write("node_modules/some-pkg/package.json", '{"dependencies": {"x": "*"}}')
    project.write("dist/node_modules/vendor.js", "console.log('vendor');\n")


class TestS10PathExclusions(unittest.TestCase):
    def test_schema_validator_skips_node_modules(self):
        with TempProject("S10") as project:
            seed_node_modules(project)
            found = [path.relative_to(project.root).as_posix() for _, path in schema_validator.find_schema_files(project.root)]
        self.assertEqual(found, ["prisma/schema.prisma"])

    def test_api_validator_excludes_by_segment_not_substring(self):
        with TempProject("S10") as project:
            seed_node_modules(project)
            found = [path.relative_to(project.root).as_posix() for path in api_validator.find_api_files(project.root)]
        self.assertIn("app-builder/routes/users.ts", found)  # "build" substring no longer drops it
        self.assertNotIn("src/capital.ts", found)  # "api" inside "capital" is not an API file
        self.assertFalse(any(item.startswith("node_modules/") for item in found), found)

    def test_seo_checker_pages_and_title(self):
        with TempProject("S10") as project:
            seed_node_modules(project)
            pages = [path.relative_to(project.root).as_posix() for path in seo_checker.find_pages(project.root)]
            document = seo_checker.check_page(project.root / "pages" / "_document.tsx", project.root)
        self.assertIn("pages/capital.tsx", pages)  # "api" substring no longer drops it
        self.assertIn("pages/_document.tsx", pages)
        self.assertFalse(any(item.startswith("node_modules/") for item in pages), pages)
        # Only a title= attribute exists: that is not a page title.
        self.assertIn("Missing <title> tag", document["issues"])
        fixed = seo_checker.check_content(
            '<Head><title>Home</title><meta name="description" content="d"/><meta property="og:title"/></Head>'
        )
        self.assertEqual(fixed, [])

    def test_seo_skip_words_are_whole_words(self):
        self.assertTrue(seo_checker.is_page_file(seo_checker.Path("pages/capital.tsx")))
        self.assertTrue(seo_checker.is_page_file(seo_checker.Path("pages/prototype.tsx")))
        self.assertFalse(seo_checker.is_page_file(seo_checker.Path("pages/api.tsx")))
        self.assertFalse(seo_checker.is_page_file(seo_checker.Path("pages/useHook.tsx")))

    def test_bundle_analyzer_applies_skip_dirs(self):
        with TempProject("S10") as project:
            seed_node_modules(project)
            report = bundle_analyzer.analyze(project.root, 250, 750, 2048)
        files = [asset["file"] for asset in report["largest_assets"]]
        self.assertEqual(files, ["dist/app.js"])

    def test_project_inside_a_build_directory_is_still_scanned(self):
        # Exclusions apply to segments relative to the project, never to its own location.
        with TempProject(subdir="build/test/site") as project:
            project.write("app/page.tsx", "export default function Page() { return <main><h1>T</h1></main> }\n")
            project.write("pages/home.tsx", "export default function Home() { return null }\n")
            project.write("package.json", '{"dependencies": {"react": "18.3.1"}}')
            project.write("package-lock.json", "{}")
            geo_pages = geo_checker.find_web_pages(project.root)
            seo_pages = seo_checker.find_pages(project.root)
            code, out = run_main(dependency_analyzer, [str(project.root)])
        self.assertEqual(len(geo_pages), 2)
        self.assertEqual(len(seo_pages), 2)
        self.assertEqual(code, 0, out)

    def test_dependency_analyzer_ignores_node_modules_manifests(self):
        with TempProject() as project:
            seed_node_modules(project)
            report = dependency_analyzer.analyze(project.root)
        self.assertEqual(report["manifest_count"], 0)
        self.assertEqual(report["findings"], [])


if __name__ == "__main__":
    unittest.main()
