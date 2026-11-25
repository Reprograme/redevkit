"""A20: the interpreter detection snippets of kit/audits/README.md require Python 3.9+.

Bug: the Bash example accepted any output matching ``^Python 3`` and the PowerShell example
any ``^Python 3``: ``Python 3.8.10`` was chosen although the audits need 3.9 or newer, and
the next candidate was never tried.

The snippets are taken from the README and run against fake ``python``, ``py`` and
``python3`` executables in a temporary PATH (``Python 2.7.18`` on stderr, as Python 2 prints
it; ``Python 3.8.10``; ``Python 3.14.0``). Bash runs on POSIX and with Git Bash on Windows;
PowerShell runs on Windows (fake ``.cmd`` files), in every PowerShell installed: Windows
PowerShell 5.1 (``powershell``) and PowerShell 7 (``pwsh``).

N01: in Windows PowerShell 5.1 ``$p.ExitCode`` stays empty after ``Start-Process -PassThru``
and ``WaitForExit(ms)`` unless the process handle was read first, so ``-eq 0`` was never
true and no Python was found. The test ran only the first PowerShell on PATH (``pwsh``),
which hid it. The snippet now reads ``$p.Handle`` right after starting the process.
"""
from __future__ import annotations

import os
import re
import shutil
import stat
import subprocess
import unittest
from pathlib import Path
from typing import Dict, List, Optional

from audit_helpers import AUDITS_DIR, TempProject

README = (AUDITS_DIR / "README.md").read_text(encoding="utf-8")
SECTION = README.split("## Interpreter detection protocol", 1)[1].split("\n## ", 1)[0]
BASH_SNIPPET = re.search(r"```bash\n(.*?)```", SECTION, re.S).group(1)  # type: ignore[union-attr]
POWERSHELL_SNIPPET = re.search(r"```powershell\n(.*?)```", SECTION, re.S).group(1)  # type: ignore[union-attr]

V27, V38, V314 = "Python 2.7.18", "Python 3.8.10", "Python 3.14.0"
# (python, py, python3) -> the candidate the snippet must choose ("" for none)
CASES = (
    ((V27, V38, V314), "python3"),
    ((V38, V314, V27), "py -3"),
    ((V314, V27, V38), "python"),
    ((V27, V38, V38), ""),
    ((None, "Python 3.9.0", V314), "py -3"),  # python missing from PATH
)


def git_bash() -> Optional[str]:
    if os.name != "nt":
        return shutil.which("bash")
    # Git for Windows: git.exe in <root>/cmd or <root>/mingw64/bin, bash in <root>/bin or
    # <root>/usr/bin. Never shutil.which("bash"): that may be the WSL launcher.
    git = shutil.which("git")
    if not git:
        return None
    for root in list(Path(git).resolve().parents)[:3]:
        for candidate in (root / "bin" / "bash.exe", root / "usr" / "bin" / "bash.exe"):
            if candidate.is_file():
                return str(candidate)
    return None


def powershells() -> List[str]:
    """Every PowerShell on PATH: PowerShell 7 (pwsh) and Windows PowerShell 5.1 (powershell)."""
    if os.name != "nt":
        return []
    found = [shutil.which(name) for name in ("pwsh", "powershell")]
    return [path for path in found if path]


BASH = git_bash()
POWERSHELLS = powershells()


def fakes(versions) -> Dict[str, Optional[str]]:
    return dict(zip(("python", "py", "python3"), versions))


class TestA20Snippets(unittest.TestCase):
    def test_snippets_check_the_minor_version(self):
        self.assertNotIn('grep -q "^Python 3"', BASH_SNIPPET)
        self.assertIn("-ge 9", BASH_SNIPPET)
        self.assertIn("'^Python 3\\.(\\d+)'", POWERSHELL_SNIPPET)
        self.assertIn("-ge 9", POWERSHELL_SNIPPET)
        self.assertIn("$null = $p.Handle", POWERSHELL_SNIPPET)  # N01: ExitCode in Windows PowerShell 5.1

    @unittest.skipUnless(BASH, "no POSIX bash (Git Bash on Windows)")
    def test_bash_snippet(self):
        for versions, expected in CASES:
            with self.subTest(versions=versions), TempProject() as project:
                folder = project.root / "fake"
                folder.mkdir()
                for name, version in fakes(versions).items():
                    path = folder / name
                    if version is None:
                        # "Not installed" for the snippet means the command fails like a missing one
                        # (127). A shadow is needed: the PATH keeps /usr/bin for `timeout`, and a CI
                        # runner (Ubuntu) has a real python there.
                        path.write_text("#!/bin/sh\nexit 127\n", encoding="utf-8", newline="\n")
                    else:
                        stream = " >&2" if version.startswith("Python 2") else ""
                        path.write_text(f'#!/bin/sh\necho "{version}"{stream}\n', encoding="utf-8", newline="\n")
                    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
                script = project.root / "detect.sh"
                script.write_text(
                    'cd "$(dirname "$0")"\nPATH="$PWD/fake:/usr/bin:/bin"\n'
                    'command -v timeout >/dev/null || { echo "NO-TIMEOUT"; exit 0; }\n'
                    + BASH_SNIPPET + 'echo "PY=[$PY]"\n',
                    encoding="utf-8", newline="\n",
                )
                done = subprocess.run([BASH, str(script)], cwd=str(project.root), capture_output=True,
                                      stdin=subprocess.DEVNULL, timeout=120)
                out = done.stdout.decode("utf-8", "replace")
                if "NO-TIMEOUT" in out:
                    self.skipTest("no timeout command (macOS without coreutils)")
                self.assertIn(f"PY=[{expected}]", out, done.stderr.decode("utf-8", "replace"))

    @unittest.skipUnless(POWERSHELLS, "PowerShell on Windows only")
    def test_powershell_snippet(self):
        for shell in POWERSHELLS:
            for versions, expected in CASES:
                with self.subTest(shell=Path(shell).name, versions=versions):
                    self.run_powershell(shell, versions, expected)

    def run_powershell(self, shell: str, versions, expected: str) -> None:
        with TempProject() as project:
            folder = project.root / "fake"
            folder.mkdir()
            for name, version in fakes(versions).items():
                if version is None:
                    continue
                stream = " 1>&2" if version.startswith("Python 2") else ""
                (folder / f"{name}.cmd").write_text(f"@echo {version}{stream}\r\n", encoding="ascii")
            script = project.root / "detect.ps1"
            script.write_text(
                '$env:PATH = "$PSScriptRoot\\fake;$env:SystemRoot\\System32"\n'
                + POWERSHELL_SNIPPET + 'Write-Output "PY=[$PY]"\n',
                encoding="utf-8-sig",
            )
            done = subprocess.run(
                [shell, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(script)],
                cwd=str(project.root), capture_output=True, stdin=subprocess.DEVNULL, timeout=180,
            )
            out = done.stdout.decode("utf-8", "replace")
            self.assertIn(f"PY=[{expected}]", out, done.stderr.decode("utf-8", "replace"))


if __name__ == "__main__":
    unittest.main()
