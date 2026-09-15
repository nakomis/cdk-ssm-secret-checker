"""Repo-level configuration: .cssc.json at the repo root.

Example:

    {
        "exclude": ["tests/fixtures/*", "vendored/*"],
        "enable": ["R006"],
        "disable": []
    }

All fields optional. ``exclude`` patterns are fnmatch globs matched against
repo-relative POSIX paths (note fnmatch's ``*`` matches across ``/``).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path

from .rules import ALL_RULES, DEFAULT_RULES

CONFIG_FILENAME = ".cssc.json"


@dataclass
class Config:
    exclude: list[str] = field(default_factory=list)
    enabled: frozenset[str] = DEFAULT_RULES

    def is_excluded(self, path: str) -> bool:
        return any(fnmatch(path, pattern) for pattern in self.exclude)


def load_config(root: Path, extra_exclude: list[str] | None = None,
                enable: list[str] | None = None, disable: list[str] | None = None) -> Config:
    """Load .cssc.json (if present) and apply CLI overrides on top."""
    raw: dict = {}
    config_path = root / CONFIG_FILENAME
    if config_path.is_file():
        raw = json.loads(config_path.read_text())
        if not isinstance(raw, dict):
            raise ValueError(f"{CONFIG_FILENAME} must contain a JSON object")

    unknown = (set(raw.get("enable", [])) | set(raw.get("disable", []))
               | set(enable or []) | set(disable or [])) - ALL_RULES
    if unknown:
        raise ValueError(f"unknown rule id(s): {', '.join(sorted(unknown))}")

    enabled = set(DEFAULT_RULES)
    enabled |= set(raw.get("enable", []))
    enabled -= set(raw.get("disable", []))
    enabled |= set(enable or [])
    enabled -= set(disable or [])

    return Config(
        exclude=list(raw.get("exclude", [])) + list(extra_exclude or []),
        enabled=frozenset(enabled),
    )
