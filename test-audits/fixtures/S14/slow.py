"""A command slower than its time limit: prints one line, then sleeps.

usage: slow.py [LIFETIME_SECONDS]   (default 6; it always ends by itself)
"""
import sys
import time

print("started-before-timeout", flush=True)
time.sleep(float(sys.argv[1]) if len(sys.argv) > 1 else 6)
print("finished-in-time", flush=True)
