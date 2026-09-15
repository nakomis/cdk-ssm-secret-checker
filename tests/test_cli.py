"""End-to-end CLI tests against throwaway git repos."""

import json
import subprocess
from pathlib import Path

import pytest

from cdk_ssm_secret_checker.__main__ import main

FIXTURES = Path(__file__).parent / "fixtures"


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path):
    git(tmp_path, "init", "-q")
    git(tmp_path, "config", "user.email", "test@example.test")
    git(tmp_path, "config", "user.name", "Test")
    return tmp_path


def stage(repo: Path, name: str, content: str) -> None:
    target = repo / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)
    git(repo, "add", name)


class TestPreCommit:
    def test_clean_staged_files_pass(self, repo, capsys):
        stage(repo, "lib/stack.ts", (FIXTURES / "good-stack.ts").read_text())
        assert main(["--pre-commit", "--root", str(repo)]) == 0
        assert "clean" in capsys.readouterr().err

    def test_bad_staged_file_blocks(self, repo, capsys):
        stage(repo, "lib/stack.ts", (FIXTURES / "bad-stack.ts").read_text())
        assert main(["--pre-commit", "--root", str(repo)]) == 1
        out = capsys.readouterr().out
        assert "lib/stack.ts" in out
        assert "R001" in out

    def test_unstaged_violation_not_scanned(self, repo):
        stage(repo, "lib/good.ts", (FIXTURES / "good-stack.ts").read_text())
        (repo / "lib" / "bad.ts").write_text((FIXTURES / "bad-stack.ts").read_text())
        assert main(["--pre-commit", "--root", str(repo)]) == 0

    def test_staged_cdk_out_blocks(self, repo):
        stage(repo, "cdk.out/MyStack.template.json", "{}")
        assert main(["--pre-commit", "--root", str(repo)]) == 1


class TestCi:
    def test_scans_committed_violations(self, repo, capsys):
        stage(repo, "lib/stack.ts", (FIXTURES / "bad-stack.ts").read_text())
        git(repo, "commit", "-q", "-m", "sneaky --no-verify commit")
        assert main(["--ci", "--root", str(repo)]) == 1
        assert "::error file=lib/stack.ts" in capsys.readouterr().out

    def test_respects_repo_config(self, repo):
        stage(repo, "vendored/stack.ts", (FIXTURES / "bad-stack.ts").read_text())
        stage(repo, ".cssc.json", json.dumps({"exclude": ["vendored/*"]}))
        git(repo, "commit", "-q", "-m", "vendored code excluded")
        assert main(["--ci", "--root", str(repo)]) == 0


class TestSweep:
    def test_refuses_without_config(self, repo, capsys):
        assert main(["--sweep", "--root", str(repo)]) == 2
        assert "sweep refused" in capsys.readouterr().err

    def test_skeleton_exits_not_implemented(self, repo, capsys, monkeypatch):
        monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
        (repo / ".cssc-sweep.json").write_text(json.dumps({"ssm_paths": ["/example/"]}))
        assert main(["--sweep", "--root", str(repo)]) == 3
        assert "not yet implemented" in capsys.readouterr().out

    def test_refuses_on_actions_runner(self, repo, capsys, monkeypatch):
        monkeypatch.setenv("GITHUB_ACTIONS", "true")
        (repo / ".cssc-sweep.json").write_text(json.dumps({"ssm_paths": ["/example/"]}))
        assert main(["--sweep", "--root", str(repo)]) == 2
        assert "GitHub Actions" in capsys.readouterr().err


class TestUsage:
    def test_outside_git_repo(self, tmp_path):
        assert main(["--ci", "--root", str(tmp_path)]) == 2

    def test_unknown_rule(self, repo):
        assert main(["--ci", "--root", str(repo), "--enable", "R999"]) == 2
