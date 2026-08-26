from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

HEADING_RE = re.compile(r"^### (RL-([A-Z]+)-(\d{2})) - (.+)$", re.MULTILINE)
LOOSE_HEADING_RE = re.compile(r"^### (.+)$", re.MULTILINE)
IMPACT_RE = re.compile(r"\*\*Impact:\*\*\s*(\S+)")
SYMPTOM_RE = re.compile(r"\*\*Symptom:\*\*\s*(\S.*)")
ACCEPT_RE = re.compile(r"\*\*Accept when:\*\*\s*(\S.*)")
CODE_BLOCK_RE = re.compile(r"```[^\n`]*\n(.*?)```", re.DOTALL)
ID_RE = re.compile(r"^RL-[A-Z]+-\d{2}$")

ALLOWED_IMPACTS = {"bug", "rerender", "bundle", "perf", "maintainability"}

DENY_LIST = (
    "next/",
    "useTransition",
    "useDeferredValue",
    "useEffectEvent",
    "createRoot",
    "Server Component",
    "RSC",
    "app router",
)
DENY_EXEMPT_FILENAME = "legacy-constraints.md"


@dataclass
class Rule:
    rule_id: str
    category: str
    number: int
    title: str
    file: str
    line: int
    body: str


@dataclass
class ValidationResult:
    files: int = 0
    rules: list[Rule] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def by_category(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for rule in self.rules:
            counts[rule.category] = counts.get(rule.category, 0) + 1
        return counts


def line_of(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def extract_rules(text: str, filename: str) -> list[Rule]:
    headings = list(HEADING_RE.finditer(text))
    rules: list[Rule] = []
    for i, match in enumerate(headings):
        rule_id, category, number_str, title = match.groups()
        start = match.end()
        end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
        body = text[start:end]
        rules.append(
            Rule(
                rule_id=rule_id,
                category=category,
                number=int(number_str),
                title=title.strip(),
                file=filename,
                line=line_of(text, match.start()),
                body=body,
            )
        )
    return rules


def code_block_contents(body: str) -> list[str]:
    return [block for block in CODE_BLOCK_RE.findall(body)]


def first_content_line(block: str) -> str:
    for raw_line in block.splitlines():
        stripped = raw_line.strip()
        if stripped:
            return stripped
    return ""


def validate_rule(rule: Rule) -> list[str]:
    errors: list[str] = []
    prefix = f"{rule.file}:{rule.line}: {rule.rule_id}"

    if not ID_RE.match(rule.rule_id):
        errors.append(f"{prefix}: id does not match ^RL-[A-Z]+-\\d{{2}}$")

    impact_match = IMPACT_RE.search(rule.body)
    if impact_match is None:
        errors.append(f"{prefix}: missing **Impact:** field")
    elif impact_match.group(1) not in ALLOWED_IMPACTS:
        errors.append(
            f"{prefix}: impact value '{impact_match.group(1)}' is not one of "
            f"{sorted(ALLOWED_IMPACTS)}"
        )

    symptom_match = SYMPTOM_RE.search(rule.body)
    if symptom_match is None:
        errors.append(f"{prefix}: missing **Symptom:** field")

    accept_match = ACCEPT_RE.search(rule.body)
    if accept_match is None:
        errors.append(f"{prefix}: missing **Accept when:** field")

    blocks = code_block_contents(rule.body)
    has_avoid = False
    has_prefer = False
    for block in blocks:
        if not block.strip():
            errors.append(f"{prefix}: contains an empty fenced code block")
            continue
        first_line = first_content_line(block)
        if first_line == "// avoid":
            has_avoid = True
        elif first_line == "// prefer":
            has_prefer = True

    if not has_avoid:
        errors.append(f"{prefix}: missing a fenced code block starting with // avoid")
    if not has_prefer:
        errors.append(f"{prefix}: missing a fenced code block starting with // prefer")

    return errors


def find_malformed_headings(text: str, filename: str) -> list[str]:
    strict_starts = {match.start() for match in HEADING_RE.finditer(text)}
    errors: list[str] = []
    for match in LOOSE_HEADING_RE.finditer(text):
        if match.start() not in strict_starts:
            errors.append(
                f"{filename}:{line_of(text, match.start())}: malformed rule heading "
                f"'{match.group(1)}' does not match '### RL-<CAT>-<NN> - <title>'"
            )
    return errors


def validate_deny_list(text: str, filename: str) -> list[str]:
    if Path(filename).name == DENY_EXEMPT_FILENAME:
        return []
    errors: list[str] = []
    for term in DENY_LIST:
        if term in text:
            errors.append(
                f"{filename}: contains modern-only term '{term}', which may only "
                f"appear inside {DENY_EXEMPT_FILENAME}"
            )
    return errors


def validate_contiguous_numbering(rules: list[Rule]) -> list[str]:
    errors: list[str] = []
    by_category: dict[str, list[Rule]] = {}
    for rule in rules:
        by_category.setdefault(rule.category, []).append(rule)

    for category, category_rules in sorted(by_category.items()):
        numbers = sorted(r.number for r in category_rules)
        expected = list(range(1, len(numbers) + 1))
        if numbers != expected:
            missing = sorted(set(expected) - set(numbers))
            duplicates = sorted({n for n in numbers if numbers.count(n) > 1})
            detail = []
            if missing:
                detail.append(f"missing {missing}")
            if duplicates:
                detail.append(f"duplicated {duplicates}")
            errors.append(f"category RL-{category}: non-contiguous numbering ({', '.join(detail)})")
    return errors


def validate_unique_ids(rules: list[Rule]) -> list[str]:
    errors: list[str] = []
    seen: dict[str, Rule] = {}
    for rule in rules:
        if rule.rule_id in seen:
            first = seen[rule.rule_id]
            errors.append(
                f"duplicate id {rule.rule_id}: first seen in {first.file}:{first.line}, "
                f"again in {rule.file}:{rule.line}"
            )
        else:
            seen[rule.rule_id] = rule
    return errors


def validate_files(paths: list[Path]) -> ValidationResult:
    result = ValidationResult(files=len(paths))
    errors: list[str] = []

    for path in paths:
        text = path.read_text(encoding="utf-8")
        errors.extend(validate_deny_list(text, str(path)))
        errors.extend(find_malformed_headings(text, str(path)))
        rules = extract_rules(text, str(path))
        result.rules.extend(rules)
        for rule in rules:
            errors.extend(validate_rule(rule))

    errors.extend(validate_unique_ids(result.rules))
    errors.extend(validate_contiguous_numbering(result.rules))

    result.errors = errors
    return result


def render_human(result: ValidationResult, min_rules: int) -> str:
    lines = [
        f"files scanned: {result.files}",
        f"rules found: {len(result.rules)}",
        "by category:",
    ]
    for category, count in sorted(result.by_category().items()):
        lines.append(f"  RL-{category}: {count}")
    if len(result.rules) < min_rules:
        lines.append(f"rule count {len(result.rules)} is below --min-rules {min_rules}")
    if result.errors:
        lines.append("errors:")
        for error in result.errors:
            lines.append(f"  {error}")
    else:
        lines.append("errors: none")
    return "\n".join(lines)


def render_json(result: ValidationResult) -> str:
    payload = {
        "files": result.files,
        "rules": len(result.rules),
        "by_category": {f"RL-{k}": v for k, v in sorted(result.by_category().items())},
        "errors": result.errors,
    }
    return json.dumps(payload)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate the structure of the RL-* rule catalog.")
    parser.add_argument("files", nargs="+", help="markdown rule files to validate")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    parser.add_argument(
        "--min-rules", type=int, default=0, help="fail if fewer than N rules are found"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    paths = [Path(f) for f in args.files]
    result = validate_files(paths)

    if args.json:
        print(render_json(result))
    else:
        print(render_human(result, args.min_rules))

    if result.errors or len(result.rules) < args.min_rules:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
