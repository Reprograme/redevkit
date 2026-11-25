"""B20: only an effective declaration of pytest makes it the project's Python runner.

Bug: ``_pytest_configured`` looked for the word ``pytest`` anywhere in pyproject.toml,
requirements*.txt, setup.cfg and tox.ini. A comment (``# we do not use pytest``) or another
tool's name (``flake8-pytest-style`` in the ruff configuration) made a unittest project
``Framework: pytest``, ``SKIPPED (pytest is not installed ...)``, exit 3: its failing
unittest suite never ran.

Decision: pytest is declared by ``pytest.ini``/``conftest.py``, by a pytest section
(``[tool.pytest.ini_options]``, ``[tool:pytest]``, ``[pytest]``), or by ``pytest`` (or a
``pytest-*`` plugin, which only runs under pytest) as a requirement: uncommented lines of
requirements files, pyproject.toml dependency lists, setup.cfg options, tox.ini ``deps``.
pyproject.toml is parsed with ``tomllib`` when it exists (3.11+), else by a line scan
(3.9, 3.10); both are tested here.
"""
from __future__ import annotations

import unittest
from unittest import mock

from audit_helpers import TempProject, load_audit, run_main

test_runner = load_audit("test_runner")

RED = "import unittest\nclass R(unittest.TestCase):\n    def test_red(self):\n        self.assertEqual(1, 2)\n"

NOT_DECLARED = {
    "pyproject.toml": (
        '[project]\nname = "x"\ndependencies = ["requests"]  # we do not use pytest\n'
        "[tool.ruff]\n# flake8-pytest-style rules\n"
        '[tool.ruff.lint]\nselect = ["PT"]\n'
        "[tool.ruff.lint.flake8-pytest-style]\nfixture-parentheses = false\n"
        '[project.optional-dependencies]\nlint = ["flake8-pytest-style>=2", "types-pytest-lazy-fixture"]\n'
        '[tool.hatch.envs.default.scripts]\ntest = "pytest {args}"\n'
    ),
    "requirements.txt": "# pytest is not used here\nrequests==2.0  # not pytest\nflake8-pytest-style\n",
    "requirements-dev.txt": "  #pytest\n-r requirements.txt\n",
    "setup.cfg": "[metadata]\nname = x\n# [tool:pytest]\n[flake8]\nselect = PT  ; flake8-pytest-style\n",
    "tox.ini": "[tox]\nenvlist = py\n# [pytest]\n[testenv]\ndeps = flake8-pytest-style\ncommands = python -m unittest\n",
}

DECLARED = (
    ("requirements.txt", "requests\npytest\n"),
    ("requirements.txt", "pytest==8.3.2 ; python_version >= '3.9'\n"),
    ("requirements-test.txt", "pytest[testing]>=8  # the runner\n"),
    ("requirements-dev.txt", "pytest-cov\n"),
    ("pyproject.toml", "[tool.pytest.ini_options]\naddopts = \"-q\"\n"),
    ("pyproject.toml", '[project]\nname = "x"\ndependencies = [\n  "requests",\n  "pytest>=8",\n]\n'),
    ("pyproject.toml", '[project.optional-dependencies]\ntest = ["pytest", "coverage"]\n'),
    ("pyproject.toml", '[dependency-groups]\ndev = ["pytest>=8", {include-group = "lint"}]\nlint = ["ruff"]\n'),
    ("pyproject.toml", '[tool.poetry.dependencies]\npython = "^3.9"\n[tool.poetry.group.dev.dependencies]\npytest = "^8"\n'),
    ("pyproject.toml", '[tool.poetry.dev-dependencies]\npytest = { version = "^8" }\n'),
    ("pyproject.toml", '[tool.pdm.dev-dependencies]\ntest = ["pytest"]\n'),
    ("pyproject.toml", '[tool.uv]\ndev-dependencies = ["pytest"]\n'),
    ("pyproject.toml", '[tool.hatch.envs.test]\ndependencies = ["pytest"]\n'),
    ("setup.cfg", "[tool:pytest]\naddopts = -q\n"),
    ("setup.cfg", "[options]\ninstall_requires =\n    requests\n    pytest>=7\n"),
    ("setup.cfg", "[options.extras_require]\ntest =\n    pytest\n"),
    ("tox.ini", "[pytest]\naddopts = -q\n"),
    ("tox.ini", "[testenv]\ndeps =\n    pytest\n    coverage\ncommands = pytest\n"),
)


class TestB20PytestDeclarations(unittest.TestCase):
    def check_both_parsers(self, files, expected: bool):
        for parser in ("tomllib", "line scan"):
            patch = mock.patch.object(test_runner, "tomllib", None) if parser == "line scan" else mock.patch.object(
                test_runner, "tomllib", test_runner.tomllib)
            with self.subTest(files=files, parser=parser), TempProject() as project, patch:
                for name, text in files.items():
                    project.write(name, text)
                self.assertIs(test_runner._pytest_configured(project.root), expected)

    def test_comments_and_other_tool_names_are_not_declarations(self):
        for name, text in NOT_DECLARED.items():
            self.check_both_parsers({name: text}, False)
        self.check_both_parsers(NOT_DECLARED, False)

    def test_effective_declarations_are_recognised(self):
        for name, text in DECLARED:
            self.check_both_parsers({name: text}, True)

    def test_invalid_toml_falls_back_to_the_line_scan(self):
        self.check_both_parsers({"pyproject.toml": '[project\ndependencies = ["pytest"]\n'}, True)
        self.check_both_parsers({"pyproject.toml": "[project\n# pytest\n"}, False)

    def test_comment_with_pytest_runs_the_unittest_suite(self):
        for name, text in (("pyproject.toml", NOT_DECLARED["pyproject.toml"]),
                           ("requirements.txt", NOT_DECLARED["requirements.txt"])):
            with self.subTest(file=name), TempProject() as project, \
                    mock.patch.object(test_runner, "python_module_available", return_value=False):
                project.write(name, text)
                project.write("test_red.py", RED)
                code, out = run_main(test_runner, [str(project.root)])
            self.assertIn("Framework: unittest", out)
            self.assertEqual(code, 1, out)  # the failing suite ran: never SKIPPED
            self.assertIn("Tests: 1 total, 0 passed, 1 failed", out)

    def test_declared_pytest_that_is_not_installed_is_still_skipped(self):
        with TempProject() as project, mock.patch.object(test_runner, "python_module_available", return_value=False):
            project.write("requirements.txt", "pytest\n")
            project.write("test_red.py", RED)
            code, out = run_main(test_runner, [str(project.root)])
        self.assertIn("Framework: pytest", out)
        self.assertEqual(code, 3, out)


if __name__ == "__main__":
    unittest.main()
