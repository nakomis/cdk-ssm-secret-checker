import json

import pytest

from cdk_ssm_secret_checker.sweep import (
    SweepRefused,
    assert_safe_environment,
    load_sweep_config,
    redact,
)


class TestSafetyRails:
    def test_refuses_github_actions(self):
        with pytest.raises(SweepRefused, match="GitHub Actions"):
            assert_safe_environment({"GITHUB_ACTIONS": "true"})

    def test_allows_local(self):
        assert_safe_environment({})

    def test_redact_never_contains_value(self):
        value = "synthetic-secret-value-for-tests"
        redacted = redact(value)
        assert value not in redacted
        assert redacted.startswith("sha256:")
        assert redacted == redact(value)  # stable, so findings are comparable


class TestSweepConfig:
    def test_valid_config(self, tmp_path):
        (tmp_path / ".cssc-sweep.json").write_text(json.dumps({
            "ssm_paths": ["/example/service/"],
            "window_days": 30,
            "repos": ["example/repo"],
        }))
        config = load_sweep_config(tmp_path)
        assert config.ssm_paths == ["/example/service/"]
        assert config.window_days == 30

    def test_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_sweep_config(tmp_path)

    def test_empty_paths_rejected(self, tmp_path):
        (tmp_path / ".cssc-sweep.json").write_text(json.dumps({"ssm_paths": []}))
        with pytest.raises(ValueError, match="ssm_paths"):
            load_sweep_config(tmp_path)

    def test_default_window_is_actions_retention(self, tmp_path):
        (tmp_path / ".cssc-sweep.json").write_text(json.dumps({"ssm_paths": ["/x/"]}))
        assert load_sweep_config(tmp_path).window_days == 90
