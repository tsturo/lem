"""Tests for specialist + process role files (Tasks 7.2 + 7.3)."""

from pathlib import Path

import pytest

from lem.schema.parser import ParsedDocument, parse_file

REPO = Path(__file__).parent.parent.parent
SPECIALIST_DIR = REPO / "profiles" / "app-idea" / "roles"
PROCESS_DIR = REPO / "process_roles"

SPECIALIST_FILES = ["architect.md", "designer.md", "market.md"]
PROCESS_FILES = [
    "jtbd-extractor.md",
    "frame-shifter.md",
    "disagreement-detector.md",
    "branch-skeptic.md",
    "pruner.md",
    "distiller.md",
    "cross-skeptic.md",
    "kill-case-skeptic.md",
    "synthesizer.md",
]


def _parse(path: Path) -> ParsedDocument:
    return parse_file(path)


def _required_frontmatter_keys(doc: ParsedDocument) -> set[str]:
    schema = doc.frontmatter.get("output_schema")
    if not isinstance(schema, dict):
        return set()
    rf = schema.get("required_frontmatter")
    if isinstance(rf, dict):
        return {k for k in rf if isinstance(k, str)}
    if isinstance(rf, list):
        return {k for k in rf if isinstance(k, str)}
    return set()


def _required_sections(doc: ParsedDocument) -> list[str]:
    schema = doc.frontmatter.get("output_schema")
    if not isinstance(schema, dict):
        return []
    rs = schema.get("required_sections")
    if isinstance(rs, list):
        return [s for s in rs if isinstance(s, str)]
    return []


@pytest.mark.parametrize("filename", SPECIALIST_FILES)
def test_specialist_role_parses(filename: str) -> None:
    doc = _parse(SPECIALIST_DIR / filename)
    assert doc.frontmatter
    assert doc.body.strip()


@pytest.mark.parametrize("filename", SPECIALIST_FILES)
def test_specialist_required_frontmatter_keys(filename: str) -> None:
    doc = _parse(SPECIALIST_DIR / filename)
    for key in ("name", "model", "worker", "phase", "output_cap", "timeout_s"):
        assert key in doc.frontmatter, f"{filename}: missing {key}"


@pytest.mark.parametrize("filename", SPECIALIST_FILES)
def test_specialist_required_sections_nonempty(filename: str) -> None:
    doc = _parse(SPECIALIST_DIR / filename)
    sections = _required_sections(doc)
    assert sections, f"{filename}: required_sections empty"
    for s in sections:
        assert isinstance(s, str) and s.strip()


@pytest.mark.parametrize("filename", SPECIALIST_FILES)
def test_specialist_has_frame_engagement(filename: str) -> None:
    doc = _parse(SPECIALIST_DIR / filename)
    assert "Frame engagement" in _required_sections(doc)


def test_architect_designer_frontmatter_disjoint() -> None:
    architect = _required_frontmatter_keys(_parse(SPECIALIST_DIR / "architect.md"))
    designer = _required_frontmatter_keys(_parse(SPECIALIST_DIR / "designer.md"))
    assert architect & designer == set()


def test_market_required_frontmatter_seven_keys() -> None:
    keys = _required_frontmatter_keys(_parse(SPECIALIST_DIR / "market.md"))
    expected = {
        "saturation",
        "direct_competitors",
        "closest_analogue",
        "genuine_differentiator",
        "business_model",
        "customer_development_signal",
        "target_user_acuteness",
    }
    assert keys == expected


def test_market_has_web_tools() -> None:
    doc = _parse(SPECIALIST_DIR / "market.md")
    tools = doc.frontmatter.get("tools")
    assert isinstance(tools, list)
    assert "WebFetch" in tools
    assert "WebSearch" in tools


@pytest.mark.parametrize("filename", PROCESS_FILES)
def test_process_role_parses(filename: str) -> None:
    doc = _parse(PROCESS_DIR / filename)
    assert doc.frontmatter
    assert doc.body.strip()


@pytest.mark.parametrize("filename", PROCESS_FILES)
def test_process_role_has_required_frontmatter(filename: str) -> None:
    doc = _parse(PROCESS_DIR / filename)
    for key in ("name", "model", "worker", "phase", "output_cap", "timeout_s"):
        assert key in doc.frontmatter, f"{filename}: missing {key}"


def test_frame_shifter_body_has_prompt_fragment_placeholder() -> None:
    doc = _parse(PROCESS_DIR / "frame-shifter.md")
    assert "{{prompt_fragment}}" in doc.body


def test_kill_case_skeptic_requires_assumptions_and_conflicts() -> None:
    doc = _parse(PROCESS_DIR / "kill-case-skeptic.md")
    keys = _required_frontmatter_keys(doc)
    assert "assumptions_leveraged" in keys
    assert "conflicts_leveraged" in keys


def test_synthesizer_is_opus_with_high_cap() -> None:
    doc = _parse(PROCESS_DIR / "synthesizer.md")
    assert doc.frontmatter["model"] == "opus"
    cap = doc.frontmatter["output_cap"]
    assert isinstance(cap, int) and cap >= 6000


def test_distiller_is_haiku() -> None:
    doc = _parse(PROCESS_DIR / "distiller.md")
    assert doc.frontmatter["model"] == "haiku"


def test_jtbd_extractor_low_cap() -> None:
    doc = _parse(PROCESS_DIR / "jtbd-extractor.md")
    cap = doc.frontmatter["output_cap"]
    assert isinstance(cap, int) and cap <= 500


def test_app_idea_frame_shifter_fragment_exists() -> None:
    fragment = REPO / "profiles" / "app-idea" / "prompt-fragments" / "frame-shifter.md"
    text = fragment.read_text(encoding="utf-8")
    assert text.strip()
    assert len(text.split()) > 30
