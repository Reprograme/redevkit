"""S15: the audits print line by line, also when their output is a pipe.

Bug: ``utf8_stdio`` left a piped stdout block-buffered, so an orchestrator showed nothing
until it exited (0 bytes after four finished checks) and a run killed from outside (the
time limit of the agent's tool) lost every line it had "printed".
"""
from __future__ import annotations

import subprocess
import sys
import threading
import unittest

from audit_helpers import AUDITS_DIR

CHILD = (
    "import sys, time\n"
    "sys.dont_write_bytecode = True\n"
    "sys.path.insert(0, sys.argv[1])\n"
    "import validation_runner\n"
    "validation_runner.utf8_stdio()\n"
    "print('visible-before-exit')\n"
    "time.sleep(6)\n"  # ends by itself; the test stops it earlier
)


class TestS15LineBuffering(unittest.TestCase):
    def test_every_utf8_stdio_is_line_buffered(self):
        for path in sorted(AUDITS_DIR.glob("*.py")):
            text = path.read_text(encoding="utf-8")
            if "def utf8_stdio" not in text:
                continue
            with self.subTest(path.name):
                self.assertIn('reconfigure(encoding="utf-8", errors="replace", line_buffering=True)', text)

    def test_a_printed_line_reaches_the_pipe_while_the_script_still_runs(self):
        proc = subprocess.Popen(
            [sys.executable, "-c", CHILD, str(AUDITS_DIR)],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        )
        lines = []
        reader = threading.Thread(target=lambda: lines.append(proc.stdout.readline()), daemon=True)
        reader.start()
        try:
            reader.join(4.5)  # the child lives 6 s: a buffered line would only arrive at its exit
            arrived_while_running = not reader.is_alive() and proc.poll() is None
        finally:
            proc.kill()
            proc.wait(timeout=10)
            reader.join(5)
            proc.stdout.close()
        self.assertTrue(arrived_while_running, "nothing reached the pipe before the script ended")
        self.assertEqual(lines[0].decode("utf-8").strip(), "visible-before-exit")


if __name__ == "__main__":
    unittest.main()
