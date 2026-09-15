"""Thin git helpers — no third-party dependencies, so the pre-commit hook
works in any repo without a virtualenv."""

from __future__ import annotations

import subprocess
from pathlib import Path


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True, text=True, check=True,
    ).stdout


def repo_root(start: Path) -> Path:
    return Path(_git(start, "rev-parse", "--show-toplevel").strip())


def staged_files(root: Path) -> list[str]:
    """Repo-relative paths of files added/copied/modified/renamed in the index."""
    out = _git(root, "diff", "--cached", "--name-only", "--diff-filter=ACMR")
    return [line for line in out.splitlines() if line]


def staged_content(root: Path, path: str) -> str | None:
    """Content of ``path`` as staged (not as on disk). None for binary content."""
    try:
        raw = subprocess.run(
            ["git", "-C", str(root), "show", f":{path}"],
            capture_output=True, check=True,
        ).stdout
        return raw.decode("utf-8")
    except (subprocess.CalledProcessError, UnicodeDecodeError):
        return None


def tracked_files(root: Path) -> list[str]:
    return [line for line in _git(root, "ls-files").splitlines() if line]
