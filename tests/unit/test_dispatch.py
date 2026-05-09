# pyright: strict
"""Tests for auth error path in workers/dispatch.py."""

from __future__ import annotations

from pathlib import Path

import pytest

from lem.types import AuthExpired, WorkerInvocation, WorkerResult
from lem.workers.dispatch import dispatch_worker


def _make_inv(tmp_path: Path) -> WorkerInvocation:
    return WorkerInvocation(
        role_path=tmp_path / "role.md",
        workspace_path=tmp_path,
        output_path=tmp_path / "output.md",
        allowed_read_paths=[],
        model="sonnet",
        max_output_tokens=1024,
        timeout_s=30,
        extra_context={},
    )


def _make_result(tmp_path: Path, *, exit_code: int, stop_reason: str = "error") -> WorkerResult:
    return WorkerResult(
        exit_code=exit_code,
        output_path=tmp_path / "output.md",
        tokens_in=0,
        tokens_out=0,
        cost_usd=0.0,
        duration_s=0.1,
        stop_reason=stop_reason,  # type: ignore[arg-type]
        schema_valid=False,
        schema_errors=[],
    )


def test_auth_exit_code_raises_auth_expired(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inv = _make_inv(tmp_path)
    r = _make_result(tmp_path, exit_code=69)
    calls: list[WorkerInvocation] = []

    def fake_invoke(i: WorkerInvocation, sp: str, tools: list[str]) -> WorkerResult:
        calls.append(i)
        return r

    monkeypatch.setattr("lem.workers.dispatch.cli_worker.invoke", fake_invoke)

    with pytest.raises(AuthExpired):
        dispatch_worker(inv, "sys", [])

    assert len(calls) == 1


def test_auth_exit_code_does_not_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Exit 69 must never trigger the non-zero-exit retry path."""
    inv = _make_inv(tmp_path)
    r = _make_result(tmp_path, exit_code=69)
    calls: list[WorkerInvocation] = []

    def fake_invoke(i: WorkerInvocation, sp: str, tools: list[str]) -> WorkerResult:
        calls.append(i)
        return r

    monkeypatch.setattr("lem.workers.dispatch.cli_worker.invoke", fake_invoke)

    with pytest.raises(AuthExpired):
        dispatch_worker(inv, "sys", [])

    assert len(calls) == 1


def test_non_auth_error_does_not_raise_auth_expired(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Exit codes other than 69 must not raise AuthExpired."""
    inv = _make_inv(tmp_path)
    r1 = _make_result(tmp_path, exit_code=1)
    r2 = _make_result(tmp_path, exit_code=0, stop_reason="end_turn")

    it = iter([r1, r2])

    def fake_invoke(i: WorkerInvocation, sp: str, tools: list[str]) -> WorkerResult:
        return next(it)

    monkeypatch.setattr("lem.workers.dispatch.cli_worker.invoke", fake_invoke)

    result = dispatch_worker(inv, "sys", [])
    assert result.exit_code == 0
