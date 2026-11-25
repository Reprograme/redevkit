"""A11: ``--timeout`` must be a finite number greater than 0.

Bug: ``_positive_seconds`` only refused ``value <= 0``. ``nan <= 0`` is false, so ``nan``,
``inf`` and ``1e999`` (float() turns it into ``inf``) were accepted; the test command
started and the runner crashed (``ValueError``/``OverflowError``, exit 1) instead of a usage
error (exit 2) before any process starts.
"""
from __future__ import annotations

import argparse
import unittest
from unittest import mock

from audit_helpers import TempProject, load_audit, run_main

test_runner = load_audit("test_runner")


class TestA11FiniteTimeout(unittest.TestCase):
    INVALID = ("nan", "NaN", "inf", "-inf", "Infinity", "1e999", "-1e999", "0", "-5", "abc")

    def test_invalid_values_are_usage_errors_before_anything_runs(self):
        for value in self.INVALID:
            with self.subTest(value), TempProject() as project, \
                    mock.patch.object(test_runner, "run_external") as run_external:
                project.write("test_ok.py", "")
                code, out = run_main(test_runner, [str(project.root), "--cmd", "python -m unittest", f"--timeout={value}"])
                self.assertEqual(code, 2, out)
                run_external.assert_not_called()

    def test_the_type_function(self):
        for value in self.INVALID:
            with self.subTest(value), self.assertRaises(argparse.ArgumentTypeError):
                test_runner._positive_seconds(value)
        self.assertEqual(test_runner._positive_seconds("0.5"), 0.5)
        self.assertEqual(test_runner._positive_seconds("600"), 600.0)
        self.assertEqual(test_runner._positive_seconds("1e3"), 1000.0)


if __name__ == "__main__":
    unittest.main()
