import json

import pytest

from cdk_ssm_secret_checker.config import load_config
from cdk_ssm_secret_checker.rules import DEFAULT_RULES


def write_config(tmp_path, data):
    (tmp_path / ".cssc.json").write_text(json.dumps(data))


def test_defaults_without_file(tmp_path):
    config = load_config(tmp_path)
    assert config.enabled == DEFAULT_RULES
    assert config.exclude == []


def test_enable_optional_rule(tmp_path):
    write_config(tmp_path, {"enable": ["R006"]})
    assert "R006" in load_config(tmp_path).enabled


def test_disable_rule(tmp_path):
    write_config(tmp_path, {"disable": ["R005"]})
    assert "R005" not in load_config(tmp_path).enabled


def test_cli_overrides_win(tmp_path):
    write_config(tmp_path, {"enable": ["R006"]})
    config = load_config(tmp_path, enable=["R006"], disable=["R001"])
    assert "R006" in config.enabled
    assert "R001" not in config.enabled


def test_exclude_globs(tmp_path):
    write_config(tmp_path, {"exclude": ["tests/fixtures/*"]})
    config = load_config(tmp_path, extra_exclude=["vendored/*"])
    assert config.is_excluded("tests/fixtures/bad-stack.ts")
    assert config.is_excluded("vendored/lib.ts")
    assert not config.is_excluded("src/stack.ts")


def test_unknown_rule_rejected(tmp_path):
    write_config(tmp_path, {"enable": ["R999"]})
    with pytest.raises(ValueError, match="R999"):
        load_config(tmp_path)
