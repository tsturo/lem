"""Tests for src/lem/branch_label.py."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from lem.branch_label import BranchLabelExtractionError, extract_branch_label
from lem.types import WorkerResult


def _make_result(**kwargs: object) -> WorkerResult:
    defaults: dict[str, object] = dict(
        exit_code=0,
        output_path=Path("/tmp/dummy"),
        tokens_in=10,
        tokens_out=5,
        cost_usd=0.0,
        duration_s=0.5,
        stop_reason="end_turn",
        schema_valid=False,
        schema_errors=[],
    )
    defaults.update(kwargs)
    return WorkerResult(**defaults)  # type: ignore[arg-type]


def test_stub_mode_returns_stub_label(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LEM_STUB_MODE", "1")
    assert extract_branch_label("now make it mobile-first with comments and ticket-saving") == "stub-label"


def test_empty_input_raises() -> None:
    with pytest.raises(BranchLabelExtractionError):
        extract_branch_label("")


def test_whitespace_only_input_raises() -> None:
    with pytest.raises(BranchLabelExtractionError):
        extract_branch_label("   \n  ")


def test_timeout_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LEM_STUB_MODE", raising=False)
    timeout_result = _make_result(exit_code=-1, stop_reason="timeout", duration_s=30.0)
    with patch("lem.branch_label.cli_worker.invoke", return_value=timeout_result):
        with pytest.raises(BranchLabelExtractionError):
            extract_branch_label("make it mobile first")


def test_cleanup_whitespace_and_newlines(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LEM_STUB_MODE", raising=False)

    def fake_invoke(inv: object, system_prompt: object, allowed_tools: object) -> WorkerResult:
        from lem.types import WorkerInvocation
        assert isinstance(inv, WorkerInvocation)
        inv.output_path.parent.mkdir(parents=True, exist_ok=True)
        inv.output_path.write_text("  mobile first  \n  with comments  \n", encoding="utf-8")
        return _make_result(output_path=inv.output_path)

    with patch("lem.branch_label.cli_worker.invoke", side_effect=fake_invoke):
        result = extract_branch_label("make it mobile first with comments and more stuff")

    assert result == "mobile-first-with-comments"


def test_garbage_output_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LEM_STUB_MODE", raising=False)

    def fake_invoke(inv: object, system_prompt: object, allowed_tools: object) -> WorkerResult:
        from lem.types import WorkerInvocation
        assert isinstance(inv, WorkerInvocation)
        inv.output_path.parent.mkdir(parents=True, exist_ok=True)
        inv.output_path.write_text("!!!", encoding="utf-8")
        return _make_result(output_path=inv.output_path)

    with patch("lem.branch_label.cli_worker.invoke", side_effect=fake_invoke):
        with pytest.raises(BranchLabelExtractionError):
            extract_branch_label("make it mobile first")
