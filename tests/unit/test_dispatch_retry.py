# pyright: strict
"""Tests for workers/dispatch.py retry logic."""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Iterator

import pytest

from lem.types import WorkerInvocation, WorkerResult
from lem.workers.dispatch import dispatch_worker

_SCHEMA: dict[str, object] = {"required_sections": ["Summary"]}

_VALID_OUTPUT = "## Summary\nThis is a summary.\n"
_INVALID_OUTPUT = "No sections here.\n"


def _make_inv(tmp_path: Path, *, extra_context: dict[str, str] | None = None) -> WorkerInvocation:
    return WorkerInvocation(
        role_path=tmp_path / "role.md",
        workspace_path=tmp_path,
        output_path=tmp_path / "output.md",
        allowed_read_paths=[],
        model="sonnet",
        max_output_tokens=1024,
        timeout_s=30,
        extra_context=extra_context or {},
    )


def _make_result(
    tmp_path: Path,
    *,
    exit_code: int = 0,
    stop_reason: str = "end_turn",
    output_content: str | None = None,
) -> WorkerResult:
    output_path = tmp_path / "output.md"
    if output_content is not None:
        output_path.write_text(output_content, encoding="utf-8")
    return WorkerResult(
        exit_code=exit_code,
        output_path=output_path,
        tokens_in=10,
        tokens_out=5,
        cost_usd=0.001,
        duration_s=0.5,
        stop_reason=stop_reason,  # type: ignore[arg-type]
        schema_valid=False,
        schema_errors=[],
    )


def _patch_invoke(
    monkeypatch: pytest.MonkeyPatch,
    results: list[WorkerResult],
) -> list[WorkerInvocation]:
    calls: list[WorkerInvocation] = []
    it: Iterator[WorkerResult] = iter(results)

    def fake_invoke(
        inv: WorkerInvocation, sp: str, tools: list[str]
    ) -> WorkerResult:
        calls.append(inv)
        return next(it)

    monkeypatch.setattr("lem.workers.dispatch.cli_worker.invoke", fake_invoke)
    return calls


# ---------------------------------------------------------------------------
# Happy path — no retry needed
# ---------------------------------------------------------------------------


def test_happy_path_no_schema(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    inv = _make_inv(tmp_path)
    r = _make_result(tmp_path)
    calls = _patch_invoke(monkeypatch, [r])

    result = dispatch_worker(inv, "sys", [])

    assert result.exit_code == 0
    assert len(calls) == 1


def test_happy_path_with_valid_schema(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    inv = _make_inv(tmp_path)
    r = _make_result(tmp_path, output_content=_VALID_OUTPUT)
    calls = _patch_invoke(monkeypatch, [r])

    result = dispatch_worker(inv, "sys", [], output_schema=_SCHEMA)

    assert result.schema_valid is True
    assert result.schema_errors == []
    assert len(calls) == 1


# ---------------------------------------------------------------------------
# Schema invalid → retry once → success
# ---------------------------------------------------------------------------


def test_schema_invalid_retries_once(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    inv = _make_inv(tmp_path)
    r1 = _make_result(tmp_path, output_content=_INVALID_OUTPUT)

    valid_path = tmp_path / "output.md"

    def fake_invoke(inv_arg: WorkerInvocation, sp: str, tools: list[str]) -> WorkerResult:
        fake_invoke.calls.append(inv_arg)  # type: ignore[attr-defined]
        if len(fake_invoke.calls) == 2:  # type: ignore[attr-defined]
            valid_path.write_text(_VALID_OUTPUT, encoding="utf-8")
        return dataclasses.replace(r1, output_path=valid_path)

    fake_invoke.calls: list[WorkerInvocation] = []  # type: ignore[attr-defined]
    monkeypatch.setattr("lem.workers.dispatch.cli_worker.invoke", fake_invoke)

    result = dispatch_worker(inv, "sys", [], output_schema=_SCHEMA)

    assert result.schema_valid is True
    assert result.schema_errors == []
    assert len(fake_invoke.calls) == 2  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Schema invalid → retry → still invalid → failure recorded
# ---------------------------------------------------------------------------


def test_schema_invalid_then_invalid_returns_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inv = _make_inv(tmp_path)
    r = _make_result(tmp_path, output_content=_INVALID_OUTPUT)
    calls = _patch_invoke(monkeypatch, [r, r])

    result = dispatch_worker(inv, "sys", [], output_schema=_SCHEMA)

    assert result.schema_valid is False
    assert len(result.schema_errors) > 0
    assert result.exit_code == 0
    assert len(calls) == 2


# ---------------------------------------------------------------------------
# Auth error (exit 69) — no retry
# ---------------------------------------------------------------------------


def test_auth_error_no_retry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    inv = _make_inv(tmp_path)
    r = _make_result(tmp_path, exit_code=69, stop_reason="error")
    calls = _patch_invoke(monkeypatch, [r])

    result = dispatch_worker(inv, "sys", [], output_schema=_SCHEMA)

    assert result.exit_code == 69
    assert len(calls) == 1


# ---------------------------------------------------------------------------
# Timeout — no retry
# ---------------------------------------------------------------------------


def test_timeout_no_retry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    inv = _make_inv(tmp_path)
    r = _make_result(tmp_path, exit_code=-1, stop_reason="timeout")
    calls = _patch_invoke(monkeypatch, [r])

    result = dispatch_worker(inv, "sys", [], output_schema=_SCHEMA)

    assert result.stop_reason == "timeout"
    assert len(calls) == 1


# ---------------------------------------------------------------------------
# Non-zero exit → retry once → success
# ---------------------------------------------------------------------------


def test_nonzero_exit_retries_once(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    inv = _make_inv(tmp_path)
    r_fail = _make_result(tmp_path, exit_code=1, stop_reason="error")
    r_ok = _make_result(tmp_path, exit_code=0, output_content=_VALID_OUTPUT)
    calls = _patch_invoke(monkeypatch, [r_fail, r_ok])

    result = dispatch_worker(inv, "sys", [])

    assert result.exit_code == 0
    assert len(calls) == 2


# ---------------------------------------------------------------------------
# Continuation prompt contains schema errors
# ---------------------------------------------------------------------------


def test_continuation_prompt_includes_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inv = _make_inv(tmp_path)
    r = _make_result(tmp_path, output_content=_INVALID_OUTPUT)
    captured: list[WorkerInvocation] = []

    def fake_invoke(inv_arg: WorkerInvocation, sp: str, tools: list[str]) -> WorkerResult:
        captured.append(inv_arg)
        return r

    monkeypatch.setattr("lem.workers.dispatch.cli_worker.invoke", fake_invoke)

    dispatch_worker(inv, "sys", [], output_schema=_SCHEMA)

    assert len(captured) == 2
    retry_inv = captured[1]
    assert "schema_errors" in retry_inv.extra_context
    assert "retry_instruction" in retry_inv.extra_context
    assert "Summary" in retry_inv.extra_context["schema_errors"]
