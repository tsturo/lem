"""Frontmatter + section parser (role files, output files).

Duplicate H2 headings: last-wins. A collision in a real role file is a bug,
but the parser should not crash on it.
"""

from __future__ import annotations

from pathlib import Path
from typing import NamedTuple, cast

import yaml


class FrontmatterError(ValueError):
    """Base for frontmatter parsing failures."""

    def __init__(self, message: str, line: int) -> None:
        super().__init__(message)
        self.line = line


class MalformedYAML(FrontmatterError):
    """YAML inside the frontmatter block failed to parse."""


class UnterminatedFrontmatter(FrontmatterError):
    """Opening --- was found but no closing --- before EOF."""


class ParsedDocument(NamedTuple):
    frontmatter: dict[str, object]
    body: str
    sections: dict[str, str]


def parse(text: str) -> ParsedDocument:
    """Parse markdown text with optional YAML frontmatter."""
    lines = text.splitlines(keepends=True)
    frontmatter, body_start = _extract_frontmatter(lines)
    body = "".join(lines[body_start:])
    sections = _extract_sections(body)
    return ParsedDocument(frontmatter=frontmatter, body=body, sections=sections)


def parse_file(path: Path) -> ParsedDocument:
    """Parse a markdown file. Includes path in error messages."""
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{path}: not valid UTF-8") from exc
    try:
        return parse(text)
    except FrontmatterError as exc:
        raise type(exc)(f"{path.name}: {exc}", exc.line) from exc


def _extract_frontmatter(lines: list[str]) -> tuple[dict[str, object], int]:
    if not lines or lines[0].rstrip("\n\r") != "---":
        return {}, 0

    for i, line in enumerate(lines[1:], start=1):
        if line.rstrip("\n\r") == "---":
            raw = "".join(lines[1:i])
            parsed = _parse_yaml_block(raw, fence_line=i + 1)
            body_start = i + 1
            if body_start < len(lines) and lines[body_start] == "\n":
                body_start += 1
            return parsed, body_start

    # No closing fence: treat the entire remainder as YAML frontmatter (no body).
    # This is the synthesizer's natural output shape — pure structured data,
    # no narrative section. Strict-fence enforcement was causing crashes when
    # Opus omitted the trailing ---.
    raw = "".join(lines[1:])
    parsed = _parse_yaml_block(raw, fence_line=len(lines))
    return parsed, len(lines)


def _parse_yaml_block(raw: str, fence_line: int) -> dict[str, object]:
    try:
        result = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        line = fence_line
        if isinstance(exc, yaml.MarkedYAMLError) and exc.problem_mark is not None:
            line = exc.problem_mark.line + 1
        raise MalformedYAML(str(exc), line=line) from exc

    if result is None:
        return {}
    if not isinstance(result, dict):
        raise MalformedYAML(
            f"frontmatter must be a YAML mapping, got {type(result).__name__}",
            line=fence_line,
        )
    if not all(isinstance(k, str) for k in result):
        raise MalformedYAML("frontmatter keys must be strings", line=fence_line)
    return cast("dict[str, object]", result)


def _extract_sections(body: str) -> dict[str, str]:
    lines = body.splitlines(keepends=True)
    sections: dict[str, str] = {}
    in_fence = False
    current_heading: str | None = None
    current_lines: list[str] = []

    for line in lines:
        stripped = line.rstrip("\n\r")
        # Fence markers may be indented per CommonMark; H2 must start at column 0.
        if stripped.lstrip(" ").startswith("```"):
            in_fence = not in_fence
            if current_heading is not None:
                current_lines.append(line)
            continue

        if not in_fence and stripped.startswith("## "):
            if current_heading is not None:
                sections[current_heading] = _join_section(current_lines)
            current_heading = stripped[3:].strip()
            current_lines = []
        elif current_heading is not None:
            current_lines.append(line)

    if current_heading is not None:
        sections[current_heading] = _join_section(current_lines)

    return sections


def _join_section(lines: list[str]) -> str:
    text = "".join(lines)
    return text.strip("\n")
