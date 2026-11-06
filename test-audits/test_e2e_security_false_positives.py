"""Found by the E2E run (scenario B): security_scan.py flagged a zero-dependency Node API.

- "Missing lock file" (high) for a package.json that declares no dependencies.
- "No obvious security-header configuration" for any project with a package.json, including
  CLIs, libraries and plain JSON APIs on node:http.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from audit_helpers import load_audit

security_scan = load_audit("security_scan")


def project(files: dict) -> tempfile.TemporaryDirectory:
    tmp = tempfile.TemporaryDirectory()
    for rel, text in files.items():
        path = Path(tmp.name) / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return tmp


class TestSecurityFalsePositives(unittest.TestCase):
    def deps(self, root):
        with mock.patch.object(security_scan.shutil, "which", return_value=None):
            return security_scan.scan_dependencies(root)

    def test_no_lock_file_needed_without_dependencies(self):
        with project({"package.json": json.dumps({"name": "x", "scripts": {"test": "node --test"}})}) as root:
            result = self.deps(root)
        self.assertFalse(any(f.get("type") == "Missing lock file" for f in result["findings"]))
        self.assertEqual(result["skipped"], [], "npm audit is not applicable, not skipped")
        self.assertTrue(str(result["npm_audit"]).startswith("not_applicable"))

    def test_lock_file_still_required_with_dependencies(self):
        with project({"package.json": json.dumps({"name": "x", "dependencies": {"left-pad": "1.0.0"}})}) as root:
            result = self.deps(root)
        self.assertTrue(any(f.get("type") == "Missing lock file" for f in result["findings"]))

    def test_plain_node_api_is_not_a_web_ui_project(self):
        with project({"package.json": json.dumps({"name": "api"}), "src/server.js": "require('node:http')\n"}) as root:
            result = security_scan.scan_configuration(root)
        self.assertEqual(result["checks"]["security_headers_config"], "not_applicable")

    def test_web_framework_still_requires_headers(self):
        with project({"package.json": json.dumps({"dependencies": {"express": "^5"}}), "package-lock.json": "{}"}) as root:
            result = security_scan.scan_configuration(root)
        self.assertIs(result["checks"]["security_headers_config"], False)
        with project({"index.html": "<!doctype html>"}) as root:
            result = security_scan.scan_configuration(root)
        self.assertIs(result["checks"]["security_headers_config"], False)


if __name__ == "__main__":
    unittest.main()
