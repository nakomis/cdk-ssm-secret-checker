"""Value-aware sweep mode — skeleton (full implementation tracked in CSSC-6).

The sweep assumes a dedicated read-only audit role, pulls the actual values of
the configured SSM parameters, and greps repo history, retained GitHub Actions
logs, and deployed web bundles for those values.

Hard safety requirements, enforced here from day one:

* A matched value is NEVER printed, logged, or written anywhere — findings
  report the parameter name, location, and a SHA-256 prefix only.
* The sweep REFUSES to run on GitHub Actions runners. A job holding every
  secret in memory in a public repo is itself an attack surface, and the
  hardened CI roles deny the required reads anyway. Run it from a private
  in-account context or a local scheduled job (launchd).
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from pathlib import Path

SWEEP_CONFIG_FILENAME = ".cssc-sweep.json"

# GitHub Actions log retention is ~90 days; sweeping further back than logs
# exist wastes time and implies coverage the sweep cannot deliver.
DEFAULT_WINDOW_DAYS = 90


class SweepRefused(RuntimeError):
    """Raised when the environment fails a safety rail — do not retry in place."""


@dataclass
class SweepConfig:
    ssm_paths: list[str]
    window_days: int = DEFAULT_WINDOW_DAYS
    repos: list[str] = field(default_factory=list)
    alert: dict = field(default_factory=dict)


def redact(value: str) -> str:
    """The only representation of a secret value that may ever be emitted."""
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def assert_safe_environment(environ: dict[str, str] | None = None) -> None:
    env = os.environ if environ is None else environ
    if env.get("GITHUB_ACTIONS") == "true":
        raise SweepRefused(
            "sweep mode must not run on GitHub Actions runners — "
            "run it from a private in-account context or a local scheduled job"
        )


def load_sweep_config(root: Path) -> SweepConfig:
    config_path = root / SWEEP_CONFIG_FILENAME
    if not config_path.is_file():
        raise FileNotFoundError(f"{SWEEP_CONFIG_FILENAME} not found in {root}")
    raw = json.loads(config_path.read_text())
    if not isinstance(raw, dict):
        raise ValueError(f"{SWEEP_CONFIG_FILENAME} must contain a JSON object")
    ssm_paths = raw.get("ssm_paths")
    if not isinstance(ssm_paths, list) or not ssm_paths:
        raise ValueError("'ssm_paths' must be a non-empty list of SSM parameter paths/prefixes")
    window = raw.get("window_days", DEFAULT_WINDOW_DAYS)
    if not isinstance(window, int) or window <= 0:
        raise ValueError("'window_days' must be a positive integer")
    return SweepConfig(
        ssm_paths=list(ssm_paths),
        window_days=window,
        repos=list(raw.get("repos", [])),
        alert=dict(raw.get("alert", {})),
    )


def run_sweep(root: Path) -> int:
    assert_safe_environment()
    config = load_sweep_config(root)
    print(f"sweep: config OK — {len(config.ssm_paths)} SSM path(s), "
          f"{config.window_days}-day window, {len(config.repos)} repo(s)")
    print("sweep: value-aware sweep not yet implemented (CSSC-6)")
    return 3
