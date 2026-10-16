"""Regression tests for cross-file version consistency.

Guards the owned-update contract: the product version must agree across every
version-bearing artifact. This caught the drift in the 1.22.0 checkpoint, where
``VERSION`` read ``1.22.0`` but ``pyproject.toml`` / ``frontend/package.json`` /
``frontend/package-lock.json`` still reported ``1.15.0`` and ``README.md`` /
``portfolio.json`` reported ``1.19.0``.
"""
import json
import re
import tomllib
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def _version() -> str:
    return (_ROOT / "VERSION").read_text().strip()


def _pyproject() -> str:
    return tomllib.loads((_ROOT / "pyproject.toml").read_text())["project"]["version"]


def _portfolio() -> str:
    return json.loads((_ROOT / "portfolio.json").read_text())["version"]


def _pkg() -> str:
    return json.loads((_ROOT / "frontend" / "package.json").read_text())["version"]


def _pkglock() -> tuple[str, str]:
    d = json.loads((_ROOT / "frontend" / "package-lock.json").read_text())
    return d["version"], d["packages"][""]["version"]


def test_version_file_is_valid_semver():
    v = _version()
    assert _SEMVER.match(v), f"VERSION is not a valid semver: {v!r}"


def test_version_agrees_across_artifacts():
    v = _version()
    assert _pyproject() == v, f"pyproject.toml={_pyproject()} != VERSION={v}"
    assert _portfolio() == v, f"portfolio.json={_portfolio()} != VERSION={v}"
    assert _pkg() == v, f"package.json={_pkg()} != VERSION={v}"
    root_v, lock_v = _pkglock()
    assert root_v == v, f"package-lock root version={root_v} != VERSION={v}"
    assert lock_v == v, f"package-lock packages[''] version={lock_v} != VERSION={v}"