"""Tests for synthesizer prompt — round-2+ conditional instruction (LEM-43)."""

from pathlib import Path

REPO = Path(__file__).parent.parent.parent
SYNTHESIZER = REPO / "process_roles" / "synthesizer.md"


def _body() -> str:
    return SYNTHESIZER.read_text(encoding="utf-8")


def test_synthesizer_prompt_contains_round2_conditional() -> None:
    body = _body()
    assert "meta/iteration-context.md" in body
    assert "meta/parent_run_id" in body


def test_synthesizer_round2_block_references_parent_verdict() -> None:
    body = _body()
    assert "parent run" in body or "parent" in body
    assert "verdict" in body


def test_synthesizer_round2_block_references_summary_body() -> None:
    body = _body()
    assert "summary_body" in body


def test_synthesizer_round2_word_limit_mentioned() -> None:
    body = _body()
    assert "80" in body


def test_synthesizer_round2_no_separate_section_instruction() -> None:
    body = _body()
    assert "separate" in body


def test_synthesizer_round1_noop_mentioned() -> None:
    body = _body()
    assert "Round-1" in body or "Round-1 runs" in body or "no iteration context" in body
