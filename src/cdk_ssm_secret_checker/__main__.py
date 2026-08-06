"""CLI entry point.

    cssc --pre-commit    scan staged files only (fast, no credentials)
    cssc --ci            scan all git-tracked files; GitHub annotations output
    cssc --sweep         value-aware sweep (skeleton — CSSC-6)

Exit codes: 0 clean, 1 findings, 2 usage/config error, 3 sweep not implemented.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .config import load_config
from .gitutil import repo_root, staged_content, staged_files, tracked_files
from .rules import Finding, scan_file
from .sweep import SweepRefused, run_sweep

MAX_FILE_BYTES = 1_000_000


def _read_working_file(root: Path, path: str) -> str | None:
    full = root / path
    try:
        if full.stat().st_size > MAX_FILE_BYTES:
            return None
        return full.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _scan(root: Path, paths: list[str], reader, config) -> list[Finding]:
    findings: list[Finding] = []
    for path in paths:
        if config.is_excluded(path):
            continue
        findings.extend(scan_file(path, reader(root, path), config.enabled))
    return findings


def _report(findings: list[Finding], github_annotations: bool) -> None:
    for f in findings:
        if github_annotations:
            print(f"::error file={f.path},line={f.line},title={f.rule}::{f.message}")
        else:
            print(f)
    noun = "finding" if len(findings) == 1 else "findings"
    print(f"cssc: {len(findings)} {noun}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="cssc",
        description="Secrets checker for the SSM-as-secret-store + public repos + CDK pattern",
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--pre-commit", action="store_true", help="scan staged files only")
    mode.add_argument("--ci", action="store_true", help="scan all tracked files, GitHub annotations output")
    mode.add_argument("--sweep", action="store_true", help="value-aware sweep (requires .cssc-sweep.json)")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="any directory inside the target repo")
    parser.add_argument("--enable", action="append", default=[], metavar="RULE", help="enable an optional rule (e.g. R006)")
    parser.add_argument("--disable", action="append", default=[], metavar="RULE", help="disable a rule")
    parser.add_argument("--exclude", action="append", default=[], metavar="GLOB", help="extra exclude pattern")
    parser.add_argument("--version", action="version", version=f"cssc {__version__}")
    args = parser.parse_args(argv)

    try:
        root = repo_root(args.root)
    except Exception:
        print(f"cssc: {args.root} is not inside a git repository", file=sys.stderr)
        return 2

    if args.sweep:
        try:
            return run_sweep(root)
        except (SweepRefused, FileNotFoundError, ValueError) as exc:
            print(f"cssc: sweep refused: {exc}", file=sys.stderr)
            return 2

    try:
        config = load_config(root, extra_exclude=args.exclude,
                             enable=args.enable, disable=args.disable)
    except ValueError as exc:
        print(f"cssc: bad configuration: {exc}", file=sys.stderr)
        return 2

    if args.pre_commit:
        findings = _scan(root, staged_files(root), staged_content, config)
    else:
        findings = _scan(root, tracked_files(root), _read_working_file, config)

    if findings:
        _report(findings, github_annotations=args.ci)
        return 1
    print("cssc: clean", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
