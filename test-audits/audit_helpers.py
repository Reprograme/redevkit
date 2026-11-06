"""Shared helpers for the audit regression tests.

Run from the repository root:

    python -m unittest discover -s test-audits -v
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Optional, Sequence, Tuple

sys.dont_write_bytecode = True  # never leave __pycache__ inside kit/audits

TESTS_DIR = Path(__file__).resolve().parent
AUDITS_DIR = TESTS_DIR.parent / "kit" / "audits"
FIXTURES_DIR = TESTS_DIR / "fixtures"

_LOADED = {}


def load_audit(name: str):
    """Import ``kit/audits/<name>.py`` by path (no package, no bytecode)."""
    if name in _LOADED:
        return _LOADED[name]
    path = AUDITS_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"redevkit_audit_{name}", path)
    assert spec and spec.loader, f"cannot load {path}"
    module = importlib.util.module_from_spec(spec)
    if str(AUDITS_DIR) not in sys.path:
        sys.path.insert(0, str(AUDITS_DIR))  # orchestrators import validation_runner
    sys.modules[spec.name] = module  # dataclasses resolve annotations through sys.modules
    spec.loader.exec_module(module)
    _LOADED[name] = module
    return module


def run_main(module, argv: Sequence[str]) -> Tuple[int, str]:
    """Call ``module.main(argv)`` and return (exit code, captured stdout)."""
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(io.StringIO()):
        try:
            code = module.main(list(argv))
        except SystemExit as exc:  # argparse errors
            code = exc.code if isinstance(exc.code, int) else 2
    return code, buffer.getvalue()


class TempProject:
    """Context manager: a temp directory, optionally seeded from fixtures/<bug>."""

    def __init__(self, fixture: Optional[str] = None, subdir: str = ""):
        self.fixture = fixture
        self.subdir = subdir
        self._tmp: Optional[tempfile.TemporaryDirectory] = None
        self.root = Path()

    def __enter__(self) -> "TempProject":
        self._tmp = tempfile.TemporaryDirectory(prefix="redevkit-audit-")
        self.root = Path(self._tmp.name) / self.subdir if self.subdir else Path(self._tmp.name)
        self.root.mkdir(parents=True, exist_ok=True)
        if self.fixture:
            shutil.copytree(FIXTURES_DIR / self.fixture, self.root, dirs_exist_ok=True)
        return self

    def __exit__(self, *exc) -> None:
        assert self._tmp is not None
        self._tmp.cleanup()

    def write(self, relative: str, content: str) -> Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path
