"""Output schema validation against role's declared output_schema.

Supported exit_criteria DSL keys (per section):
  min_bullets: int  — at least N lines starting with '- ' or '* '
  min_words:   int  — at least N whitespace-delimited tokens in section text

Any other exit_criteria key produces an 'unsupported exit criterion' error so
role authors catch typos rather than silently skipping checks.
"""

from __future__ import annotations

import re
from typing import NamedTuple

from lem.schema.parser import ParsedDocument

_PLACEHOLDER_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("<TBD>", re.compile(r"<TBD>", re.IGNORECASE)),
    ("<placeholder>", re.compile(r"<placeholder>", re.IGNORECASE)),
    ("[TODO]", re.compile(r"\[TODO\]", re.IGNORECASE)),
    ("<...>", re.compile(r"<\.\.\.>")),
]

_TYPE_MAP: dict[str, type] = {
    "str": str,
    "int": int,
    "bool": bool,
    "list": list,
    "dict": dict,
}


class ValidationResult(NamedTuple):
    valid: bool
    errors: list[str]


def validate(doc: ParsedDocument, schema: dict[str, object]) -> ValidationResult:
    """Validate a parsed document against a role's output_schema."""
    errors: list[str] = []
    errors.extend(_validate_frontmatter(doc.frontmatter, schema))
    errors.extend(_validate_enums(doc.frontmatter, schema))
    errors.extend(_validate_sections(doc.sections, schema))
    errors.extend(_find_placeholders(doc.body))
    return ValidationResult(valid=len(errors) == 0, errors=errors)


def _build_enum_table(schema: dict[str, object]) -> dict[str, list[str]]:
    enums: object = schema.get("enums")
    table: dict[str, list[str]] = {}
    if isinstance(enums, dict):
        for k, v in enums.items():
            if isinstance(k, str) and isinstance(v, list):
                table[k] = [str(item) for item in v]
    return table


def _validate_frontmatter(
    frontmatter: dict[str, object], schema: dict[str, object]
) -> list[str]:
    errors: list[str] = []
    required = schema.get("required_frontmatter")
    if required is None:
        return errors

    if isinstance(required, list):
        for key in required:
            if not isinstance(key, str):
                continue
            if key not in frontmatter:
                errors.append(f"required frontmatter key '{key}' missing")
        return errors

    if not isinstance(required, dict):
        return errors

    enum_table = _build_enum_table(schema)

    for key, type_spec in required.items():
        if not isinstance(key, str):
            continue
        if key not in frontmatter:
            errors.append(f"required frontmatter key '{key}' missing")
            continue
        if not isinstance(type_spec, str):
            continue

        # Per-value enum membership is enforced by _validate_enums; here we only
        # report the schema-author error of declaring `enum` without a table entry.
        if type_spec == "enum":
            if key not in enum_table:
                errors.append(
                    f"frontmatter '{key}' declared as enum but"
                    f" '{key}' not found in enums table"
                )
            continue

        if type_spec in _TYPE_MAP:
            expected_type = _TYPE_MAP[type_spec]
            value = frontmatter[key]
            if not isinstance(value, expected_type):
                actual = type(value).__name__
                errors.append(
                    f"frontmatter '{key}' must be {type_spec}, got {actual}"
                )

    return errors


def _validate_enums(
    frontmatter: dict[str, object], schema: dict[str, object]
) -> list[str]:
    """Enforce the `enums` table independently of `required_frontmatter` form."""
    errors: list[str] = []
    enum_table = _build_enum_table(schema)
    for key, allowed in enum_table.items():
        if key not in frontmatter:
            continue
        value = frontmatter[key]
        if str(value) not in allowed:
            errors.append(
                f"frontmatter '{key}' must be one of {allowed}, got '{value}'"
            )
    return errors


def _validate_sections(
    sections: dict[str, str], schema: dict[str, object]
) -> list[str]:
    errors: list[str] = []

    required_sections: object = schema.get("required_sections")
    section_names: list[str] = []
    if isinstance(required_sections, list):
        section_names = [s for s in required_sections if isinstance(s, str)]

    for name in section_names:
        if name not in sections:
            errors.append(f"section '{name}' missing")
            continue
        if not sections[name].strip():
            errors.append(f"section '{name}' is empty")

    exit_criteria: object = schema.get("exit_criteria")
    if isinstance(exit_criteria, dict):
        for section_name, criteria in exit_criteria.items():
            if not isinstance(section_name, str) or not isinstance(criteria, dict):
                continue
            if section_name not in sections:
                continue
            content = sections[section_name]
            errors.extend(_check_exit_criteria(section_name, content, criteria))

    return errors


def _check_exit_criteria(
    section_name: str, content: str, criteria: dict[str, object]
) -> list[str]:
    errors: list[str] = []
    for key, value in criteria.items():
        if key == "min_bullets":
            if not isinstance(value, int):
                continue
            count = _count_bullets(content)
            if count < value:
                plural = "s" if count != 1 else ""
                errors.append(
                    f"section '{section_name}' has {count} bullet{plural},"
                    f" requires min_bullets={value}"
                )
        elif key == "min_words":
            if not isinstance(value, int):
                continue
            count = len(content.split())
            if count < value:
                plural = "s" if count != 1 else ""
                errors.append(
                    f"section '{section_name}' has {count} word{plural},"
                    f" requires min_words={value}"
                )
        else:
            errors.append(
                f"unsupported exit criterion '{key}' in section '{section_name}'"
            )
    return errors


def _count_bullets(text: str) -> int:
    count = 0
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("- ") or stripped.startswith("* "):
            count += 1
    return count


def _find_placeholders(body: str) -> list[str]:
    errors: list[str] = []
    lines = body.splitlines()
    in_fence = False
    for lineno, line in enumerate(lines, start=1):
        stripped = line.lstrip(" ")
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for label, pattern in _PLACEHOLDER_PATTERNS:
            for match in pattern.finditer(line):
                errors.append(f"placeholder '{match.group()}' found at line {lineno}")
    return errors
