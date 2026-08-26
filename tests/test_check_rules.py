from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import check_rules  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def write(tmp_path: Path, name: str, content: str) -> Path:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


def make_rule(
    rule_id: str = "RL-TEST-01",
    title: str = "A rule",
    impact: str = "bug",
    symptom: str = "something observable goes wrong.",
    avoid: str = "function Bad() {\n  return null\n}",
    prefer: str = "function Good() {\n  return null\n}",
    accept: str | None = "never.",
    extra_blocks: str = "",
    include_avoid: bool = True,
    include_prefer: bool = True,
) -> str:
    lines = [
        f"### {rule_id} - {title}",
        "",
        f"**Impact:** {impact}",
        f"**Symptom:** {symptom}",
        "",
    ]
    if include_avoid:
        lines += ["```jsx", "// avoid", avoid, "```", ""]
    if include_prefer:
        lines += ["```jsx", "// prefer", prefer, "```", ""]
    if extra_blocks:
        lines.append(extra_blocks)
        lines.append("")
    if accept is not None:
        lines.append(f"**Accept when:** {accept}")
        lines.append("")
    return "\n".join(lines)


def test_valid_rule_passes(tmp_path: Path) -> None:
    path = write(tmp_path, "valid.md", make_rule())
    result = check_rules.validate_files([path])
    assert result.errors == []
    assert len(result.rules) == 1
    assert result.by_category() == {"TEST": 1}


def test_good_minimal_fixture_passes() -> None:
    result = check_rules.validate_files([FIXTURES / "good_minimal.md"])
    assert result.errors == []
    assert len(result.rules) == 1


def test_missing_accept_when_reported() -> None:
    result = check_rules.validate_files([FIXTURES / "bad_rule_missing_accept.md"])
    assert result.errors
    assert any("RL-TEST-01" in e and "Accept when" in e for e in result.errors)


def test_duplicate_id_detected() -> None:
    result = check_rules.validate_files([FIXTURES / "bad_rule_duplicate_id.md"])
    assert any("duplicate id" in e and "RL-TEST-01" in e for e in result.errors)


def test_non_contiguous_numbering(tmp_path: Path) -> None:
    content = make_rule(rule_id="RL-FOO-01") + "\n" + make_rule(rule_id="RL-FOO-03")
    path = write(tmp_path, "gap.md", content)
    result = check_rules.validate_files([path])
    assert any("non-contiguous" in e and "RL-FOO" in e for e in result.errors)


def test_missing_impact_field(tmp_path: Path) -> None:
    content = make_rule().replace("**Impact:** bug\n", "")
    path = write(tmp_path, "no_impact.md", content)
    result = check_rules.validate_files([path])
    assert any("missing **Impact:**" in e for e in result.errors)


def test_impact_value_outside_allowed_set(tmp_path: Path) -> None:
    path = write(tmp_path, "bad_impact.md", make_rule(impact="ui"))
    result = check_rules.validate_files([path])
    assert any("impact value 'ui' is not one of" in e for e in result.errors)


def test_missing_symptom_field(tmp_path: Path) -> None:
    content = make_rule().replace("**Symptom:** something observable goes wrong.\n", "")
    path = write(tmp_path, "no_symptom.md", content)
    result = check_rules.validate_files([path])
    assert any("missing **Symptom:**" in e for e in result.errors)


def test_missing_avoid_block(tmp_path: Path) -> None:
    content = make_rule(include_avoid=False)
    path = write(tmp_path, "no_avoid.md", content)
    result = check_rules.validate_files([path])
    assert any("missing a fenced code block starting with // avoid" in e for e in result.errors)


def test_missing_prefer_block(tmp_path: Path) -> None:
    content = make_rule(include_prefer=False)
    path = write(tmp_path, "no_prefer.md", content)
    result = check_rules.validate_files([path])
    assert any("missing a fenced code block starting with // prefer" in e for e in result.errors)


def test_empty_fenced_block(tmp_path: Path) -> None:
    content = make_rule(extra_blocks="```js\n\n```")
    path = write(tmp_path, "empty_block.md", content)
    result = check_rules.validate_files([path])
    assert any("empty fenced code block" in e for e in result.errors)


def test_malformed_rule_id_heading(tmp_path: Path) -> None:
    content = "### RL-foo-1 - a heading with a bad id\n\nbody text\n"
    path = write(tmp_path, "malformed.md", content)
    result = check_rules.validate_files([path])
    assert any("malformed rule heading" in e for e in result.errors)
    assert result.rules == []


def test_deny_list_fires_outside_legacy_constraints(tmp_path: Path) -> None:
    content = make_rule() + "\nuseTransition is not available here.\n"
    path = write(tmp_path, "checklist.md", content)
    result = check_rules.validate_files([path])
    assert any("useTransition" in e and "modern-only term" in e for e in result.errors)


def test_deny_list_quiet_inside_legacy_constraints(tmp_path: Path) -> None:
    content = "# Legacy constraints\n\nuseTransition needs React 18.\n"
    path = write(tmp_path, "legacy-constraints.md", content)
    result = check_rules.validate_files([path])
    assert result.errors == []


def test_min_rules_enforced_via_cli(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = check_rules.main([str(FIXTURES / "good_minimal.md"), "--min-rules", "5"])
    assert exit_code == 1


def test_min_rules_satisfied_via_cli() -> None:
    exit_code = check_rules.main([str(FIXTURES / "good_minimal.md"), "--min-rules", "1"])
    assert exit_code == 0


def test_cli_json_output_structure(capsys: pytest.CaptureFixture[str]) -> None:
    check_rules.main([str(FIXTURES / "good_minimal.md"), "--json"])
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["files"] == 1
    assert payload["rules"] == 1
    assert payload["by_category"] == {"RL-TEST": 1}
    assert payload["errors"] == []


def test_unique_ids_across_multiple_files(tmp_path: Path) -> None:
    a = write(tmp_path, "a.md", make_rule(rule_id="RL-ALPHA-01"))
    b = write(tmp_path, "b.md", make_rule(rule_id="RL-BETA-01"))
    result = check_rules.validate_files([a, b])
    assert result.errors == []
    assert len(result.rules) == 2
    assert result.by_category() == {"ALPHA": 1, "BETA": 1}
