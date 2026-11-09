"""A SKIPPED result is never reported as PASS, also when it is aggregated.

Bugs: schema_validator.py exited 0 for Drizzle-only projects although it
validates no Drizzle rule; checklist.py and verify_all.py exited 0 when every
check was skipped, so "nothing verified" looked like a passing suite.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from audit_helpers import TempProject, load_audit, run_main

schema_validator = load_audit("schema_validator")
validation_runner = load_audit("validation_runner")

DRIZZLE = 'import { pgTable, serial } from "drizzle-orm/pg-core";\nexport const users = pgTable("users", { id: serial("id") });\n'
PRISMA = "model User {\n  id        Int      @id\n  createdAt DateTime @default(now())\n}\n"

FAKE_SCRIPTS = {
    "pass.py": "import sys\nprint('ok')\nsys.exit(0)\n",
    "fail.py": "import sys\nprint('bad')\nsys.exit(1)\n",
    "skip.py": "import sys\nprint('SKIPPED (fake tool missing)')\nsys.exit(3)\n",
}


def json_tail(out: str) -> dict:
    return json.loads(out[out.index("\n{") + 1:])


class TestSchemaValidatorDrizzle(unittest.TestCase):
    def test_drizzle_only_is_skipped(self):
        with TempProject() as project:
            project.write("src/db/schema/users.schema.ts", DRIZZLE)
            code, out = run_main(schema_validator, [str(project.root)])
        self.assertEqual(code, 3, out)
        self.assertIn("SKIPPED (Drizzle schemas found, not validated)", out)
        self.assertIn("Not validated: src/db/schema/users.schema.ts", out)
        self.assertNotIn("No schema issues found", out)

    def test_drizzle_next_to_prisma_is_listed_not_validated(self):
        with TempProject() as project:
            project.write("prisma/schema.prisma", PRISMA)
            project.write("src/db/schema/users.schema.ts", DRIZZLE)
            code, out = run_main(schema_validator, [str(project.root)])
        self.assertEqual(code, 0, out)
        self.assertNotIn("SKIPPED", out)
        self.assertIn("Not validated: src/db/schema/users.schema.ts", out)
        payload = json_tail(out)
        self.assertEqual(payload["schemas_checked"], 1)
        self.assertEqual(payload["files"], ["prisma/schema.prisma"])
        self.assertEqual(payload["not_validated"], ["src/db/schema/users.schema.ts"])


class TestOrchestratorExitCodes(unittest.TestCase):
    def result(self, status: str, required: bool = False):
        return validation_runner.CheckResult("c", "cat", status, required, reason="r")

    def test_exit_code_rules(self):
        code = validation_runner.suite_exit_code
        self.assertEqual(code([self.result("skipped"), self.result("skipped", True)]), 3)
        self.assertEqual(code([]), 3)
        self.assertEqual(code([self.result("passed"), self.result("skipped", True)]), 0)
        self.assertEqual(code([self.result("skipped"), self.result("failed")]), 1)
        self.assertEqual(code([self.result("passed"), self.result("error")]), 1)

    def run_fake_suite(self, scripts, extra=()):
        specs = tuple(
            validation_runner.CheckSpec(name, script, "Fake", required=(name == "Required"))
            for name, script in scripts
        )
        with tempfile.TemporaryDirectory(prefix="redevkit-fake-audits-") as audits, TempProject() as project:
            for name, body in FAKE_SCRIPTS.items():
                (Path(audits) / name).write_text(body, encoding="utf-8")
            report = project.root / "report.json"
            with mock.patch.object(validation_runner, "AUDITS_DIR", Path(audits)):
                runner = type("Runner", (), {
                    "main": staticmethod(lambda argv: validation_runner.run_suite("T", "S", "d", specs, argv)),
                })
                code, out = run_main(runner, [str(project.root), "--report", str(report), *extra])
            payload = json.loads(report.read_text(encoding="utf-8"))
        return code, out, payload

    def test_all_skipped_suite_is_skipped_not_passed(self):
        code, out, payload = self.run_fake_suite([("Required", "skip.py"), ("Missing", "absent.py")])
        self.assertEqual(code, 3, out)
        self.assertIn("SKIPPED (all 2 check(s) skipped; nothing was verified)", out)
        self.assertIn("[SKIPPED] (required) Fake / Required - SKIPPED (fake tool missing)", out)
        self.assertIn("Required check(s) SKIPPED (not verified): Required", out)
        self.assertNotIn("[PASS]", out)
        self.assertEqual((payload["status"], payload["exit_code"], payload["success"]), ("skipped", 3, False))

    def test_one_pass_with_skipped_required_is_pass_and_visible(self):
        code, out, payload = self.run_fake_suite([("Ok", "pass.py"), ("Required", "skip.py")])
        self.assertEqual(code, 0, out)
        self.assertIn("Required check(s) SKIPPED (not verified): Required", out)
        self.assertEqual((payload["status"], payload["success"]), ("passed", True))

    def test_any_failure_is_fail(self):
        code, out, payload = self.run_fake_suite([("Required", "skip.py"), ("Bad", "fail.py")])
        self.assertEqual(code, 1, out)
        self.assertEqual((payload["status"], payload["exit_code"]), ("failed", 1))

    def test_url_checks_without_url_are_skipped(self):
        specs = (validation_runner.CheckSpec("Lighthouse", "lighthouse_audit.py", "Runtime", target="url", required=True),)
        with TempProject() as project:
            runner = type("Runner", (), {
                "main": staticmethod(lambda argv: validation_runner.run_suite("T", "S", "d", specs, argv)),
            })
            code, out = run_main(runner, [str(project.root)])
        self.assertEqual(code, 3, out)
        self.assertIn("[SKIPPED] (required) Runtime / Lighthouse - SKIPPED (URL not provided)", out)


if __name__ == "__main__":
    unittest.main()
