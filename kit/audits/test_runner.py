#!/usr/bin/env python3
"""
Test Runner - Unified test execution and coverage reporting.
Runs the project's tests based on project type.

Usage:
    python test_runner.py <project_path> [--cmd COMMAND] [--coverage] [--timeout SECONDS]
                                         [--log FILE] [--paths FILE [FILE ...]]

The runner is agnostic of the test suite: ``--cmd`` runs any test command (the project's
declared one, ``tech.md`` > Dev environment > Test) with the same time limit, log and
verdict. A ``{paths}`` token in it marks where test files go. The command runs without a
shell: leading ``NAME=value`` words set environment variables, and shell operators
(``&&``, ``|``, ``;``, redirections) are a usage error (exit 2): put chained steps in a
project script. Without ``--cmd`` the command is detected:

    - Node.js: npm test, jest, vitest (project-local binaries only, no downloads)
    - PHP: Pest or PHPUnit from vendor/bin (``composer.json`` ``config.bin-dir``), else the
      ``composer test`` script, else a global ``phpunit`` next to a phpunit.xml
    - Python: pytest, unittest (the project's .venv/venv interpreter when it exists,
      otherwise the current interpreter)
    - Go (go test ./...), Rust (cargo test), .NET (dotnet test), Ruby (rspec, rails test),
      Java with Maven (mvnw or mvn -B test). Gradle prints no test result by default, so
      it needs a declared command whose output shows the results.

``--paths`` runs only the given test files (relative to the project). vitest, jest
(directly or through ``npm test --``), a ``node --test`` script without positional
arguments, pytest, unittest, Pest, PHPUnit (several files from PHPUnit 10), rspec, rails
test, go test (the packages of the files) and a declared command with ``{paths}`` take test
files; any other test command cannot, so the whole suite runs and the output says so
(``Scope: full suite (...)``, JSON ``"scope": "full suite"`` with ``"paths_ignored"``). A
path that does not exist or lies outside the project is a usage error (exit 2).

Executables are resolved with shutil.which (npm resolves to npm.cmd on
Windows). The test command runs through audit_common.run_external: it cannot
read the terminal (no watch mode, no prompt) and the whole process tree is
killed when the time limit expires.

Verdict (the exit code follows the 0/1/2/3 contract of the audits):

* PASS (0): the command exited 0 and its output shows that tests ran: a
  recognised summary (unittest, pytest, jest, vitest, node:test, mocha, PHPUnit,
  Pest, RSpec, minitest, cargo, Maven Surefire, dotnet, or a generic "N passed")
  with at least one test and no failed one, or, for a format the runner does
  not parse, any evidence of executed tests ("12 specs", "ok 1", a check mark,
  "PASS file") printed by the test script itself (npm's pretest and posttest output
  and build lines such as "✓ 34 modules transformed" do not count); see
  ``has_test_evidence``.
* SKIPPED (3): no test command, runner or declared framework not installed,
  the summary says zero tests ran or that every test was skipped (0 passed,
  0 failed, skipped/pending/ignored > 0), the runner reported that it found no
  test file, or the command exited 0 without any test result in its output (for
  example ``"test": "echo ok"``). Nothing was verified: never PASS.
* FAIL (1): any other non-zero exit code, a recognised summary with failed tests
  even when the command exited 0 (observed failures take precedence; every summary
  of the output is added up), a failure line of any known runner in an output that
  exited 0 (``failure_signal``), and a timeout. A timeout prints a ``[TIMEOUT]`` line and the JSON carries
  ``"status": "timeout"`` and ``"timed_out": true``.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
import re
import shlex
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

sys.dont_write_bytecode = True  # importing the shared helper must not leave __pycache__ behind
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_common import run_external, strip_ansi, unsafe_batch_argument  # noqa: E402

tomllib: Any
try:
    import tomllib  # Python 3.11+
except ImportError:  # Python 3.9 and 3.10: pyproject.toml is read by a line scan
    tomllib = None

EXIT_PASS, EXIT_FAIL, EXIT_USAGE, EXIT_SKIPPED = 0, 1, 2, 3
TIMEOUT_SECONDS = 300  # default of --timeout
TAIL_LINES = 40  # lines of test output shown (the end: failures and the summary are there)
NO_TESTS_EXIT_CODES = {5}  # pytest "no tests collected", unittest "NO TESTS RAN" (3.12+)
PYTHON_FRAMEWORKS = {"pytest", "unittest"}  # the only commands whose exit 5 means "no tests"
NPM_PLACEHOLDER = "no test specified"  # `npm init` default: echo "Error: no test specified" && exit 1
VITEST_COVERAGE_PROVIDERS = ("@vitest/coverage-v8", "@vitest/coverage-istanbul")
COVERAGE_PROVIDER_MISSING = "coverage provider not installed"
COVERAGE_UNSUPPORTED = "coverage not supported for this test command"
COVERAGE_DECLARED = "coverage not supported for a declared command (add the coverage flags to --cmd)"
NO_TEST_RESULT = "the test command exited 0 but its output shows no test result"
PATHS_TOKEN = "{paths}"  # in --cmd: replaced by the --paths files, removed without them
NO_PATHS_TOKEN = "the declared command has no {paths} token"
SHELL_OPERATOR = re.compile(r"^[;&|<>()]+$|^\d+>")  # a whole word made of operators, or "2>file"
ENV_ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
DOTNET_PROJECTS = ("*.sln", "*.slnx", "*.csproj", "*.fsproj", "*.vbproj")
# dotnet prints its summary in the OS language ("Aprovado! – Com falha: 0, ..."): English keeps it parseable.
# A NAME=value word of --cmd overrides these.
RUNNER_ENV = {"DOTNET_CLI_UI_LANGUAGE": "en", "VSLANG": "1033"}
# A test script that is only `node --test` plus flags takes test files after `npm test --`;
# with a positional argument (a folder, a glob) the files would run in addition to it.
NODE_TEST_SCRIPT = re.compile(r"^node --test(?: --[A-Za-z][\w-]*(?:=\S+)?)*$")


def utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)  # type: ignore[union-attr]
        except (AttributeError, ValueError, OSError):
            pass


def which(name: str) -> Optional[str]:
    """Resolve an executable on PATH (``npm`` -> ``npm.cmd`` on Windows)."""
    return shutil.which(name)


def local_bin(project_path: Path, name: str) -> Optional[str]:
    """node_modules/.bin executable of the project or of a parent folder (workspaces hoist
    dependencies, and npm itself looks there); never downloads with npx."""
    for parent in (project_path, *project_path.parents):
        folder = parent / "node_modules" / ".bin"
        if folder.is_dir():
            found = shutil.which(name, path=str(folder))
            if found:
                return found
    return None


def node_package_installed(project_path: Path, package: str) -> bool:
    """True when ``node_modules/<package>`` exists in the project or in a parent folder."""
    return any(
        (parent / "node_modules" / package / "package.json").is_file()
        for parent in (project_path, *project_path.parents)
    )


def project_python(project_path: Path) -> str:
    """Interpreter of the project's virtual environment (``.venv`` or ``venv``), else the current one."""
    for name in (".venv", "venv"):
        for relative in (("Scripts", "python.exe"), ("bin", "python"), ("bin", "python3")):
            candidate = project_path / name / relative[0] / relative[1]
            if candidate.is_file():
                return str(candidate)
    return sys.executable


def python_module_available(module: str, python: Optional[str] = None) -> bool:
    """True when ``module`` can be imported by ``python`` (default: the current interpreter)."""
    if python and os.path.normcase(python) != os.path.normcase(sys.executable):
        probe = f"import importlib.util, sys; sys.exit(0 if importlib.util.find_spec({module!r}) else 1)"
        try:
            done = run_external([python, "-c", probe], timeout=30)
        except OSError:
            return False
        return done.returncode == 0 and not done.timed_out
    try:
        return importlib.util.find_spec(module) is not None
    except (ImportError, ValueError):
        return False


def _python_project(project_path: Path) -> bool:
    markers = ("pyproject.toml", "requirements.txt", "setup.py", "setup.cfg", "pytest.ini", "tox.ini")
    return any((project_path / name).exists() for name in markers)


# A requirement ("pytest", "pytest[testing]>=8", "pytest==8.3 ; python_version>'3.8'",
# "pytest @ https://..."): the distribution name and nothing that is not a requirement after it.
_REQUIREMENT = re.compile(
    r"^\s*([A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?)\s*(?:\[[^\]]*\])?\s*"
    r"(?:(?:[<>=!~]=?|===)[^;@]*)?\s*(?:@[^;]*)?\s*(?:;.*)?$"
)
_INI_SECTION = re.compile(r"^\s*\[([^\]]+)\]\s*$")
_INI_KEY = re.compile(r"^([^=:\s][^=:]*?)\s*[=:]\s*(.*)$")
_TOML_TABLE = re.compile(r"^\s*\[\[?\s*([^\]]+?)\s*\]\]?\s*$")
_TOML_KEY = re.compile(r"""^\s*("[^"]*"|'[^']*'|[A-Za-z0-9_.-]+)\s*=\s*(.*)$""")
_TOML_STRING = re.compile(r'"((?:[^"\\]|\\.)*)"|\'([^\']*)\'')


def _names_pytest(requirement: str) -> bool:
    """True for a requirement of pytest or of a pytest plugin (``pytest-cov``, ``pytest_mock``).

    A plugin depends on pytest and only runs under it. ``flake8-pytest-style`` or
    ``types-pytest`` are other tools: their name does not start with ``pytest``.
    """
    match = _REQUIREMENT.match(requirement)
    if not match:
        return False
    name = re.sub(r"[-_.]+", "-", match.group(1)).lower()
    return name == "pytest" or name.startswith("pytest-")


def _requirement_lines(text: str) -> List[str]:
    """The requirement lines of a requirements file or of an INI value: comments
    (a ``#`` at the start or after a space) and option lines (``-r``, ``--hash``) removed."""
    lines = []
    for line in text.splitlines():
        line = re.sub(r"(?:^|\s)[#;].*$", "", line).strip()
        if line and not line.startswith("-"):
            lines.append(line)
    return lines


def _ini_sections(text: str) -> Dict[str, Dict[str, str]]:
    """Sections of an INI file (setup.cfg, tox.ini): name -> key -> value, continuation
    lines joined with newlines. Lenient: comment lines are dropped, duplicates are merged."""
    sections: Dict[str, Dict[str, str]] = {}
    section: Optional[Dict[str, str]] = None
    key: Optional[str] = None
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped[0] in "#;":
            continue
        header = _INI_SECTION.match(line)
        if header:
            section = sections.setdefault(header.group(1).strip().lower(), {})
            key = None
            continue
        if section is None:
            continue
        if line[0] in " \t" and key is not None:
            section[key] += "\n" + stripped
            continue
        pair = _INI_KEY.match(stripped)
        if pair:
            key = pair.group(1).strip().lower()
            section[key] = pair.group(2)
    return sections


def _ini_declares_pytest(text: str, config_sections: Sequence[str], requirement_keys: Sequence[str]) -> bool:
    """A pytest section (``[tool:pytest]``, ``[pytest]``), or pytest in a requirement value."""
    sections = _ini_sections(text)
    if any(name in sections for name in config_sections):
        return True
    for name, values in sections.items():
        for key, value in values.items():
            # setup.cfg: [options] install_requires/tests_require, [options.extras_require] any
            # key; tox.ini: deps of any [testenv...] section.
            wanted = key in requirement_keys or name == "options.extras_require"
            if wanted and any(_names_pytest(line) for line in _requirement_lines(value)):
                return True
    return False


def _toml_requirements(data: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    """(requirement strings, Poetry dependency names) of a parsed pyproject.toml."""
    def table(value: Any) -> Dict[str, Any]:
        return value if isinstance(value, dict) else {}

    def strings(value: Any) -> List[str]:
        return [item for item in value if isinstance(item, str)] if isinstance(value, list) else []

    project, tool = table(data.get("project")), table(data.get("tool"))
    requirements = strings(project.get("dependencies"))
    for group in table(project.get("optional-dependencies")).values():
        requirements += strings(group)
    for group in table(data.get("dependency-groups")).values():  # PEP 735
        requirements += strings(group)
    requirements += strings(table(tool.get("uv")).get("dev-dependencies"))
    for group in table(table(tool.get("pdm")).get("dev-dependencies")).values():
        requirements += strings(group)
    for env in table(table(tool.get("hatch")).get("envs")).values():
        requirements += strings(table(env).get("dependencies")) + strings(table(env).get("extra-dependencies"))
    poetry = table(tool.get("poetry"))
    names = list(table(poetry.get("dependencies"))) + list(table(poetry.get("dev-dependencies")))
    for group in table(poetry.get("group")).values():
        names += list(table(table(group).get("dependencies")))
    return requirements, names


def _toml_strip_comment(line: str) -> str:
    """``line`` without its ``#`` comment (a ``#`` inside a string is kept)."""
    quote = ""
    for index, char in enumerate(line):
        if quote:
            if char == "\\" and quote == '"':
                continue
            if char == quote:
                quote = ""
        elif char in "\"'":
            quote = char
        elif char == "#":
            return line[:index]
    return line


def _toml_scan_declares_pytest(text: str) -> bool:
    """Line scan of pyproject.toml without ``tomllib`` (Python 3.9, 3.10) or when it does not
    parse: a ``[tool.pytest...]`` table, a ``pytest`` key in a dependencies table (Poetry), or
    a pytest requirement string in a dependencies table or array. Comments are ignored."""
    table, key = "", ""
    depth = 0  # open brackets of a multi-line array
    for raw in text.splitlines():
        line = _toml_strip_comment(raw).strip()
        if not line:
            continue
        header = _TOML_TABLE.match(line) if depth == 0 else None
        if header:
            table, key = header.group(1).replace(" ", "").replace('"', "").replace("'", ""), ""
            if table == "tool.pytest" or table.startswith("tool.pytest."):
                return True
            continue
        if depth == 0:
            pair = _TOML_KEY.match(line)
            if not pair:
                continue
            key, line = pair.group(1).strip("\"'"), pair.group(2)
            if "dependencies" in table and _names_pytest(key):
                return True  # [tool.poetry.dependencies] pytest = "^8"
        in_dependencies = ("dependencies" in key or "dependencies" in table or table == "dependency-groups"
                           or table.startswith("dependency-groups."))
        if in_dependencies:
            for match in _TOML_STRING.finditer(line):
                if _names_pytest(match.group(1) if match.group(1) is not None else match.group(2)):
                    return True
        depth = max(depth + line.count("[") - line.count("]"), 0)  # strings with brackets are rare
    return False


def _pyproject_declares_pytest(text: str) -> bool:
    if tomllib is not None:
        try:
            data = tomllib.loads(text)
        except ValueError:  # TOMLDecodeError: the line scan still reads the declarations
            data = None
        if isinstance(data, dict):
            if isinstance(data.get("tool"), dict) and "pytest" in data["tool"]:
                return True  # [tool.pytest.ini_options]
            requirements, names = _toml_requirements(data)
            return any(_names_pytest(item) for item in requirements + names)
    return _toml_scan_declares_pytest(text)


def _pytest_configured(project_path: Path) -> bool:
    """True when the project declares pytest: ``pytest.ini`` or ``conftest.py``, a pytest
    section (``[tool.pytest.ini_options]``, ``[tool:pytest]`` in setup.cfg, ``[pytest]`` in
    tox.ini), or pytest (or a ``pytest-*`` plugin) in a requirement of ``requirements*.txt``,
    the pyproject.toml dependency lists, setup.cfg options or tox.ini ``deps``. The word in a
    comment or in another tool's name (``flake8-pytest-style``) is not a declaration."""
    if (project_path / "pytest.ini").exists() or (project_path / "conftest.py").exists():
        return True
    checks = [(path, lambda text: any(_names_pytest(line) for line in _requirement_lines(text)))
              for path in sorted(project_path.glob("requirements*.txt"))]
    checks += [
        (project_path / "pyproject.toml", _pyproject_declares_pytest),
        (project_path / "setup.cfg", lambda text: _ini_declares_pytest(
            text, ("tool:pytest",), ("install_requires", "tests_require", "setup_requires"))),
        (project_path / "tox.ini", lambda text: _ini_declares_pytest(text, ("pytest",), ("deps",))),
    ]
    for path, declares in checks:
        try:
            if path.is_file() and declares(path.read_text("utf-8", errors="ignore")):
                return True
        except OSError:
            continue
    return False


def _package_holds_tests(folder: Path, seen: Optional[set] = None) -> bool:
    """True when a package below ``folder`` holds a ``test*.py``: unittest discovery from
    ``folder`` reaches it (it descends only into folders with ``__init__.py``, at any depth)."""
    seen = set() if seen is None else seen
    try:
        real = os.path.realpath(str(folder))
        if real in seen:
            return False  # a symlink loop
        seen.add(real)
        entries = sorted(entry for entry in folder.iterdir() if entry.is_dir())
    except OSError:
        return False
    for entry in entries:
        if (entry / "__init__.py").is_file() and (any(entry.glob("test*.py")) or _package_holds_tests(entry, seen)):
            return True
    return False


def _unittest_start_dirs(project_path: Path) -> List[str]:
    """Start directories for ``unittest discover``, relative to the project.

    From the project root unittest only finds ``test*.py`` in the root and in packages
    below it, so the usual ``tests/test_x.py`` without ``tests/__init__.py`` is invisible
    ("no tests found" although tests exist, even failing ones). Every supported location
    that holds tests is a start: the root when it has a ``test*.py`` or a package below it
    holds one (``tests/`` with ``__init__.py``, ``mypkg/tests/``), and each of
    ``tests``/``test`` that is not a package and holds one. A package folder is never a
    start of its own: the root discovery finds it, and it does not enter a folder that is
    not a package, so no test is discovered twice.
    """
    root_tests = any(project_path.glob("test*.py")) or _package_holds_tests(project_path)
    starts = ["."] if root_tests else []
    for name in ("tests", "test"):
        folder = project_path / name
        if folder.is_dir() and not (folder / "__init__.py").exists() and any(folder.glob("test*.py")):
            starts.append(name)
    # A folder below tests/ or test/ that no start reaches (tests/unit/ without __init__.py):
    # discovery would skip its tests in silence, even failing ones. It becomes a start of its own.
    for name in ("tests", "test"):
        for folder in _test_folders(project_path / name):
            rel = folder.relative_to(project_path).as_posix()
            if not any(_discovery_reaches(project_path, start, rel) for start in starts):
                starts.append(rel)
    return starts


_SKIPPED_TEST_DIRS = {"__pycache__", "node_modules", "fixtures", "site-packages"}


def _test_folders(top: Path) -> List[Path]:
    """Folders below ``top`` (not ``top`` itself) that hold a ``test*.py``, in sorted order.
    Hidden folders, ``__pycache__``, ``node_modules``, ``fixtures`` and symlinked folders are not entered."""
    found: List[Path] = []
    if not top.is_dir():
        return found
    for current, dirs, files in os.walk(str(top)):
        dirs[:] = sorted(d for d in dirs if not d.startswith(".") and d not in _SKIPPED_TEST_DIRS
                         and not os.path.islink(os.path.join(current, d)))
        path = Path(current)
        if path != top and any(f.startswith("test") and f.endswith(".py") for f in files):
            found.append(path)
    return found


def _discovery_reaches(project_path: Path, start: str, rel: str) -> bool:
    """True when ``unittest discover -s start`` finds the tests of folder ``rel``: it is the
    start, or every folder from below the start down to ``rel`` is a package."""
    if rel == start:
        return True
    prefix = "" if start == "." else start + "/"
    if not rel.startswith(prefix):
        return False
    parts = rel[len(prefix):].split("/")
    base = project_path if start == "." else project_path / start
    for index in range(len(parts)):
        if not (base.joinpath(*parts[: index + 1]) / "__init__.py").is_file():
            return False
    return True


# ``unittest discover`` takes one start directory. Several starts run one after the other,
# each ``discover -v -s <start> -t <start>`` in its own process, so a start never sees the
# modules or the sys.path entries of another (tests/helpers.py and test/helpers.py each
# import their own, also inside a test). Each prints its own summary; the runner adds them
# up. Exit code: 1 when a start failed, 5 when no start ran a test (as unittest 3.12+),
# else 0.
UNITTEST_MULTI = (
    "import subprocess, sys\n"
    "codes = []\n"
    "for start in sys.argv[1:]:\n"
    "    print('[unittest] discover -s ' + start, flush=True)\n"
    "    codes.append(subprocess.call([sys.executable, '-m', 'unittest', 'discover', '-v', '-s', start, '-t', start]))\n"
    "sys.exit(1 if any(code not in (0, 5) for code in codes) else 5 if all(code == 5 for code in codes) else 0)\n"
)
UNITTEST_MULTI_LABEL = '"<unittest discover -s START, one process per start>"'  # shown instead of the script


def _unittest_command(python: str, project_path: Path) -> List[str]:
    """``unittest discover`` of every start directory (see ``_unittest_start_dirs``)."""
    starts = _unittest_start_dirs(project_path)
    if len(starts) > 1:
        return [python, "-c", UNITTEST_MULTI, *starts]
    extra = ["-s", starts[0]] if starts and starts[0] != "." else []
    return [python, "-m", "unittest", "discover", "-v", *extra]


def _empty_result() -> Dict[str, Any]:
    return {
        "type": "unknown",
        "framework": None,
        "cmd": None,
        "coverage_cmd": None,
        "coverage_skip_reason": COVERAGE_UNSUPPORTED,
        "skip_reason": "no test framework detected",
    }


def _runnable(result: Dict[str, Any], framework: str, cmd: List[str],
              coverage_cmd: Optional[List[str]] = None,
              coverage_skip_reason: str = COVERAGE_UNSUPPORTED) -> Dict[str, Any]:
    result.update({
        "framework": framework, "cmd": cmd, "coverage_cmd": coverage_cmd,
        "coverage_skip_reason": coverage_skip_reason, "skip_reason": None,
    })
    return result


def _not_runnable(result: Dict[str, Any], framework: Optional[str], reason: str) -> Dict[str, Any]:
    result.update({"framework": framework, "cmd": None, "skip_reason": reason})
    return result


def _read_json(path: Path) -> Dict[str, Any]:
    """The JSON object in ``path`` (a BOM is accepted), {} when unreadable."""
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _detect_node(project_path: Path, result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    package_json = project_path / "package.json"
    if not package_json.exists():
        return None
    result["type"] = "node"
    try:
        pkg = json.loads(package_json.read_text(encoding="utf-8-sig"))  # npm accepts a BOM
    except (OSError, ValueError) as exc:  # ValueError: invalid JSON or invalid UTF-8
        pkg = {}
        result["skip_reason"] = f"package.json could not be read: {exc}"
    scripts = pkg.get("scripts", {}) if isinstance(pkg, dict) else {}
    deps: Dict[str, Any] = {}
    if isinstance(pkg, dict):
        for section in ("dependencies", "devDependencies"):
            if isinstance(pkg.get(section), dict):
                deps.update(pkg[section])

    coverage_cmd = None
    coverage_skip_reason = COVERAGE_UNSUPPORTED
    framework = None
    binary = None
    if "vitest" in deps:
        framework = "vitest"
        binary = local_bin(project_path, "vitest")
        if binary and any(node_package_installed(project_path, name) for name in VITEST_COVERAGE_PROVIDERS):
            coverage_cmd = [binary, "run", "--coverage"]
        else:
            # Without its provider ``vitest --coverage`` fails before running any test.
            coverage_skip_reason = COVERAGE_PROVIDER_MISSING
    elif "jest" in deps:
        framework = "jest"
        binary = local_bin(project_path, "jest")
        coverage_cmd = [binary, "--coverage"] if binary else None

    test_script = scripts.get("test") if isinstance(scripts, dict) else None
    placeholder = isinstance(test_script, str) and NPM_PLACEHOLDER in test_script
    has_script = not placeholder and isinstance(scripts, dict) and "test" in scripts
    if placeholder and not framework:
        # Not a test command: the next stacks are tried, else SKIPPED.
        result["skip_reason"] = "package.json test script is the npm placeholder (no test specified)"
        return None
    if framework and not binary:
        # The declared framework is not installed: `npm test` could only fail with
        # "command not found". Nothing can be verified until the dependencies are installed.
        return _not_runnable(
            result, framework, f"{framework} is not installed in node_modules/.bin (run the package install first)"
        )
    if has_script:
        npm = which("npm")
        if not framework and isinstance(test_script, str) and NODE_TEST_SCRIPT.match(test_script.strip()):
            framework = "node --test"
        if not npm:
            return _not_runnable(result, framework or "npm test", "npm not found on PATH")
        return _runnable(result, framework or "npm test", [npm, "test"], coverage_cmd, coverage_skip_reason)
    if framework:
        cmd = [binary, "run"] if framework == "vitest" else [binary]
        return _runnable(result, framework, cmd, coverage_cmd, coverage_skip_reason)
    return None  # a package.json without tests (a PHP or Python app's front end): next stacks


def _phpunit_major(project_path: Path) -> Optional[int]:
    """Major version of the installed phpunit/phpunit (vendor/composer/installed.json)."""
    data: Any
    try:
        data = json.loads((project_path / "vendor" / "composer" / "installed.json").read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None
    packages = data.get("packages", []) if isinstance(data, dict) else data  # Composer 2 / Composer 1
    for package in packages if isinstance(packages, list) else []:
        if isinstance(package, dict) and package.get("name") == "phpunit/phpunit":
            match = re.match(r"v?(\d+)", str(package.get("version", "")))
            return int(match.group(1)) if match else None
    return None


def _detect_php(project_path: Path, result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    composer_json = project_path / "composer.json"
    configs = ("phpunit.xml", "phpunit.xml.dist", "phpunit.dist.xml")
    has_config = any((project_path / name).is_file() for name in configs)
    if not composer_json.is_file() and not has_config:
        return None
    result["type"] = "php"
    composer = _read_json(composer_json)
    deps: Dict[str, Any] = {}
    for section in ("require", "require-dev"):
        if isinstance(composer.get(section), dict):
            deps.update(composer[section])
    config = composer.get("config") if isinstance(composer.get("config"), dict) else {}
    bin_dir = str(config.get("bin-dir") or "vendor/bin").strip("/\\") or "vendor/bin"
    packages = {"pest": "pestphp/pest", "phpunit": "phpunit/phpunit"}
    php = which("php")
    for name, package in packages.items():  # Pest first: it runs the PHPUnit tests too
        if (project_path / bin_dir / name).is_file():
            if not php:
                return _not_runnable(result, name, "php not found on PATH")
            return _runnable(result, name, [php, f"{bin_dir}/{name}"])
    declared = [name for name, package in packages.items() if package in deps]
    if declared:
        return _not_runnable(
            result, declared[0], f"{declared[0]} is not installed in {bin_dir} (run composer install first)"
        )
    scripts = composer.get("scripts") if isinstance(composer.get("scripts"), dict) else {}
    if "test" in scripts:
        composer_bin = which("composer")
        if not composer_bin:
            return _not_runnable(result, "composer test", "composer not found on PATH")
        return _runnable(result, "composer test", [composer_bin, "test"])
    global_phpunit = which("phpunit") if has_config else None
    if global_phpunit:
        return _runnable(result, "phpunit", [global_phpunit])
    result["skip_reason"] = "no PHP test runner (Pest or PHPUnit in composer.json, a composer test script)"
    return None


def _python_tests_present(project_path: Path) -> bool:
    """A pytest configuration or a test module: the project's tests are Python."""
    if _pytest_configured(project_path):
        return True
    for folder in (project_path, project_path / "tests", project_path / "test"):
        if folder.is_dir() and (any(folder.glob("test_*.py")) or any(folder.glob("*_test.py"))):
            return True
    return False


def _detect_python(project_path: Path, result: Dict[str, Any], require_tests: bool = False) -> Optional[Dict[str, Any]]:
    if not _python_project(project_path) or (require_tests and not _python_tests_present(project_path)):
        return None
    result["type"] = "python"
    python = project_python(project_path)
    if python_module_available("pytest", python):
        if python_module_available("pytest_cov", python):
            return _runnable(result, "pytest", [python, "-m", "pytest", "-v"],
                             [python, "-m", "pytest", "--cov", "--cov-report=term-missing"])
        return _runnable(result, "pytest", [python, "-m", "pytest", "-v"], None, COVERAGE_PROVIDER_MISSING)
    if _pytest_configured(project_path):
        return _not_runnable(result, "pytest", f"pytest is not installed for {python}")
    return _runnable(result, "unittest", _unittest_command(python, project_path))


def _detect_tool(result: Dict[str, Any], kind: str, framework: str, tool: str, args: List[str],
                 coverage_args: Optional[List[str]] = None) -> Dict[str, Any]:
    result["type"] = kind
    found = which(tool)
    if not found:
        return _not_runnable(result, framework, f"{tool} not found on PATH")
    return _runnable(result, framework, [found, *args], [found, *coverage_args] if coverage_args else None)


def _detect_go(project_path: Path, result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not (project_path / "go.mod").is_file():
        return None
    return _detect_tool(result, "go", "go test", "go", ["test", "./..."], ["test", "-cover", "./..."])


def _detect_rust(project_path: Path, result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not (project_path / "Cargo.toml").is_file():
        return None
    return _detect_tool(result, "rust", "cargo test", "cargo", ["test"])


def _detect_dotnet(project_path: Path, result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    solutions = sorted(p.name for pattern in ("*.sln", "*.slnx") for p in project_path.glob(pattern))
    projects = sorted(p.name for pattern in DOTNET_PROJECTS[2:] for p in project_path.glob(pattern))
    if not solutions and not projects:
        return None
    if len(solutions) > 1 or (not solutions and len(projects) > 1):
        result["type"] = "dotnet"
        return _not_runnable(result, "dotnet test",
                             "several .NET solution or project files at the root: declare the test command (--cmd)")
    return _detect_tool(result, "dotnet", "dotnet test", "dotnet", ["test", *solutions])


def _detect_ruby(project_path: Path, result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    gemfile = project_path / "Gemfile"
    if not gemfile.is_file():
        return None
    result["type"] = "ruby"
    gems = ""
    for name in ("Gemfile", "Gemfile.lock"):
        try:
            gems += (project_path / name).read_text("utf-8", errors="ignore")
        except OSError:
            continue
    if (project_path / ".rspec").is_file() or re.search(r"\brspec\b", gems):
        bundle = which("bundle")
        if not bundle:
            return _not_runnable(result, "rspec", "bundle not found on PATH")
        return _runnable(result, "rspec", [bundle, "exec", "rspec"])
    if (project_path / "bin" / "rails").is_file() and (project_path / "test").is_dir():
        ruby = which("ruby")
        if not ruby:
            return _not_runnable(result, "rails test", "ruby not found on PATH")
        return _runnable(result, "rails test", [ruby, "bin/rails", "test"])
    result["skip_reason"] = "no Ruby test runner (rspec in the Gemfile, or bin/rails with a test folder)"
    return None


def _detect_jvm(project_path: Path, result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if (project_path / "pom.xml").is_file():
        result["type"] = "java"
        wrapper = shutil.which("mvnw", path=str(project_path))  # mvnw.cmd on Windows
        if wrapper:
            return _runnable(result, "maven", [wrapper, "-B", "test"])
        return _detect_tool(result, "java", "maven", "mvn", ["-B", "test"])
    gradle = ("build.gradle", "build.gradle.kts", "settings.gradle", "settings.gradle.kts")
    if any((project_path / name).is_file() for name in gradle):
        result["type"] = "java"
        return _not_runnable(result, "gradle", "Gradle prints no test result by default: declare a test command "
                             "whose output shows the results (--cmd)")
    return None


def detect_test_framework(project_path: Path) -> Dict[str, Any]:
    """Detect the test command. ``cmd`` is None and ``skip_reason`` set when it cannot run.

    ``coverage_cmd`` is None when coverage cannot be collected; ``coverage_skip_reason``
    then says why. The stacks are tried in order; a stack whose manifest exists but whose
    tests cannot be found lets the next one try (a Laravel ``package.json`` without a test
    script, a Python helper ``requirements.txt`` in a Go project). Python claims the project
    early only when it has Python tests or a pytest configuration; otherwise it comes last,
    with unittest discovery as the fallback.
    """
    result = _empty_result()
    detectors = (
        _detect_node, _detect_php, lambda path, found: _detect_python(path, found, require_tests=True),
        _detect_go, _detect_rust, _detect_dotnet, _detect_ruby, _detect_jvm, _detect_python,
    )
    for detector in detectors:
        found = detector(project_path, result)
        if found is not None:
            return found
    return result


# --------------------------------------------------------------------------
# Declared command (--cmd)
# --------------------------------------------------------------------------

def parse_command(text: str) -> Tuple[Dict[str, str], List[str]]:
    """Split a declared test command into (environment, argv). ValueError when unusable.

    Quotes group words; on Windows a backslash is a path separator, not an escape. Leading
    ``NAME=value`` words become environment variables. Shell operators are refused: the
    command runs without a shell.
    """
    lexer = shlex.shlex(text, posix=True, punctuation_chars=";&|<>()")
    lexer.whitespace_split = True
    if os.name == "nt":
        lexer.escape = ""
    try:
        words = list(lexer)
    except ValueError as exc:  # unbalanced quotes
        raise ValueError(f"cannot parse the test command: {exc}") from None
    operators = [word for word in words if SHELL_OPERATOR.match(word)]
    if operators:
        raise ValueError(
            f"shell operators are not supported ({' '.join(operators)}): the command runs without a shell; "
            "put the steps in a project script (npm, composer, make) and declare that"
        )
    env: Dict[str, str] = {}
    while words and ENV_ASSIGNMENT.match(words[0]):
        name, _, value = words.pop(0).partition("=")
        env[name] = value
    if not words:
        raise ValueError("the test command is empty")
    return env, words


def resolve_executable(project_path: Path, name: str) -> Optional[str]:
    """Path of the command's executable: a path is taken relative to the project, a bare
    name is looked up on PATH, then in node_modules/.bin and vendor/bin of the project."""
    if "/" in name or "\\" in name:
        candidate = Path(name) if Path(name).is_absolute() else project_path / name
        return shutil.which(str(candidate)) or (str(candidate) if candidate.is_file() else None)
    found = which(name) or local_bin(project_path, name)
    if found:
        return found
    vendor_bin = project_path / "vendor" / "bin"
    return shutil.which(name, path=str(vendor_bin)) if vendor_bin.is_dir() else None


def _framework_of(argv: Sequence[str]) -> Optional[str]:
    """Known runner named in a declared command (exit 5 of pytest/unittest means no tests)."""
    names = [Path(word).stem.lower() for word in argv]
    for known in ("pytest", "unittest", "vitest", "jest", "pest", "phpunit", "rspec"):
        if known in names:
            return known
    return None


def declared_command(project_path: Path, text: str) -> Dict[str, Any]:
    """The detection result for ``--cmd``. ValueError when the command cannot be parsed."""
    env, argv = parse_command(text)
    result = _empty_result()
    result.update({"type": "declared", "framework": _framework_of(argv), "env": env,
                   "coverage_skip_reason": COVERAGE_DECLARED, "declared": True})
    executable = resolve_executable(project_path, argv[0])
    if not executable:
        return _not_runnable(result, result["framework"], f"command not found: {argv[0]}")
    result["cmd"] = [executable, *argv[1:]]
    result["skip_reason"] = None
    return result


def scoped_command(cmd: List[str], framework: Optional[str], paths: Sequence[str],
                   project_path: Optional[Path] = None) -> Optional[List[str]]:
    """``cmd`` restricted to the test files ``paths``, or None when the runner cannot take files.

    ``npm test`` passes the files after ``--`` only when the framework is known (vitest, jest,
    or a script that is only ``node --test`` plus flags): an arbitrary test script may ignore
    or misread them.
    """
    if framework in ("vitest", "node --test", "pytest", "pest", "rspec", "rails test"):
        extra = list(paths)
    elif framework == "jest":
        extra = ["--runTestsByPath", *paths]
    elif framework == "phpunit":
        major = _phpunit_major(project_path) if project_path else None
        if len(paths) > 1 and (major is None or major < 10):  # PHPUnit 9 takes one test file
            return None
        extra = list(paths)
    elif framework == "unittest":
        return [cmd[0], "-m", "unittest", "-v", *paths]  # file paths replace discovery
    elif framework == "go test":
        folders = {Path(path).parent.as_posix() for path in paths}  # go test takes packages
        packages = sorted("." if folder == "." else f"./{folder}" for folder in folders)
        return [word for word in cmd if word != "./..."] + packages
    else:
        return None
    if len(cmd) == 2 and cmd[1] == "test":  # npm test
        return [*cmd, "--", *extra]
    return [*cmd, *extra]


def fill_paths(cmd: List[str], paths: Sequence[str]) -> List[str]:
    """A declared command with its ``{paths}`` token replaced by ``paths`` (removed without)."""
    filled: List[str] = []
    for word in cmd:
        filled.extend(paths if word == PATHS_TOKEN else [word])
    return filled


def resolve_paths(project_path: Path, paths: Sequence[str]) -> Tuple[List[str], List[str]]:
    """Project-relative POSIX paths and the list of invalid entries (missing or outside)."""
    relative: List[str] = []
    invalid: List[str] = []
    for raw in paths:
        candidate = Path(raw)
        full = (candidate if candidate.is_absolute() else project_path / candidate).resolve()
        try:
            rel = full.relative_to(project_path)
        except ValueError:
            invalid.append(f"{raw} (outside the project)")
            continue
        if not full.exists():
            invalid.append(f"{raw} (not found)")
            continue
        relative.append(rel.as_posix())
    return relative, invalid


# --------------------------------------------------------------------------
# Reading the test output
# --------------------------------------------------------------------------

_UNITTEST_RAN = re.compile(r"^Ran (\d+) tests? in ", re.MULTILINE)
_UNITTEST_RESULT = re.compile(r"^(?:OK|FAILED)(?: \(([^)\n]*)\))?[ \t]*$", re.MULTILINE)
# Vitest and Jest print a file/suite summary ("Test Files  3 passed", "Test Suites: 3 passed")
# before the test summary ("Tests  22 passed (22)", "Tests: 20 passed, 22 total"): count tests.
_TESTS_LINE = re.compile(r"^[ \t]*Tests:?[ \t]+(\S[^\n]*)$", re.MULTILINE)
# node --test summary: "ℹ tests 2" (spec reporter) or "# tests 2" (TAP reporter).
_NODE_TEST = re.compile(
    r"^[ \t]*[^\sA-Za-z0-9]{1,2}[ \t]+(tests|pass|fail|cancelled|skipped|todo)[ \t]+(\d+)[ \t]*$", re.MULTILINE
)
_PYTEST_SUMMARY = re.compile(
    r"^(?:=+ )?((?:\d+ [a-z]+(?:, )?)+) in \d+(?:\.\d+)?s(?: \([\d:]+\))?(?: =+)?[ \t]*$", re.MULTILINE
)
_PYTEST_NOTHING = re.compile(r"^(?:=+ )?no tests ran in \d", re.MULTILINE)
_MOCHA = re.compile(r"^[ \t]*(\d+) (passing|failing|pending)\b", re.MULTILINE)
# PHPUnit: "OK (5 tests, 10 assertions)", or "Tests: 5, Assertions: 9, Failures: 1, Skipped: 1."
_PHPUNIT_OK = re.compile(r"^OK \((\d+) tests?, \d+ assertions?\)", re.MULTILINE)
_PHPUNIT_TOTALS = re.compile(r"^Tests: (\d+), Assertions: \d+((?:, [A-Z][A-Za-z ]*: \d+)*)\.?[ \t]*$", re.MULTILINE)
_RSPEC = re.compile(r"^(\d+) examples?, (\d+) failures?(?:, (\d+) pending)?", re.MULTILINE)
_MINITEST = re.compile(r"^(\d+) runs, \d+ assertions, (\d+) failures, (\d+) errors, (\d+) skips", re.MULTILINE)
_CARGO = re.compile(r"^test result: \w+\. (\d+) passed; (\d+) failed;(?: (\d+) ignored;)?", re.MULTILINE)  # one line per test binary
# Maven Surefire: the per-class lines end with "Time elapsed"; the per-module totals do not.
_SUREFIRE = re.compile(
    r"^(?:\[\w+\] )?Tests run: (\d+), Failures: (\d+), Errors: (\d+), Skipped: (\d+)[ \t]*$", re.MULTILINE
)
_DOTNET_SUMMARY = re.compile(
    r"Test summary: total: (\d+)[,;] failed: (\d+)[,;] succeeded: (\d+)(?:[,;] skipped: (\d+))?", re.IGNORECASE
)
_DOTNET_PROJECT = re.compile(r"(?:Passed|Failed)!\s+[-–]\s+Failed:\s+(\d+),\s+Passed:\s+(\d+),\s+Skipped:\s+(\d+),\s+Total:\s+(\d+)")
_GENERIC = re.compile(r"\b(\d+)\s+(?:tests?\s+)?(passed|failed)\b")  # case-sensitive: "test_2 PASSED" is a test name
_NO_TEST_FILES = re.compile(
    r"No test files found|No tests found, exiting with code|^No tests executed!", re.IGNORECASE | re.MULTILINE
)
_NPM_ECHO = re.compile(r"^> [^\n]*$", re.MULTILINE)  # npm prints the script it runs: not a test result
_TEST_EVIDENCE = (
    re.compile(r"\b[1-9]\d*\s+(?:\w+\s+){0,2}(?:pass|passed|passing|succeeded|successful)\b", re.IGNORECASE),
    re.compile(r"\b[1-9]\d*\s+(?:tests?|specs?|examples?|assertions?|scenarios?|test cases?)\b", re.IGNORECASE),
    re.compile(r"\b(?:passed|total|tests):\s*[1-9]\d*\b", re.IGNORECASE),  # dotnet, uvu, PHPUnit
    re.compile(r"\bExecuted\s+[1-9]\d*\s+of\b"),                 # karma
    re.compile(r"\bTests run:\s*[1-9]\d*\b"),                    # JUnit, Maven Surefire
    re.compile(r"^ok\s+\d+\b", re.MULTILINE),                    # TAP: "ok 1 - adds"
    re.compile(r"^ok\s+\S+\s+\(?\d[\d.]*m?s\)?", re.MULTILINE),  # go test: "ok  pkg  0.012s"
    re.compile(r"^[ \t]*(?:---[ \t]+)?PASS\b", re.MULTILINE),    # jest "PASS src/a.test.js", go "--- PASS:"
    # Check marks of spec reporters; a build tool's "✓ 34 modules transformed" or "✓ built in 1s" is not a test.
    re.compile(r"^[ \t]*[✓✔√][ \t]+(?!(?i:\d+\s+modules?\b|built\b|compiled\b|done\b))\S", re.MULTILINE),
)
# Failures reported in the output, whatever the summary the parser picked. A command that exits 0
# while one of these lines is present (a wrapper that loses an exit code, two suites where the last
# one is green) is FAIL: an observed failure always wins.
_FAILURE_SIGNALS = (
    re.compile(r"^FAILED \((?:[a-z ]+=\d+(?:, )?)+\)[ \t]*$", re.MULTILINE),                 # unittest
    re.compile(r"^(?:=+ )?(?:\d+ [a-z]+, )*[1-9]\d* (?:failed|errors?)\b[^\n]* in \d", re.MULTILINE),  # pytest
    re.compile(r"^[ \t]*Tests:?[ \t]+[^\n]*\b[1-9]\d* failed\b", re.MULTILINE),               # jest, vitest
    re.compile(r"^[ \t]*[^\sA-Za-z0-9]{1,2}[ \t]+(?:fail|cancelled)[ \t]+[1-9]\d*[ \t]*$", re.MULTILINE),  # node --test
    re.compile(r"^[ \t]*[1-9]\d* failing\b", re.MULTILINE),                                     # mocha
    re.compile(r"^(?:FAILURES|ERRORS)!$", re.MULTILINE),                                         # PHPUnit
    re.compile(r"^Tests: \d+, Assertions: \d+, [^\n]*\b(?:Failures|Errors): [1-9]", re.MULTILINE),  # PHPUnit
    re.compile(r"^\d+ examples?, [1-9]\d* failures?", re.MULTILINE),                             # RSpec
    re.compile(r"^\d+ runs, \d+ assertions, (?:[1-9]\d* failures|\d+ failures, [1-9]\d* errors)", re.MULTILINE),  # minitest
    re.compile(r"^test result: FAILED\.", re.MULTILINE),                                         # cargo
    re.compile(r"^(?:\[\w+\] )?Tests run: \d+, (?:Failures: [1-9]|Failures: \d+, Errors: [1-9])", re.MULTILINE),  # Surefire
    re.compile(r"Test summary: total: \d+[,;] failed: [1-9]", re.IGNORECASE),                    # dotnet
    re.compile(r"\bFailed!\s+[-–]\s+Failed:\s+[1-9]"),                                           # dotnet (per project)
    re.compile(r"^not ok \d+\b(?![^\n]*#\s*(?i:todo|skip))", re.MULTILINE),                     # TAP
    re.compile(r"^(?:--- FAIL:|FAIL\s+\S)", re.MULTILINE),                                       # go test, jest file
)
# npm announces each lifecycle script it runs ("> app@1.0.0 pretest", then "> node build.js").
_NPM_LIFECYCLE = re.compile(r"^> \S+ ((?:pre|post)?test)(?:\s.*)?$")


def _last(pattern: "re.Pattern[str]", text: str) -> Optional["re.Match[str]"]:
    found = None
    for found in pattern.finditer(text):
        pass
    return found


def _count(word: str, text: str) -> int:
    match = re.search(r"(\d+)\s+" + word + r"\b", text)
    return int(match.group(1)) if match else 0


def _parse_counts(output: str, result: Dict[str, Any]) -> bool:
    """Fill ``tests_run``/``tests_passed``/``tests_failed``/``tests_skipped`` from the summary.

    Returns True when a summary was recognised (then ``tests_run`` 0 really means "no test
    ran"), False when the format is unknown (the counts stay 0). ``tests_skipped`` counts the
    tests the runner reported as skipped, pending, ignored, incomplete or todo: they ran
    nothing, so they are never counted as passed.

    An output may hold several summaries of the same runner (several unittest starts, a
    wrapper script that runs one suite after another): the unittest, pytest, jest/vitest,
    cargo, Maven Surefire and per-project dotnet summaries are added up, so a failure
    reported before a later green summary is never lost.
    """
    output = strip_ansi(output)
    passed = failed = run = skipped = 0

    rans = list(_UNITTEST_RAN.finditer(output))
    if rans:  # unittest: one summary per run (several starts, a wrapper that runs several suites)
        outcomes = list(_UNITTEST_RESULT.finditer(output))
        numbers: Dict[str, int] = {}
        for index, ran in enumerate(rans):
            run += int(ran.group(1))
            end = rans[index + 1].start() if index + 1 < len(rans) else len(output)
            outcome = next((m for m in outcomes if ran.end() <= m.start() < end), None)  # its OK/FAILED line
            for key, value in re.findall(r"([a-z ]+)=(\d+)", outcome.group(1) if outcome and outcome.group(1) else ""):
                numbers[key.strip()] = numbers.get(key.strip(), 0) + int(value)
        failed = numbers.get("failures", 0) + numbers.get("errors", 0) + numbers.get("unexpected successes", 0)
        skipped = numbers.get("skipped", 0)
        passed = max(run - failed - skipped - numbers.get("expected failures", 0), 0)
    else:
        tests_lines = [m.group(1) for m in _TESTS_LINE.finditer(output) if re.search(r"\d+\s+(?:passed|failed|total|skipped|todo)\b", m.group(1))]
        node = {m.group(1): int(m.group(2)) for m in _NODE_TEST.finditer(output)}
        pytest_summaries = [m.group(1) for m in _PYTEST_SUMMARY.finditer(output)]  # one per session
        mocha = {m.group(2): int(m.group(1)) for m in _MOCHA.finditer(output)}
        if tests_lines:  # jest, vitest: one summary per run, added up
            for details in tests_lines:
                line_passed, line_failed = _count("passed", details), _count("failed", details)
                total = re.search(r"(\d+)\s+total\b", details)
                passed, failed = passed + line_passed, failed + line_failed
                skipped += _count("skipped", details) + _count("todo", details)
                run += int(total.group(1)) if total else line_passed + line_failed
        elif "tests" in node:  # node --test (spec and TAP reporters)
            run, passed = node["tests"], node.get("pass", 0)
            failed = node.get("fail", 0) + node.get("cancelled", 0)
            skipped = node.get("skipped", 0) + node.get("todo", 0)
        elif pytest_summaries:  # one summary line per pytest session, added up
            for details in pytest_summaries:
                passed += _count("passed", details)
                failed += _count("failed", details) + _count("errors?", details)
                skipped += _count("skipped", details)
            run = passed + failed
        elif _PYTEST_NOTHING.search(output):
            pass  # recognised: zero tests
        elif "passing" in mocha:
            passed, failed, skipped = mocha["passing"], mocha.get("failing", 0), mocha.get("pending", 0)
            run = passed + failed
        elif _PHPUNIT_OK.search(output) or _PHPUNIT_TOTALS.search(output):
            # One summary per run ("OK (...)" or the totals line), added up: a red run followed
            # by a green one (composer test running two suites) is still red.
            for ok in _PHPUNIT_OK.finditer(output):
                run, passed = run + int(ok.group(1)), passed + int(ok.group(1))
            for totals in _PHPUNIT_TOTALS.finditer(output):
                numbers = {key.strip().lower(): int(value) for key, value in re.findall(r"([A-Za-z ]+): (\d+)", totals.group(2))}
                line_failed = numbers.get("failures", 0) + numbers.get("errors", 0)
                line_skipped = numbers.get("skipped", 0) + numbers.get("incomplete", 0)
                run, failed, skipped = run + int(totals.group(1)), failed + line_failed, skipped + line_skipped
                passed += max(int(totals.group(1)) - line_failed - line_skipped, 0)
        elif _RSPEC.search(output):  # one summary per run, added up
            for rspec in _RSPEC.finditer(output):
                line_run, line_failed, line_skipped = int(rspec.group(1)), int(rspec.group(2)), int(rspec.group(3) or 0)
                run, failed, skipped = run + line_run, failed + line_failed, skipped + line_skipped
                passed += max(line_run - line_failed - line_skipped, 0)
        elif _MINITEST.search(output):  # one summary per run, added up
            for minitest in _MINITEST.finditer(output):
                line_run = int(minitest.group(1))
                line_failed, line_skipped = int(minitest.group(2)) + int(minitest.group(3)), int(minitest.group(4))
                run, failed, skipped = run + line_run, failed + line_failed, skipped + line_skipped
                passed += max(line_run - line_failed - line_skipped, 0)
        elif _CARGO.search(output):  # unit, integration and doc tests: one summary each
            for match in _CARGO.finditer(output):
                passed, failed = passed + int(match.group(1)), failed + int(match.group(2))
                skipped += int(match.group(3) or 0)
            run = passed + failed
        elif _SUREFIRE.search(output):  # one total per Maven module
            for match in _SUREFIRE.finditer(output):
                run += int(match.group(1))
                failed += int(match.group(2)) + int(match.group(3))
                skipped += int(match.group(4))
            passed = max(run - failed - skipped, 0)
        elif _last(_DOTNET_SUMMARY, output):
            summary = _last(_DOTNET_SUMMARY, output)
            run, failed, passed = (int(summary.group(n)) for n in (1, 2, 3))  # type: ignore[union-attr]
            skipped = int(summary.group(4) or 0)  # type: ignore[union-attr]
        elif _DOTNET_PROJECT.search(output):  # one line per test project
            for match in _DOTNET_PROJECT.finditer(output):
                failed, passed, run = failed + int(match.group(1)), passed + int(match.group(2)), run + int(match.group(4))
                skipped += int(match.group(3))
        else:
            generic = {m.group(2): int(m.group(1)) for m in _GENERIC.finditer(output)}  # the last one wins
            if not generic:
                return False
            passed, failed = generic.get("passed", 0), generic.get("failed", 0)
            run = passed + failed

    result["tests_run"], result["tests_passed"], result["tests_failed"] = run, passed, failed
    result["tests_skipped"] = skipped
    return True


def _without_npm_hooks(output: str) -> str:
    """``output`` without what npm's ``pretest`` and ``posttest`` scripts printed: a build or a
    lint run there is not a test, and its "✓ 34 modules transformed" is no test evidence."""
    kept: List[str] = []
    in_hook = False
    for line in output.split("\n"):
        stage = _NPM_LIFECYCLE.match(line)
        if stage:
            in_hook = stage.group(1) != "test"
        if not in_hook:
            kept.append(line)
    return "\n".join(kept)


def has_test_evidence(output: str) -> bool:
    """True when the output of an unrecognised runner still shows that tests were executed
    (by the test script itself: npm's pretest and posttest output does not count)."""
    text = _NPM_ECHO.sub("", _without_npm_hooks(strip_ansi(output)))
    return any(pattern.search(text) for pattern in _TEST_EVIDENCE)


def failure_signal(output: str) -> Optional[str]:
    """The first line of the output that reports a failed test (any known runner), or None."""
    text = strip_ansi(output)
    found = [match for pattern in _FAILURE_SIGNALS for match in [pattern.search(text)] if match]
    if not found:
        return None
    first = min(found, key=lambda match: match.start())
    start = text.rfind("\n", 0, first.start()) + 1
    end = text.find("\n", first.start())
    return text[start:end if end != -1 else len(text)].strip()


def run_tests(cmd: List[str], cwd: Path, timeout: Optional[float] = None,
              framework: Optional[str] = None, env: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Run tests and return results. ``status`` is passed, failed, skipped or timeout.

    ``env`` holds extra environment variables (the ``NAME=value`` words of a declared command).

    ``output`` is the full combined stdout and stderr, in the order the runner wrote it;
    ``error`` is the reason of a skipped, failed or timed-out run.
    """
    limit = TIMEOUT_SECONDS if timeout is None else timeout
    result: Dict[str, Any] = {
        "status": "failed",
        "output": "",
        "error": "",
        "exit_code": None,
        "timed_out": False,
        "counts_parsed": False,
        "duration_seconds": 0.0,
        "tests_run": 0,
        "tests_passed": 0,
        "tests_failed": 0,
        "tests_skipped": 0,
    }
    started = time.monotonic()
    try:
        proc = run_external(cmd, cwd=cwd, timeout=limit, env={**RUNNER_ENV, **(env or {})}, merge_stderr=True)
    except FileNotFoundError:
        result["status"] = "skipped"
        result["error"] = f"command not found: {cmd[0]}"
        return result
    except OSError as exc:
        result["status"] = "skipped"
        result["error"] = f"could not start {cmd[0]}: {exc}"
        return result
    result["duration_seconds"] = round(time.monotonic() - started, 1)

    combined = (proc.stdout or "") + (("\n" + proc.stderr) if proc.stderr else "")
    result["output"] = combined
    result["exit_code"] = proc.returncode
    result["counts_parsed"] = _parse_counts(combined, result)
    if proc.timed_out:
        result["status"] = "timeout"
        result["timed_out"] = True
        result["error"] = (
            f"timed out after {limit:g}s and the process tree was killed "
            "(watch mode, a prompt, or a suite slower than the limit: see --timeout)"
        )
    elif proc.returncode == 0:
        signal = failure_signal(combined)
        if result["counts_parsed"] and result["tests_failed"] > 0:
            # The summary shows failed tests although the command exited 0 (a wrapper script that
            # loses the exit code): the observed failures decide.
            result["status"] = "failed"
            result["error"] = f"{result['tests_failed']} failed test(s) in the summary although the command exited 0"
        elif signal:
            # A failure the parsed summary does not count (another runner's summary, a red suite
            # before a green one): the observed failure decides.
            result["status"] = "failed"
            result["error"] = f"the output reports a failure although the command exited 0: {signal[:200]}"
        elif result["counts_parsed"] and result["tests_passed"] == 0 and result["tests_skipped"] > 0:
            # Every test that ran was skipped (pending, ignored, todo): nothing was verified.
            result["status"] = "skipped"
            result["error"] = f"all tests were skipped ({result['tests_skipped']} skipped, 0 passed)"
        elif result["counts_parsed"] and result["tests_run"] == 0:
            # e.g. `node --test` without test files, unittest before 3.12: nothing was verified.
            result["status"] = "skipped"
            result["error"] = "no tests found"
        elif result["counts_parsed"] or has_test_evidence(combined):
            result["status"] = "passed"
        else:
            result["status"] = "skipped"
            # PHPUnit exits 0 with "No tests executed!"
            result["error"] = "no tests found" if _NO_TEST_FILES.search(strip_ansi(combined)) else NO_TEST_RESULT
    elif framework in PYTHON_FRAMEWORKS and proc.returncode in NO_TESTS_EXIT_CODES and result["tests_failed"] == 0:
        result["status"] = "skipped"
        result["error"] = "no tests found"
    elif result["tests_run"] == 0 and _NO_TEST_FILES.search(strip_ansi(combined)):
        # vitest and jest exit 1 when they find no test file: nothing was verified.
        result["status"] = "skipped"
        result["error"] = "no tests found"
    else:
        result["status"] = "failed"
        result["error"] = f"exit code {proc.returncode}"
    return result


def _positive_seconds(value: str) -> float:
    """A finite time limit greater than 0: ``nan``, ``inf`` and overflowing values such as
    ``1e999`` (which float() turns into ``inf``) are a usage error before any process starts."""
    try:
        seconds = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a number: {value}") from None
    if not math.isfinite(seconds):
        raise argparse.ArgumentTypeError(f"the time limit must be a finite number of seconds: {value}")
    if seconds <= 0:
        raise argparse.ArgumentTypeError("the time limit must be greater than 0")
    return seconds


def _write_log(path: Path, text: str) -> Optional[str]:
    """Write the full output; return an error message instead of raising."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    except OSError as exc:
        return str(exc)
    return None


def main(argv: Optional[Sequence[str]] = None) -> int:
    utf8_stdio()
    parser = argparse.ArgumentParser(description="Run the project's test suite")
    parser.add_argument("project", nargs="?", default=".")
    parser.add_argument(
        "--cmd", metavar="COMMAND",
        help="The project's test command (any test suite) instead of detection; a {paths} word marks where "
             "--paths files go. No shell: leading NAME=value words set variables, operators are refused",
    )
    parser.add_argument("--coverage", action="store_true", help="Run with coverage when supported")
    parser.add_argument(
        "--timeout", type=_positive_seconds, default=None, metavar="SECONDS",
        help=f"Time limit of the test command (default {TIMEOUT_SECONDS}); the process tree is killed when it expires",
    )
    parser.add_argument("--log", type=Path, metavar="FILE", help="Write the full combined test output to FILE")
    parser.add_argument(
        "--paths", nargs="+", metavar="FILE",
        help="Run only these test files (relative to the project); runners that cannot take files run the whole suite",
    )
    args = parser.parse_args(argv)
    timeout = TIMEOUT_SECONDS if args.timeout is None else args.timeout

    project_path = Path(args.project).resolve()
    if not project_path.is_dir():
        print(json.dumps({"error": f"Directory not found: {project_path}"}))
        return EXIT_USAGE
    paths: List[str] = []
    if args.paths:
        paths, invalid = resolve_paths(project_path, args.paths)
        if invalid:
            print(json.dumps({"error": "invalid --paths: " + "; ".join(invalid)}))
            return EXIT_USAGE
    if args.cmd is not None:
        try:
            parse_command(args.cmd)
        except ValueError as exc:
            print(json.dumps({"error": f"invalid --cmd: {exc}"}))
            return EXIT_USAGE

    print(f"\n{'=' * 60}")
    print("[TEST RUNNER] Unified Test Execution")
    print(f"{'=' * 60}")
    print(f"Project: {project_path}")
    print(f"Coverage: {'enabled' if args.coverage else 'disabled'}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    info = declared_command(project_path, args.cmd) if args.cmd is not None else detect_test_framework(project_path)
    declared = bool(info.get("declared"))
    print(f"Command source: {'declared (--cmd)' if declared else 'detected'}")
    print(f"Type: {info['type']}")
    print(f"Framework: {info['framework']}")
    print("-" * 60)

    output: Dict[str, Any] = {
        "script": "test_runner",
        "project": str(project_path),
        "command_source": "declared" if declared else "detected",
        "type": info["type"],
        "framework": info["framework"],
    }

    if not info["cmd"]:
        reason = info["skip_reason"] or "no test command"
        print(f"SKIPPED ({reason})")
        output.update({"status": "skipped", "timed_out": False, "reason": reason})
        print(json.dumps(output, indent=2))
        return EXIT_SKIPPED

    cmd = info["cmd"]
    coverage = "not requested"
    if args.coverage and info["coverage_cmd"]:
        cmd, coverage = info["coverage_cmd"], "collected"
    elif args.coverage:
        coverage = f"skipped ({info['coverage_skip_reason']})"
    scope = "full suite"
    paths_ignored: Optional[str] = None
    if declared:
        if paths and PATHS_TOKEN not in cmd:
            paths_ignored = NO_PATHS_TOKEN
            scope = f"full suite ({paths_ignored})"
        elif paths:
            scope = f"paths ({len(paths)})"
        cmd = fill_paths(cmd, paths)
    elif paths:
        scoped = scoped_command(cmd, info["framework"], paths, project_path)
        if scoped:
            cmd, scope = scoped, f"paths ({len(paths)})"
        else:
            paths_ignored = f"{info['framework'] or 'this test command'} cannot run selected test files"
            scope = f"full suite ({paths_ignored})"
    unsafe = unsafe_batch_argument(cmd) if os.name == "nt" else None
    if unsafe is not None:
        # cmd.exe would expand it even inside quotes: a file name could change the command or its exit code.
        print(json.dumps({"error": f"cannot pass {unsafe!r} to {Path(cmd[0]).name}: cmd.exe expands % ! \" "
                                   "and line breaks even inside quotes; rename the file or declare a command "
                                   "that is not a .cmd/.bat"}))
        return EXIT_USAGE
    print(f"Scope: {scope}")
    env_words = [f"{name}={value}" for name, value in (info.get("env") or {}).items()]
    shown = [UNITTEST_MULTI_LABEL if word == UNITTEST_MULTI else word for word in cmd]
    print(f"Running: {' '.join([*env_words, *shown])}")
    print(f"Time limit: {timeout:g}s")
    if coverage.startswith("skipped"):
        # The suite still runs: a missing coverage tool must not turn passing tests into FAIL.
        print(f"SKIPPED ({info['coverage_skip_reason']})")
    print("-" * 60)

    result = run_tests(cmd, project_path, timeout=timeout, framework=info["framework"], env=info.get("env"))
    lines = strip_ansi(result["output"]).rstrip("\n").split("\n") if result["output"].strip() else []
    if len(lines) > TAIL_LINES:
        print(f"... ({len(lines) - TAIL_LINES} earlier lines omitted; --log FILE keeps the full output)")
    for line in lines[-TAIL_LINES:]:
        print(line)

    log_path: Optional[Path] = args.log.resolve() if args.log else None
    log_error = _write_log(log_path, result["output"]) if log_path else None

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    if result["status"] == "passed":
        print("[PASS] All tests passed")
    elif result["status"] == "skipped":
        print(f"SKIPPED ({result['error']})")
    elif result["status"] == "timeout":
        print(f"[TIMEOUT] Test command {result['error']}")
    else:
        print(f"[FAIL] Some tests failed ({result['error']})")

    if result["tests_run"] > 0 or result["tests_skipped"] > 0:
        skipped = f", {result['tests_skipped']} skipped" if result["tests_skipped"] else ""
        print(
            f"Tests: {result['tests_run']} total, {result['tests_passed']} passed, "
            f"{result['tests_failed']} failed{skipped}"
        )
    if log_path:
        print(f"Log: could not write {log_path}: {log_error}" if log_error else f"Log: {log_path}")

    output.update({
        "command": cmd,
        "status": result["status"],
        "timed_out": result["timed_out"],
        "exit_code": result["exit_code"],
        "duration_seconds": result["duration_seconds"],
        "tests_run": result["tests_run"],
        "tests_passed": result["tests_passed"],
        "tests_failed": result["tests_failed"],
        "tests_skipped": result["tests_skipped"],
        "counts_parsed": result["counts_parsed"],
        "coverage": coverage,
        "scope": "paths" if scope.startswith("paths") else "full suite",
    })
    if paths:
        output["paths"] = paths
    if paths_ignored:
        output["paths_ignored"] = paths_ignored
    if result["status"] != "passed":
        output["reason"] = result["error"]
    if log_path and not log_error:
        output["log"] = str(log_path)
    print("\n" + json.dumps(output, indent=2))
    return {"passed": EXIT_PASS, "skipped": EXIT_SKIPPED}.get(result["status"], EXIT_FAIL)


if __name__ == "__main__":
    raise SystemExit(main())
