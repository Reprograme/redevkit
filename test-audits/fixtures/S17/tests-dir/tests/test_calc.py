"""The usual layout: tests/ next to the code, without tests/__init__.py."""
import unittest


class CalcTest(unittest.TestCase):
    def test_sum_is_right(self):
        self.assertEqual(1 + 1, 2)

    def test_sum_is_wrong(self):
        self.assertEqual(1 + 1, 3)  # fails on purpose: the runner must report FAIL, not SKIPPED
