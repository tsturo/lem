"""Tests for src/lem/schema/parser.py."""

from pathlib import Path

import pytest

from lem.schema.parser import (
    MalformedYAML,
    ParsedDocument,
    UnterminatedFrontmatter,
    parse,
    parse_file,
)

FIXTURES = Path(__file__).parent.parent / "fixtures" / "parser"


# ---------------------------------------------------------------------------
# Valid full document
# ---------------------------------------------------------------------------


def test_valid_file_frontmatter() -> None:
    doc = parse_file(FIXTURES / "valid.md")
    assert doc.frontmatter["name"] == "architect"
    assert doc.frontmatter["model"] == "sonnet"
    assert doc.frontmatter["tools"] == ["WebFetch", "Bash"]


def test_valid_file_sections_extracted() -> None:
    doc = parse_file(FIXTURES / "valid.md")
    assert set(doc.sections.keys()) == {"Overview", "Requirements", "Output Format"}


def test_valid_file_section_content() -> None:
    doc = parse_file(FIXTURES / "valid.md")
    assert "evaluates system design" in doc.sections["Overview"]
    assert "Performance" in doc.sections["Requirements"]
    assert "JSON object" in doc.sections["Output Format"]


def test_valid_file_body_contains_intro() -> None:
    doc = parse_file(FIXTURES / "valid.md")
    assert "body content before any section" in doc.body


def test_valid_file_section_content_stripped() -> None:
    doc = parse_file(FIXTURES / "valid.md")
    for content in doc.sections.values():
        assert not content.startswith("\n")
        assert not content.endswith("\n")


# ---------------------------------------------------------------------------
# No frontmatter
# ---------------------------------------------------------------------------


def test_no_frontmatter_returns_empty_dict() -> None:
    doc = parse_file(FIXTURES / "no_frontmatter.md")
    assert doc.frontmatter == {}


def test_no_frontmatter_body_preserved() -> None:
    doc = parse_file(FIXTURES / "no_frontmatter.md")
    assert "Architecture Review" in doc.body


def test_no_frontmatter_sections_extracted() -> None:
    doc = parse_file(FIXTURES / "no_frontmatter.md")
    assert "Overview" in doc.sections


def test_no_frontmatter_inline() -> None:
    doc = parse("""\
# Title

No frontmatter here.

## Section One

Content.
""")
    assert doc.frontmatter == {}
    assert "Section One" in doc.sections


# ---------------------------------------------------------------------------
# Malformed YAML
# ---------------------------------------------------------------------------


def test_malformed_yaml_raises() -> None:
    with pytest.raises(MalformedYAML):
        parse_file(FIXTURES / "malformed_yaml.md")


def test_malformed_yaml_has_line_info() -> None:
    with pytest.raises(MalformedYAML) as exc_info:
        parse_file(FIXTURES / "malformed_yaml.md")
    assert exc_info.value.line is not None


def test_malformed_yaml_inline() -> None:
    with pytest.raises(MalformedYAML):
        parse("---\nbad: {unclosed\n---\nbody\n")


# ---------------------------------------------------------------------------
# Unterminated frontmatter
# ---------------------------------------------------------------------------


def test_unterminated_raises() -> None:
    with pytest.raises(UnterminatedFrontmatter):
        parse_file(FIXTURES / "unterminated.md")


def test_unterminated_inline() -> None:
    with pytest.raises(UnterminatedFrontmatter):
        parse("---\nname: foo\n")


def test_unterminated_has_line_info() -> None:
    with pytest.raises(UnterminatedFrontmatter) as exc_info:
        parse("---\nname: foo\n")
    assert exc_info.value.line is not None


# ---------------------------------------------------------------------------
# H2 inside fenced code block
# ---------------------------------------------------------------------------


def test_h2_in_codeblock_not_a_section() -> None:
    doc = parse_file(FIXTURES / "h2_in_codeblock.md")
    assert "NotASection" not in doc.sections


def test_h2_outside_codeblock_is_a_section() -> None:
    doc = parse_file(FIXTURES / "h2_in_codeblock.md")
    assert "Real Section" in doc.sections
    assert "Another Real Section" in doc.sections


def test_codeblock_content_preserved_in_section() -> None:
    doc = parse_file(FIXTURES / "h2_in_codeblock.md")
    assert "NotASection" in doc.sections["Real Section"]


# ---------------------------------------------------------------------------
# Empty file
# ---------------------------------------------------------------------------


def test_empty_file_returns_empty() -> None:
    doc = parse_file(FIXTURES / "empty.md")
    assert doc.frontmatter == {}
    assert doc.body == ""
    assert doc.sections == {}


def test_empty_string() -> None:
    doc = parse("")
    assert doc.frontmatter == {}
    assert doc.body == ""
    assert doc.sections == {}


# ---------------------------------------------------------------------------
# Frontmatter only (no body)
# ---------------------------------------------------------------------------


def test_frontmatter_only_body_empty() -> None:
    doc = parse_file(FIXTURES / "frontmatter_only.md")
    assert doc.frontmatter["name"] == "minimal"
    assert doc.body == ""
    assert doc.sections == {}


# ---------------------------------------------------------------------------
# Frontmatter that parses to a non-dict
# ---------------------------------------------------------------------------


def test_frontmatter_is_list_raises() -> None:
    with pytest.raises(MalformedYAML):
        parse_file(FIXTURES / "frontmatter_is_list.md")


def test_frontmatter_is_scalar_raises() -> None:
    with pytest.raises(MalformedYAML):
        parse("---\njust a string\n---\nbody\n")


# ---------------------------------------------------------------------------
# ParsedDocument type
# ---------------------------------------------------------------------------


def test_parsed_document_is_namedtuple() -> None:
    doc = parse("body only")
    assert isinstance(doc, ParsedDocument)
    assert hasattr(doc, "frontmatter")
    assert hasattr(doc, "body")
    assert hasattr(doc, "sections")


def test_parsed_document_tuple_access() -> None:
    doc = parse("body only")
    fm, body, sections = doc
    assert fm == {}
    assert body == "body only"
    assert sections == {}


# ---------------------------------------------------------------------------
# Duplicate H2 headings (last-wins)
# ---------------------------------------------------------------------------


def test_duplicate_h2_last_wins() -> None:
    text = "---\n---\n## Alpha\nfirst\n## Alpha\nsecond\n"
    doc = parse(text)
    assert doc.sections["Alpha"] == "second"


# ---------------------------------------------------------------------------
# parse_file includes path in error messages
# ---------------------------------------------------------------------------


def test_parse_file_error_includes_path(tmp_path: Path) -> None:
    bad_file = tmp_path / "broken.md"
    bad_file.write_text("---\nname: foo\n", encoding="utf-8")
    with pytest.raises(UnterminatedFrontmatter, match="broken.md"):
        parse_file(bad_file)


# ---------------------------------------------------------------------------
# Edge: empty frontmatter block (yaml.safe_load → None → {})
# ---------------------------------------------------------------------------


def test_empty_frontmatter_block() -> None:
    doc = parse("---\n---\nbody here\n")
    assert doc.frontmatter == {}
    assert doc.body == "body here\n"


# ---------------------------------------------------------------------------
# Edge: body with no H2 sections
# ---------------------------------------------------------------------------


def test_body_with_no_sections() -> None:
    doc = parse("---\nname: x\n---\nJust a body paragraph.\n")
    assert doc.sections == {}
    assert "Just a body paragraph" in doc.body
