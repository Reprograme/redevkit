"""Child of the S14 tests: starts heartbeat.py (the grandchild) and then waits or leaves.

usage: spawn_tree.py MODE HEARTBEAT_FILE LIFETIME_SECONDS

MODE ``wait``: prints ``child-started`` and sleeps LIFETIME_SECONDS (a command that never
finishes in time: watch mode, a prompt). MODE ``leave``: prints ``child-done`` and exits 0
at once while the grandchild lives on with the inherited pipes (a script that leaves a
background process behind). Both processes end by themselves after LIFETIME_SECONDS.
"""
import subprocess
import sys
import time
from pathlib import Path

mode, target, lifetime = sys.argv[1], sys.argv[2], float(sys.argv[3])
subprocess.Popen([sys.executable, str(Path(__file__).with_name("heartbeat.py")), target, str(lifetime)])
if mode == "wait":
    print("child-started", flush=True)
    time.sleep(lifetime)
else:
    print("child-done", flush=True)
