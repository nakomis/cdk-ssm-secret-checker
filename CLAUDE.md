# cdk-ssm-secret-checker

Reusable secrets checker for the "SSM as secret store + public repos + CDK" pattern. Origin: PROJ-50, part of the secrets-hardening epic (MULTI-6). Taiga project: CSSC (ID 35).

## Non-negotiable constraints

- **Static and CI modes stay stdlib-only.** The pre-commit hook must work in any repo with bare `python3`, no venv, no pip install. boto3 may only ever be imported inside sweep-mode code paths, lazily.
- **A matched secret value is never printed, logged, or written.** Findings report parameter name, file, line, and a SHA-256 prefix (`sweep.redact()`) only.
- **Sweep mode never runs on GitHub Actions runners** — `assert_safe_environment()` enforces this; do not weaken it.
- **All test fixtures are fully synthetic.** Nothing that ever was a real value, path pattern from a real leak, or real account ID goes in this repo (golden rule; see also the never-publish-financial-statements principle).

## Repository layout

- `src/cdk_ssm_secret_checker/` — `rules.py` (R001–R006 engine), `config.py` (.cssc.json), `gitutil.py`, `sweep.py` (skeleton), `__main__.py` (CLI)
- `tests/` — pytest; fixtures in `tests/fixtures/` are excluded from self-scanning via `.cssc.json`
- `.githooks/pre-commit` — runs the checker on this repo itself (dogfooding), plus drawio→SVG and README TOC

## Testing

```bash
python3 -m pytest -q          # needs pytest (pip install -e '.[dev]')
```

Coverage target 70% minimum. CI (`.github/workflows/ci.yml`) runs the suite on Python 3.9 and 3.12 plus a `--ci` self-scan; `CI Status` is the required check.

## Modes and exit codes

`--pre-commit` (staged files), `--ci` (tracked files, GitHub annotations), `--sweep` (skeleton — full implementation is CSSC-6). Exit codes: 0 clean, 1 findings, 2 usage/config error, 3 sweep not implemented.

## Architecture diagrams

Source: `docs/architecture/cdk-ssm-secret-checker.drawio` — SVG auto-regenerated on commit by `.githooks/pre-commit`.

To activate the hook after cloning:
```bash
git config core.hooksPath .githooks
```
