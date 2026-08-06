from pathlib import Path

import pytest

from cdk_ssm_secret_checker.rules import ALL_RULES, DEFAULT_RULES, scan_file

FIXTURES = Path(__file__).parent / "fixtures"


def scan_fixture(name: str, enabled=DEFAULT_RULES):
    return scan_file(f"tests/fixtures/{name}", (FIXTURES / name).read_text(), enabled)


def rules_hit(findings):
    return sorted({f.rule for f in findings})


class TestBadStack:
    def test_default_rules_fire(self):
        findings = scan_fixture("bad-stack.ts")
        assert rules_hit(findings) == ["R001", "R004", "R005"]
        assert sum(1 for f in findings if f.rule == "R001") == 2

    def test_r006_only_when_enabled(self):
        assert "R006" not in rules_hit(scan_fixture("bad-stack.ts"))
        assert "R006" in rules_hit(scan_fixture("bad-stack.ts", ALL_RULES))

    def test_findings_carry_location(self):
        finding = next(f for f in scan_fixture("bad-stack.ts") if f.rule == "R004")
        assert finding.path == "tests/fixtures/bad-stack.ts"
        assert finding.line > 1
        assert "unsafePlainText" in finding.message


class TestGoodStack:
    def test_clean_even_with_all_rules(self):
        assert scan_fixture("good-stack.ts", ALL_RULES) == []


class TestSuppression:
    def test_ignore_directives(self):
        findings = scan_fixture("suppressed.ts")
        # Only the mismatched directive (R001 listed against an R004 violation) reports
        assert len(findings) == 1
        assert findings[0].rule == "R004"
        assert "also-a-placeholder" in (FIXTURES / "suppressed.ts").read_text().splitlines()[findings[0].line - 1]


class TestContextJson:
    def test_ssm_keys_flagged_hosted_zone_allowed(self):
        findings = scan_fixture("cdk.context.json")
        assert rules_hit(findings) == ["R002"]
        assert len(findings) == 1
        assert "/example/service/api-key" in findings[0].message

    def test_only_applies_to_cdk_context_json(self):
        text = (FIXTURES / "cdk.context.json").read_text()
        assert scan_file("some/other.json", text) == []


class TestDocFiles:
    def test_code_rules_skip_documentation(self):
        # Docs describing the dangerous patterns must not be flagged —
        # this repo's own README tripped R001/R004 before this exemption
        text = (FIXTURES / "bad-stack.ts").read_text()
        assert scan_file("docs/how-not-to-leak.md", text, ALL_RULES) == []

    def test_path_rules_still_apply_to_docs(self):
        assert rules_hit(scan_file("cdk.out/notes.md", None)) == ["R003"]


class TestSynthOutput:
    @pytest.mark.parametrize("path", [
        "cdk.out/MyStack.template.json",
        "infra/cdk.out/manifest.json",
        "cdk-deploy.out/tree.json",
    ])
    def test_out_dirs_flagged(self, path):
        assert rules_hit(scan_file(path, None)) == ["R003"]

    @pytest.mark.parametrize("path", [
        "lib/my-stack.ts",
        "docs/cdk.out.md",
        "shout/template.json",
    ])
    def test_normal_paths_clean(self, path):
        assert scan_file(path, None) == []
