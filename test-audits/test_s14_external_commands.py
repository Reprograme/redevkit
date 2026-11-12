"""S14: every external command runs through audit_common.run_external.

Bugs (the pipeline "hung between test and verify"):

* ``subprocess.run(timeout=...)`` killed only the first process. On Windows ``npm.cmd`` is
  a ``cmd.exe`` that starts ``node``: ``node`` survived, kept the output pipes open, and
  the audit waited on them without limit (a 5 s limit returned after 40 s; with a real
  watch mode, never). The process tree was left running.
* The command inherited the terminal as stdin and no ``CI`` variable, so
  ``"test": "vitest"`` entered watch mode when the audit was started from a console.

The helper gives the command a null stdin, ``CI=1``/``NO_COLOR=1``/``FORCE_COLOR=0``, its
own process group, kills the whole tree on timeout and never waits unbounded on a pipe.

Every process these tests start ends by itself within LIFETIME seconds.
"""
from __future__ import annotations

import os
import sys
import time
import unittest
from pathlib import Path
from unittest import mock

from audit_helpers import AUDITS_DIR, FIXTURES_DIR, TempProject, load_audit

audit_common = load_audit("audit_common")

SPAWN_TREE = str(FIXTURES_DIR / "S14" / "spawn_tree.py")
SLOW = str(FIXTURES_DIR / "S14" / "slow.py")
LIFETIME = 8  # seconds after which the fixture processes exit on their own
CONVERTED = ("test_runner", "lint_runner", "type_coverage", "security_scan", "lighthouse_audit", "validation_runner")


def python(code: str) -> list:
    return [sys.executable, "-c", code]


def beats(path: Path) -> int:
    return path.stat().st_size if path.exists() else 0


def wait_for_beats(path: Path, seconds: float = 5.0) -> int:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline and beats(path) == 0:
        time.sleep(0.05)
    return beats(path)


class TestS14RunExternal(unittest.TestCase):
    def test_stdin_is_the_null_device(self):
        # A command that reads the terminal (a prompt, watch mode keys) gets end-of-file at once.
        done = audit_common.run_external(python("import sys; print(repr(sys.stdin.read()))"), timeout=20)
        self.assertEqual((done.returncode, done.stdout.strip(), done.timed_out), (0, "''", False))

    def test_environment_is_non_interactive_and_colourless(self):
        code = "import os; print(os.environ.get('CI'), os.environ.get('NO_COLOR'), os.environ.get('FORCE_COLOR'), os.environ.get('S14_EXTRA'))"
        clean = {key: value for key, value in os.environ.items() if key not in {"CI", "NO_COLOR", "FORCE_COLOR"}}
        with mock.patch.dict(os.environ, clean, clear=True):
            done = audit_common.run_external(python(code), timeout=20, env={"S14_EXTRA": "x"})
        self.assertEqual(done.stdout.split(), ["1", "1", "0", "x"])
        with mock.patch.dict(os.environ, {"CI": "true"}):
            kept = audit_common.run_external(python(code), timeout=20)
        self.assertEqual(kept.stdout.split()[0], "true")  # the caller's CI value is kept

    def test_streams_are_separate_or_merged_in_order(self):
        code = "import sys; print('out'); sys.stdout.flush(); print('err', file=sys.stderr); sys.stderr.flush(); print('out2')"
        split = audit_common.run_external(python(code), timeout=20)
        self.assertEqual((split.stdout, split.stderr), ("out\nout2\n", "err\n"))
        merged = audit_common.run_external(python(code), timeout=20, merge_stderr=True)
        self.assertEqual((merged.stdout, merged.stderr), ("out\nerr\nout2\n", ""))

    def test_exit_code_and_missing_command(self):
        self.assertEqual(audit_common.run_external(python("raise SystemExit(7)"), timeout=20).returncode, 7)
        with self.assertRaises(FileNotFoundError):
            audit_common.run_external(["definitely-not-a-real-command-s14"], timeout=5)

    def test_timeout_kills_the_whole_tree_and_keeps_the_partial_output(self):
        with TempProject() as project:
            heartbeat = project.root / "heartbeat"
            started = time.monotonic()
            done = audit_common.run_external([sys.executable, SPAWN_TREE, "wait", str(heartbeat), str(LIFETIME)], timeout=2)
            elapsed = time.monotonic() - started
            self.assertTrue(done.timed_out)
            self.assertIn("child-started", done.stdout)  # printed before the limit: kept as evidence
            self.assertLess(elapsed, LIFETIME - 1, "the helper waited for the tree instead of killing it")
            self.assertGreater(wait_for_beats(heartbeat, 1.0), 0, "the grandchild never started")
            before = beats(heartbeat)
            time.sleep(0.7)
            self.assertEqual(beats(heartbeat), before, "the grandchild survived the timeout")

    def test_a_process_left_behind_does_not_block_the_command(self):
        # The command exits 0 while a process it started still holds the output pipe.
        with TempProject() as project, mock.patch.object(audit_common, "PIPE_GRACE_SECONDS", 1):
            heartbeat = project.root / "heartbeat"
            started = time.monotonic()
            done = audit_common.run_external([sys.executable, SPAWN_TREE, "leave", str(heartbeat), "4"], timeout=20)
            elapsed = time.monotonic() - started
            self.assertEqual((done.returncode, done.timed_out), (0, False))
            self.assertIn("child-done", done.stdout)
            self.assertLess(elapsed, 3.5, "the helper waited for the pipe of a process that outlived the command")
            time.sleep(max(0.0, 4.5 - (time.monotonic() - started)))  # let the leftover end before the folder is removed

    def test_command_runs_in_the_given_directory(self):
        with TempProject() as project:
            done = audit_common.run_external(python("import os; print(os.getcwd())"), cwd=project.root, timeout=20)
            self.assertEqual(os.path.realpath(done.stdout.strip()), os.path.realpath(str(project.root)))

    def test_ansi_sequences_are_stripped(self):
        coloured = "\x1b[2m      Tests \x1b[22m \x1b[1m\x1b[32m22 passed\x1b[39m\x1b[22m\x1b[90m (22)\x1b[39m"
        self.assertEqual(audit_common.strip_ansi(coloured), "      Tests  22 passed (22)")


class TestS14EveryAuditUsesTheHelper(unittest.TestCase):
    def test_no_direct_subprocess_call_is_left(self):
        for name in CONVERTED:
            text = (AUDITS_DIR / f"{name}.py").read_text(encoding="utf-8")
            with self.subTest(name):
                self.assertIn("run_external", text)
                self.assertNotRegex(text, r"(?m)^import subprocess")

    def test_slow_linter_is_killed_at_its_limit(self):
        lint_runner = load_audit("lint_runner")
        linter = {"name": "slow", "cmd": [sys.executable, SLOW, str(LIFETIME)], "skip_reason": None}
        with TempProject() as project, mock.patch.object(lint_runner, "TIMEOUT_SECONDS", 1):
            started = time.monotonic()
            result = lint_runner.run_linter(linter, project.root)
            elapsed = time.monotonic() - started
        self.assertEqual((result["status"], result["timed_out"]), ("failed", True))
        self.assertIn("timeout after 1s", result["error"])
        self.assertIn("started-before-timeout", result["output"])
        self.assertLess(elapsed, LIFETIME - 1)


if __name__ == "__main__":
    unittest.main()
