"""Static rules for the SSM + CDK secret-leak pattern.

All rules are stdlib-only and operate on a file path plus (for text rules) the
file's content, so they can run against staged content in a pre-commit hook or
tracked files in CI without touching AWS.

Rules:
    R001  valueFromLookup / StringParameter.fromLookup on a secret-named parameter path
    R002  cdk.context.json containing cached ``ssm:`` keys (hosted-zone keys are fine)
    R003  CDK synth output (cdk.out / *.out) committed to the repo
    R004  SecretValue.unsafePlainText / SecretValue.plainText
    R005  CfnOutput whose value references a secret-named variable
    R006  (off by default) SSM StringParameter construct with a secret-looking name
          — CDK can only create ``Type: String`` parameters, so the value lands in
          plain text in the template and the parameter store

Suppression: a line (or the line directly above it) containing ``cssc:ignore``
suppresses all rules for that line; ``cssc:ignore R001,R004`` suppresses only
the listed rules.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

SECRET_NAME = re.compile(r"key|secret|password|token|credential|priv", re.IGNORECASE)
IGNORE_DIRECTIVE = re.compile(r"cssc:ignore(?:[ \t]+(?P<rules>R\d+(?:[ \t]*,[ \t]*R\d+)*))?")
STRING_LITERAL = re.compile(r"""['"`]([^'"`]+)['"`]""")

DEFAULT_RULES = frozenset({"R001", "R002", "R003", "R004", "R005"})
OPTIONAL_RULES = frozenset({"R006"})
ALL_RULES = DEFAULT_RULES | OPTIONAL_RULES

# How many lines after the construct call a multi-line rule looks through for
# its properties (CfnOutput / StringParameter calls are rarely longer).
CONSTRUCT_WINDOW = 10

# Documentation that *describes* the dangerous patterns is not itself a leak —
# only the path-based rules (R002/R003) apply to these files.
DOC_EXTENSIONS = (".md", ".markdown", ".rst", ".txt", ".adoc")


@dataclass(frozen=True)
class Finding:
    path: str
    line: int  # 1-based
    rule: str
    message: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line} {self.rule} {self.message}"


def _suppressed(lines: list[str], index: int, rule: str) -> bool:
    """True if line ``index`` (0-based) carries or inherits a cssc:ignore for ``rule``."""
    candidates = [lines[index]]
    if index > 0:
        candidates.append(lines[index - 1])
    for text in candidates:
        m = IGNORE_DIRECTIVE.search(text)
        if not m:
            continue
        listed = m.group("rules")
        if listed is None or rule in {r.strip() for r in listed.split(",")}:
            return True
    return False


def _r001(path: str, lines: list[str]) -> list[Finding]:
    findings = []
    for i, line in enumerate(lines):
        if "valueFromLookup" not in line and "StringParameter.fromLookup" not in line:
            continue
        secret_literals = [s for s in STRING_LITERAL.findall(line) if SECRET_NAME.search(s)]
        if not secret_literals:
            continue
        if _suppressed(lines, i, "R001"):
            continue
        findings.append(Finding(
            path, i + 1, "R001",
            f"context lookup of secret-named SSM parameter '{secret_literals[0]}' — "
            "the value will be cached in cdk.context.json in plain text; "
            "use valueForStringParameter (deploy-time ref) or a SecureString instead",
        ))
    return findings


# Hosted-zone lookups also land in cdk.context.json but hold no secrets.
ALLOWED_CONTEXT_PREFIXES = ("hosted-zone:", "availability-zones:", "vpc-provider:", "ami:", "endpoint-service-availability-zones:", "load-balancer:", "security-group:", "key-provider:")


def _r002(path: str, lines: list[str]) -> list[Finding]:
    if not path.split("/")[-1] == "cdk.context.json":
        return []
    try:
        data = json.loads("\n".join(lines))
    except (ValueError, TypeError):
        return []
    if not isinstance(data, dict):
        return []
    findings = []
    for key in data:
        if not key.startswith("ssm:"):
            continue
        line_no = next((i + 1 for i, l in enumerate(lines) if key in l), 1)
        findings.append(Finding(
            path, line_no, "R002",
            f"cdk.context.json caches SSM parameter value under '{key}' — "
            "context-cached SSM values are committed in plain text; remove the entry "
            "and stop using valueFromLookup for it",
        ))
    return findings


def _r003(path: str) -> list[Finding]:
    parts = path.split("/")
    for part in parts[:-1]:
        if part == "cdk.out" or part.endswith(".out"):
            return [Finding(
                path, 1, "R003",
                f"CDK synth output committed (inside '{part}/') — synthesised templates "
                "can embed resolved secret values; add it to .gitignore and remove it from the index",
            )]
    return []


def _r004(path: str, lines: list[str]) -> list[Finding]:
    findings = []
    for i, line in enumerate(lines):
        m = re.search(r"SecretValue\s*\.\s*(unsafePlainText|plainText)\s*\(", line)
        if not m:
            continue
        if _suppressed(lines, i, "R004"):
            continue
        findings.append(Finding(
            path, i + 1, "R004",
            f"SecretValue.{m.group(1)}() puts the secret in the synthesised template "
            "in plain text; source it from Secrets Manager or an SSM SecureString",
        ))
    return findings


def _construct_window(lines: list[str], start: int) -> str:
    return "\n".join(lines[start:start + CONSTRUCT_WINDOW])


def _r005(path: str, lines: list[str]) -> list[Finding]:
    findings = []
    for i, line in enumerate(lines):
        if not re.search(r"\bnew\s+CfnOutput\s*\(|\bCfnOutput\s*\(\s*(this|scope|self)\b", line):
            continue
        window = _construct_window(lines, i)
        value = re.search(r"\bvalue\s*[:=]\s*([^,}\n]{1,160})", window)
        if not value or not SECRET_NAME.search(value.group(1)):
            continue
        if _suppressed(lines, i, "R005"):
            continue
        findings.append(Finding(
            path, i + 1, "R005",
            f"CfnOutput value references secret-named expression '{value.group(1).strip()}' — "
            "stack outputs are visible to anyone with DescribeStacks and appear in deploy logs",
        ))
    return findings


def _r006(path: str, lines: list[str]) -> list[Finding]:
    findings = []
    for i, line in enumerate(lines):
        if not re.search(r"\bnew\s+(?:ssm\s*\.\s*)?StringParameter\s*\(", line):
            continue
        window = _construct_window(lines, i)
        name = re.search(r"\bparameterName\s*[:=]\s*['\"`]([^'\"`]+)['\"`]", window)
        if not name or not SECRET_NAME.search(name.group(1)):
            continue
        if _suppressed(lines, i, "R006"):
            continue
        findings.append(Finding(
            path, i + 1, "R006",
            f"StringParameter creates secret-named parameter '{name.group(1)}' as Type: String — "
            "CDK cannot create SecureStrings; create the parameter out-of-band instead",
        ))
    return findings


def scan_file(path: str, text: str | None, enabled: frozenset[str] = DEFAULT_RULES) -> list[Finding]:
    """Run all enabled rules against one file.

    ``path`` is repo-relative with forward slashes. ``text`` may be None for
    path-only scanning (binary or unreadable files) — only R003 applies then.
    """
    findings: list[Finding] = []
    if "R003" in enabled:
        findings.extend(_r003(path))
    if text is None or path.lower().endswith(DOC_EXTENSIONS):
        return findings
    lines = text.splitlines()
    if "R001" in enabled:
        findings.extend(_r001(path, lines))
    if "R002" in enabled:
        findings.extend(_r002(path, lines))
    if "R004" in enabled:
        findings.extend(_r004(path, lines))
    if "R005" in enabled:
        findings.extend(_r005(path, lines))
    if "R006" in enabled:
        findings.extend(_r006(path, lines))
    return findings
