# pyright: strict
"""Tests for failure/timeout.py and workers/dispatch.py."""

from __future__ import annotations

import signal
import subprocess
import time
from pathlib import Path

import pytest

from lem.failure.timeout import run_with_escalation
from lem.types import WorkerInvocation, WorkerResult
from lem.workers.dispatch import dispatch_worker

TIMEOUT_STUBS = Path(__file__).parent.parent / "fixtures" / "timeout_stubs"
CLAUDE_STUBS = Path(__file__).parent.parent / "fixtures" / "claude_stubs"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_invocation(
    tmp_path: Path,
    *,
    timeout_s: int = 30,
    output_path: Path | None = None,
) -> WorkerInvocation:
    return WorkerInvocation(
        role_path=tmp_path / "role.md",
        workspace_path=tmp_path,
        output_path=output_path or tmp_path / "output.json",
        allowed_read_paths=[],
        model="sonnet",
        max_output_tokens=1024,
        timeout_s=timeout_s,
        extra_context={},
    )


# ---------------------------------------------------------------------------
# failure/timeout.py — run_with_escalation
# ---------------------------------------------------------------------------


def test_quick_command_completes_normally() -> None:
    result = run_with_escalation(
        [str(TIMEOUT_STUBS / "quick")],
        timeout_s=5,
    )
    assert result.returncode == 0
    assert "done" in result.stdout


def test_no_timeout_for_fast_command() -> None:
    start = time.monotonic()
    result = run_with_escalation(
        [str(TIMEOUT_STUBS / "quick")],
        timeout_s=5,
    )
    elapsed = time.monotonic() - start
    assert result.returncode == 0
    assert elapsed < 2.0


def test_sigterm_sent_at_timeout() -> None:
    start = time.monotonic()
    result = run_with_escalation(
        [str(TIMEOUT_STUBS / "sleeper")],
        timeout_s=1,
        grace_s=5,
    )
    elapsed = time.monotonic() - start
    assert result.returncode == -signal.SIGTERM
    assert elapsed < 3.0


def test_sigkill_after_grace_when_sigterm_ignored() -> None:
    start = time.monotonic()
    result = run_with_escalation(
        [str(TIMEOUT_STUBS / "sigterm_immune")],
        timeout_s=1,
        grace_s=1,
    )
    elapsed = time.monotonic() - start
    assert result.returncode == -signal.SIGKILL
    assert elapsed < 4.0


def test_input_passed_to_subprocess() -> None:
    result = run_with_escalation(
        ["cat"],
        timeout_s=5,
        input="hello world",
    )
    assert result.returncode == 0
    assert result.stdout == "hello world"


def test_cwd_set_correctly(tmp_path: Path) -> None:
    result = run_with_escalation(
        ["pwd"],
        timeout_s=5,
        cwd=tmp_path,
    )
    assert result.returncode == 0
    assert Path(result.stdout.strip()).resolve() == tmp_path.resolve()


# ---------------------------------------------------------------------------
# workers/dispatch.py — happy path passthrough
# ---------------------------------------------------------------------------


def test_dispatch_passes_through_happy_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LEM_CLAUDE_BIN", str(CLAUDE_STUBS / "claude_success"))
    inv = make_invocation(tmp_path)
    result = dispatch_worker(inv, system_prompt="Be concise.", allowed_tools=[])

    assert isinstance(result, WorkerResult)
    assert result.stop_reason == "end_turn"
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# workers/dispatch.py — timeout integration
# ---------------------------------------------------------------------------


def test_dispatch_returns_timeout_result_when_claude_hangs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LEM_CLAUDE_BIN", str(CLAUDE_STUBS / "claude_hang"))
    inv = make_invocation(tmp_path, timeout_s=1)
    result = dispatch_worker(inv, system_prompt="sys", allowed_tools=[])

    assert result.stop_reason == "timeout"
    assert result.exit_code == -1
    assert result.tokens_in == 0
    assert result.tokens_out == 0


def test_dispatch_no_partial_output_on_timeout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LEM_CLAUDE_BIN", str(CLAUDE_STUBS / "claude_hang"))
    output = tmp_path / "output.json"
    inv = make_invocation(tmp_path, timeout_s=1, output_path=output)
    dispatch_worker(inv, system_prompt="sys", allowed_tools=[])

    assert not output.exists()
    tmp_file = output.with_suffix(output.suffix + ".tmp")
    assert not tmp_file.exists()
