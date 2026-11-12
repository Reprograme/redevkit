"""Grandchild of the S14 tests: appends one byte to a file every 0.1 s.

usage: heartbeat.py FILE LIFETIME_SECONDS

It always ends by itself after LIFETIME_SECONDS, so a failed tree kill can never
leave a process behind. It keeps the stdout/stderr it inherited open (that is what
blocked the audits: the pipe of a killed parent stays open in its children).
"""
import sys
import time

target, lifetime = sys.argv[1], float(sys.argv[2])
deadline = time.monotonic() + lifetime
while time.monotonic() < deadline:
    with open(target, "ab") as handle:
        handle.write(b".")
    time.sleep(0.1)
