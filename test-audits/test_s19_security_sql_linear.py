"""S19: the "SQL string concatenation" rule must be linear in the length of a line.

Bug: the rule was one regex, ``<keyword>[^\\n]*?\\+ operand | operand \\+[^\\n]*?<keyword>``.
From every ``x +`` it rescanned the rest of the line looking for a SQL keyword, so a
bundled file on one line (not named ``*.min.js``) cost 5.6 s at 100 KB and 87.5 s at
400 KB: the Security Scan, the first check of both orchestrators, looked hung and at
about 1 MB hit its time limit.

The rule now reads each line once (``_sql_concatenation_lines``) and finds the same lines.
"""
from __future__ import annotations

import time
import unittest

from audit_helpers import TempProject, load_audit

security_scan = load_audit("security_scan")

NAME = "SQL string concatenation"


def concatenation_lines(source: str, suffix: str = ".js"):
    without_comments, _ = security_scan.code_views(source, suffix)
    return sorted(line for line, name, *_ in security_scan.find_sql_injection(without_comments) if name == NAME)


def bundle(size: int) -> str:
    """One physical line of minified-looking code: thousands of ``operand+`` and no SQL."""
    unit = 'function f(a,b){return a+b.c(d)+e[0]+"x"+g}var h=i+j,k=l.m+n;'
    return (unit * (size // len(unit) + 1))[:size]


class TestS19SqlConcatenationIsLinear(unittest.TestCase):
    def test_long_single_line_is_scanned_quickly(self):
        source = bundle(300_000) + ';db.run("SELECT * FROM users WHERE id = " + userId);\n'
        started = time.monotonic()
        lines = concatenation_lines(source)
        elapsed = time.monotonic() - started
        self.assertEqual(lines, [1])  # the real finding at the end of the long line is still reported
        self.assertLess(elapsed, 10, "quadratic again: the old regex needed about 50 s for this input")

    def test_whole_scan_of_a_bundled_file_is_quick(self):
        with TempProject() as project:
            project.write("public/js/app.js", bundle(300_000) + "\n")
            started = time.monotonic()
            result = security_scan.scan_code_patterns(str(project.root))
            elapsed = time.monotonic() - started
        self.assertEqual(result["scanned_files"], 1)
        self.assertLess(elapsed, 15)

    def test_same_lines_as_the_regex_it_replaces(self):
        cases = {
            'run("SELECT id FROM t WHERE a = " + req.query.id)\n': [1],
            'const q = prefix + "SELECT * FROM t";\n': [1],
            'q = "SELECT * FROM t WHERE a=" +\n    userId\n': [1],          # operand on the next line
            'const q = prefix\n  + "SELECT * FROM t"\n': [1],              # leading "+": the operand line
            'q = "SELECT * FROM t" +\n\n\n   x\n': [1],
            'const q = (a) + "SELECT * FROM t";\n': [1],
            'q = parts[0] + "SELECT x FROM t"\n': [1],
            'db.run("insert into t values (" + v + ")")\n': [1],
            "x = 'delete from t where id=' + id\n": [1],
            'q = "UPDATE users SET name=" + name\n': [1],
            'a = "SELECT 1 FROM t" + x\nb = y + "SELECT 2 FROM t"\n': [1, 2],
            'i = i + 1; q = "SELECT * FROM t"\n': [1],
            # not a variable joined to SQL:
            'q = "SELECT * FROM t WHERE id = ?"\n': [],
            'const q = "a" + "SELECT * FROM t";\n': [],
            'const q = "SELECT * FROM t" + "x";\n': [],
            'const q = foo("x") + "SELECT * FROM t";\n': [],
            'q = 1 + "SELECT * FROM t"\n': [],
            'q = "SELECT * FROM t LIMIT " + 10\n': [],
            'total = a + b\nq = "SELECT * FROM t"\n': [],                  # the "+" is on another line
        }
        for source, expected in cases.items():
            with self.subTest(source):
                self.assertEqual(concatenation_lines(source), expected)

    def test_other_sql_rules_are_unchanged(self):
        source = (
            "const a = `SELECT * FROM t\n  WHERE id = ${id}`;\n"
            'q = "SELECT * FROM t WHERE id = %s" % user_id\n'
        )
        without_comments, _ = security_scan.code_views(source, ".js")
        found = sorted((line, name) for line, name, *_ in security_scan.find_sql_injection(without_comments))
        self.assertEqual(found, [(1, "SQL template literal interpolation"), (3, "SQL string formatting")])
        without_comments, _ = security_scan.code_views('q = f"SELECT * FROM t WHERE id = {user_id}"\n', ".py")
        self.assertEqual([name for _, name, *_ in security_scan.find_sql_injection(without_comments)], ["SQL f-string"])


if __name__ == "__main__":
    unittest.main()
