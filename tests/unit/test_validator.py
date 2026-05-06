"""Tests for src/lem/schema/validator.py."""

from pathlib import Path

import pytest

from lem.schema.parser import parse, parse_file
from lem.schema.validator import ValidationResult, validate

FIXTURES = Path(__file__).parent.parent / "fixtures" / "validator"

FULL_SCHEMA: dict[str, object] = {
    "required_frontmatter": {
        "saturation": "enum",
        "direct_competitors": "list",
        "closest_analogue": "str",
        "genuine_differentiator": "str",
    },
    "required_sections": ["TAM", "Competitors", "Saturation", "Differentiator"],
    "enums": {
        "saturation": ["low", "medium", "high", "very-high"],
    },
    "exit_criteria": {
        "Competitors": {"min_bullets": 3},
        "Differentiator": {"min_words": 10},
    },
}


# ---------------------------------------------------------------------------
# ValidationResult type
# ---------------------------------------------------------------------------


def test_validation_result_is_namedtuple() -> None:
    result = ValidationResult(valid=True, errors=[])
    assert isinstance(result, ValidationResult)
    assert result.valid is True
    assert result.errors == []


def test_validation_result_valid_false_has_errors() -> None:
    result = ValidationResult(valid=False, errors=["something wrong"])
    assert result.valid is False
    assert len(result.errors) == 1


# ---------------------------------------------------------------------------
# Valid document passes all checks
# ---------------------------------------------------------------------------


def test_valid_document_passes() -> None:
    doc = parse_file(FIXTURES / "valid.md")
    result = validate(doc, FULL_SCHEMA)
    assert result.valid is True
    assert result.errors == []


# ---------------------------------------------------------------------------
# required_frontmatter — dict form (key → type)
# ---------------------------------------------------------------------------


def test_missing_frontmatter_key_detected() -> None:
    doc = parse_file(FIXTURES / "missing_frontmatter_key.md")
    result = validate(doc, FULL_SCHEMA)
    assert not result.valid
    assert any("genuine_differentiator" in e and "missing" in e for e in result.errors)


def test_wrong_frontmatter_type_list_expected() -> None:
    doc = parse_file(FIXTURES / "multiple_failures.md")
    result = validate(doc, FULL_SCHEMA)
    assert any("direct_competitors" in e and "list" in e for e in result.errors)


def test_wrong_frontmatter_type_str_expected() -> None:
    text = (
        "---\n"
        "saturation: high\n"
        "direct_competitors:\n  - Acme\n"
        "closest_analogue:\n  - not-a-string\n"
        "genuine_differentiator: fine\n"
        "---\n\n"
        "## TAM\n\nLarge market.\n\n"
        "## Competitors\n\n- A\n- B\n- C\n\n"
        "## Saturation\n\nHigh.\n\n"
        "## Differentiator\n\nUnique product offering lower cost and open API.\n"
    )
    doc = parse(text)
    result = validate(doc, FULL_SCHEMA)
    assert any("closest_analogue" in e and "str" in e for e in result.errors)


# ---------------------------------------------------------------------------
# required_frontmatter — list form (keys only, no type check)
# ---------------------------------------------------------------------------


def test_list_form_keys_only_present() -> None:
    schema: dict[str, object] = {
        "required_frontmatter": ["saturation", "direct_competitors"],
    }
    doc = parse("---\nsaturation: high\ndirect_competitors:\n  - Acme\n---\nbody\n")
    result = validate(doc, schema)
    assert result.valid is True


def test_list_form_missing_key_detected() -> None:
    schema: dict[str, object] = {
        "required_frontmatter": ["saturation", "missing_key"],
    }
    doc = parse("---\nsaturation: high\n---\nbody\n")
    result = validate(doc, schema)
    assert not result.valid
    assert any("missing_key" in e and "missing" in e for e in result.errors)


# ---------------------------------------------------------------------------
# required_sections
# ---------------------------------------------------------------------------


def test_missing_section_detected() -> None:
    doc = parse_file(FIXTURES / "missing_section.md")
    result = validate(doc, FULL_SCHEMA)
    assert not result.valid
    assert any("Differentiator" in e and "missing" in e for e in result.errors)


def test_empty_section_detected() -> None:
    doc = parse_file(FIXTURES / "empty_section.md")
    result = validate(doc, FULL_SCHEMA)
    assert not result.valid
    assert any("Saturation" in e and "empty" in e for e in result.errors)


def test_whitespace_only_section_is_empty() -> None:
    text = (
        "---\n"
        "saturation: high\n"
        "direct_competitors:\n  - Acme\n"
        "closest_analogue: Acme\n"
        "genuine_differentiator: Cost\n"
        "---\n\n"
        "## TAM\n\nLarge market.\n\n"
        "## Competitors\n\n- A\n- B\n- C\n\n"
        "## Saturation\n\n   \n\n"
        "## Differentiator\n\nUnique product offering lower cost and open API.\n"
    )
    doc = parse(text)
    result = validate(doc, FULL_SCHEMA)
    assert any("Saturation" in e and "empty" in e for e in result.errors)


# ---------------------------------------------------------------------------
# enums
# ---------------------------------------------------------------------------


def test_enum_violation_detected() -> None:
    doc = parse_file(FIXTURES / "enum_violation.md")
    result = validate(doc, FULL_SCHEMA)
    assert not result.valid
    assert any(
        "saturation" in e and "extreme" in e and "low" in e for e in result.errors
    )


def test_enum_valid_value_passes() -> None:
    text = (
        "---\n"
        "saturation: very-high\n"
        "direct_competitors:\n  - Acme\n"
        "closest_analogue: Acme\n"
        "genuine_differentiator: Cost\n"
        "---\n\n"
        "## TAM\n\nLarge market.\n\n"
        "## Competitors\n\n- A\n- B\n- C\n\n"
        "## Saturation\n\nVery high saturation.\n\n"
        "## Differentiator\n\nOur product is unique due to lower cost open API and superior developer experience.\n"
    )
    doc = parse(text)
    result = validate(doc, FULL_SCHEMA)
    assert result.valid is True


def test_enum_type_missing_from_enums_table_is_schema_error() -> None:
    schema: dict[str, object] = {
        "required_frontmatter": {"saturation": "enum"},
        "required_sections": [],
    }
    doc = parse("---\nsaturation: high\n---\nbody\n")
    result = validate(doc, schema)
    assert not result.valid
    assert any("saturation" in e and "enums" in e for e in result.errors)


# ---------------------------------------------------------------------------
# exit_criteria
# ---------------------------------------------------------------------------


def test_min_bullets_fail() -> None:
    doc = parse_file(FIXTURES / "exit_criteria_min_bullets_fail.md")
    result = validate(doc, FULL_SCHEMA)
    assert not result.valid
    assert any(
        "Competitors" in e and "bullet" in e and "3" in e for e in result.errors
    )


def test_min_bullets_pass() -> None:
    text = (
        "---\n"
        "saturation: high\n"
        "direct_competitors:\n  - Acme\n"
        "closest_analogue: Acme\n"
        "genuine_differentiator: Cost\n"
        "---\n\n"
        "## TAM\n\nLarge market.\n\n"
        "## Competitors\n\n- A\n- B\n- C\n\n"
        "## Saturation\n\nHigh saturation.\n\n"
        "## Differentiator\n\nOur product is unique due to lower cost open API and superior developer experience.\n"
    )
    doc = parse(text)
    result = validate(doc, FULL_SCHEMA)
    assert result.valid is True


def test_min_words_fail() -> None:
    text = (
        "---\n"
        "saturation: high\n"
        "direct_competitors:\n  - Acme\n"
        "closest_analogue: Acme\n"
        "genuine_differentiator: Cost\n"
        "---\n\n"
        "## TAM\n\nLarge market.\n\n"
        "## Competitors\n\n- A\n- B\n- C\n\n"
        "## Saturation\n\nHigh saturation.\n\n"
        "## Differentiator\n\nShort text.\n"
    )
    doc = parse(text)
    result = validate(doc, FULL_SCHEMA)
    assert not result.valid
    assert any("Differentiator" in e and "word" in e and "10" in e for e in result.errors)


def test_unsupported_exit_criterion_emits_error() -> None:
    schema: dict[str, object] = {
        "required_sections": ["Alpha"],
        "exit_criteria": {"Alpha": {"min_named_items": 3}},
    }
    doc = parse(
        "---\n---\n\n## Alpha\n\nSome content here with enough words.\n"
    )
    result = validate(doc, schema)
    assert any(
        "unsupported" in e and "min_named_items" in e and "Alpha" in e
        for e in result.errors
    )


# ---------------------------------------------------------------------------
# placeholder detection
# ---------------------------------------------------------------------------


def test_placeholder_tbd_detected() -> None:
    doc = parse_file(FIXTURES / "placeholder_in_body.md")
    result = validate(doc, FULL_SCHEMA)
    assert not result.valid
    assert any("<TBD>" in e for e in result.errors)


def test_placeholder_todo_detected() -> None:
    doc = parse_file(FIXTURES / "placeholder_in_body.md")
    result = validate(doc, FULL_SCHEMA)
    assert any("[TODO]" in e for e in result.errors)


def test_placeholder_includes_line_number() -> None:
    doc = parse_file(FIXTURES / "placeholder_in_body.md")
    result = validate(doc, FULL_SCHEMA)
    placeholder_errors = [e for e in result.errors if "<TBD>" in e or "[TODO]" in e]
    assert all("line" in e for e in placeholder_errors)


def test_placeholder_in_codeblock_not_detected() -> None:
    doc = parse_file(FIXTURES / "placeholder_in_codeblock.md")
    result = validate(doc, FULL_SCHEMA)
    placeholder_errors = [
        e
        for e in result.errors
        if any(p in e for p in ["<TBD>", "<placeholder>", "[TODO]", "<...>"])
    ]
    assert placeholder_errors == []


def test_placeholder_ellipsis_detected() -> None:
    text = (
        "---\n"
        "saturation: high\n"
        "direct_competitors:\n  - Acme\n"
        "closest_analogue: Acme\n"
        "genuine_differentiator: Cost\n"
        "---\n\n"
        "## TAM\n\nMarket size is <...>.\n\n"
        "## Competitors\n\n- A\n- B\n- C\n\n"
        "## Saturation\n\nHigh saturation.\n\n"
        "## Differentiator\n\nUnique product offering lower cost and open API.\n"
    )
    doc = parse(text)
    result = validate(doc, FULL_SCHEMA)
    assert any("<...>" in e for e in result.errors)


def test_placeholder_case_insensitive() -> None:
    text = (
        "---\n"
        "saturation: high\n"
        "direct_competitors:\n  - Acme\n"
        "closest_analogue: Acme\n"
        "genuine_differentiator: Cost\n"
        "---\n\n"
        "## TAM\n\nMarket size is <tbd>.\n\n"
        "## Competitors\n\n- A\n- B\n- C\n\n"
        "## Saturation\n\nHigh saturation.\n\n"
        "## Differentiator\n\nUnique product offering lower cost and open API.\n"
    )
    doc = parse(text)
    result = validate(doc, FULL_SCHEMA)
    assert any("<tbd>" in e.lower() or "tbd" in e.lower() for e in result.errors)


# ---------------------------------------------------------------------------
# multiple simultaneous failures
# ---------------------------------------------------------------------------


def test_multiple_failures_all_reported() -> None:
    doc = parse_file(FIXTURES / "multiple_failures.md")
    result = validate(doc, FULL_SCHEMA)
    assert not result.valid
    assert len(result.errors) >= 3

    has_missing_key = any("closest_analogue" in e and "missing" in e for e in result.errors)
    has_missing_key2 = any("genuine_differentiator" in e and "missing" in e for e in result.errors)
    has_missing_section = any("Differentiator" in e and "missing" in e for e in result.errors)
    has_enum_violation = any("saturation" in e and "extreme" in e for e in result.errors)
    has_placeholder = any("<TBD>" in e for e in result.errors)
    has_type_error = any("direct_competitors" in e and "list" in e for e in result.errors)

    failure_flags = [
        has_missing_key,
        has_missing_key2,
        has_missing_section,
        has_enum_violation,
        has_placeholder,
        has_type_error,
    ]
    assert all(failure_flags), f"missing failure categories: {failure_flags}"


def test_enums_enforced_with_list_form_required_frontmatter() -> None:
    doc = parse(
        "---\nname: example\nsaturation: extreme\n---\nbody\n"
    )
    schema: dict[str, object] = {
        "required_frontmatter": ["name", "saturation"],
        "enums": {"saturation": ["low", "medium", "high"]},
    }
    result = validate(doc, schema)
    assert not result.valid
    assert any("saturation" in e and "extreme" in e for e in result.errors)


# ---------------------------------------------------------------------------
# edge cases
# ---------------------------------------------------------------------------


def test_empty_schema_always_passes() -> None:
    doc = parse("body text here\n")
    result = validate(doc, {})
    assert result.valid is True


def test_schema_with_no_required_sections_ignores_sections() -> None:
    schema: dict[str, object] = {"required_frontmatter": ["name"]}
    doc = parse("---\nname: test\n---\nbody\n")
    result = validate(doc, schema)
    assert result.valid is True


def test_validate_returns_validation_result_type() -> None:
    doc = parse("body\n")
    result = validate(doc, {})
    assert isinstance(result, ValidationResult)
