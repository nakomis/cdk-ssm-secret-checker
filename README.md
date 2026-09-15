# cdk-ssm-secret-checker — keep SSM-stored secrets out of your public CDK repos

<img src="docs/logo.png" alt="cdk-ssm-secret-checker logo" width="200" align="right"/>

If you store secrets in AWS SSM Parameter Store (because Secrets Manager costs money and you're on a shoestring), keep your infrastructure in CDK, and publish your repos publicly, there is a family of easy mistakes that will quietly commit your secret **values** to the repo. This tool catches them — before commit, in CI, and (eventually) by sweeping for the actual values after the fact.

## Support

If you find this useful, please consider buying me a coffee:

[![Donate with PayPal](https://www.paypalobjects.com/en_GB/i/btn/btn_donate_SM.gif)](https://www.paypal.com/donate?hosted_button_id=Q3BESC73EWVNN&custom=cdk-ssm-secret-checker)

## Table of Contents

<!-- toc -->

- [The problem](#the-problem)
- [One tool, three modes](#one-tool-three-modes)
- [Rules](#rules)
- [Usage](#usage)
- [Configuration](#configuration)
- [Repository Layout](#repository-layout)
- [Architecture Diagrams](#architecture-diagrams)
- [Support](#support)

<!-- tocstop -->

## The problem

CDK's `StringParameter.valueFromLookup()` fetches an SSM parameter at **synth time** and caches the resolved value — in plain text — in `cdk.context.json`, a file the CDK docs tell you to commit. If that parameter held an API key, your key is now in your public repo's history. Similar leaks happen via committed `cdk.out/` synth output, `SecretValue.unsafePlainText()`, and `CfnOutput`s that echo secrets into stack outputs and deploy logs.

## One tool, three modes

| Mode | When | Needs credentials? | What it does |
|------|------|--------------------|--------------|
| `--pre-commit` | Every commit, via git hook | No | Scans **staged** files only; milliseconds; blocks the commit |
| `--ci` | Pull requests / pushes | No | Scans all **tracked** files; GitHub annotations; catches `--no-verify` commits after the event |
| `--sweep` | Scheduled (e.g. weekly) | Yes (read-only audit role) | Pulls the *actual* secret values from SSM and greps repo history, retained Actions logs, and deployed web bundles for them |

Static and CI modes are **stdlib-only Python** — no virtualenv, no dependencies, safe to call from any repo's pre-commit hook.

> **Sweep mode is a skeleton at present**: the CLI, config format, and safety rails exist; the value-aware search is under construction. Two safety properties are non-negotiable and enforced from day one: matched values are never printed (parameter name, location, and SHA-256 prefix only), and the sweep refuses to run on GitHub Actions runners.

## Rules

| Rule | Catches | Default |
|------|---------|---------|
| R001 | `valueFromLookup` / `StringParameter.fromLookup` on a secret-named parameter path (`key\|secret\|password\|token\|credential\|priv`) | on |
| R002 | `cdk.context.json` containing cached `ssm:` entries (hosted-zone and other non-secret context is fine) | on |
| R003 | CDK synth output (`cdk.out/`, `*.out/`) committed to the repo | on |
| R004 | `SecretValue.unsafePlainText()` / `SecretValue.plainText()` | on |
| R005 | `CfnOutput` whose value references a secret-named variable | on |
| R006 | SSM `StringParameter` construct creating a secret-named parameter as `Type: String` (CDK cannot create SecureStrings) | off |

Suppress a finding with a trailing or preceding comment: `// cssc:ignore` (all rules) or `// cssc:ignore R001,R004` (listed rules only).

Documentation files (`.md`, `.rst`, `.txt`, `.adoc`) are exempt from the code-pattern rules — prose that *describes* `valueFromLookup` is not a leak. (This README taught us that by failing its own pre-commit hook.) Path-based rules still apply everywhere.

## Usage

```bash
# In a git hook (.githooks/pre-commit or .git/hooks/pre-commit):
python3 -m cdk_ssm_secret_checker --pre-commit || exit 1

# In CI:
python -m cdk_ssm_secret_checker --ci

# Installed via pip (exposes the `cssc` command):
pip install .
cssc --ci
```

Exit codes: `0` clean, `1` findings, `2` usage/config error, `3` sweep not yet implemented.

## Configuration

Optional `.cssc.json` at the repo root:

```json
{
    "exclude": ["tests/fixtures/*", "vendored/*"],
    "enable": ["R006"],
    "disable": []
}
```

`--enable`, `--disable`, and `--exclude` CLI flags layer on top.

Sweep mode reads `.cssc-sweep.json`:

```json
{
    "ssm_paths": ["/myapp/prod/"],
    "window_days": 90,
    "repos": ["myorg/myrepo"],
    "alert": { "type": "webhook", "url": "https://example.test/hook" }
}
```

`window_days` defaults to 90 because GitHub Actions logs are only retained ~90 days — sweeping further back than the logs exist implies coverage the sweep cannot deliver.

## Repository Layout

- `src/cdk_ssm_secret_checker/` — the tool (stdlib-only for static/CI modes)
- `tests/` — pytest suite; every fixture is fully synthetic
- `docs/architecture/` — architecture diagrams (drawio source, SVG auto-generated on commit)
- `.githooks/` — this repo's own pre-commit hook, which runs the checker on itself

## Architecture Diagrams

`docs/architecture/cdk-ssm-secret-checker.drawio` is the source for the diagrams.
The SVG is auto-regenerated on commit by the pre-commit hook in `.githooks/pre-commit`.

To activate the hook after cloning:

```bash
git config core.hooksPath .githooks
```

## Support

If you find this useful, please consider buying me a coffee:

[![Donate with PayPal](https://www.paypalobjects.com/en_GB/i/btn/btn_donate_SM.gif)](https://www.paypal.com/donate?hosted_button_id=Q3BESC73EWVNN&custom=cdk-ssm-secret-checker)
