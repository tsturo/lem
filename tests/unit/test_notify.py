# pyright: strict
"""Tests for src/lem/notify.py — OS notifications."""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from lem.notify import notify
from lem.types import RunState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_state(*, status: str = "completed", run_id: str = "test-run") -> RunState:
    now = time.time()
    return RunState(
        run_id=run_id,
        workspace_path=Path("/tmp/ws"),
        phase="4",
        status=status,  # type: ignore[arg-type]
        started_at=now - 5.0,
        last_event_at=now,
        cost_so_far=0.0,
        error=None,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_notify_noop_without_env_or_force(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LEM_NOTIFY", raising=False)
    state = _make_state()
    with patch("subprocess.run") as mock_run:
        notify(state)
        mock_run.assert_not_called()


def test_notify_fires_when_force_true(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LEM_NOTIFY", raising=False)
    state = _make_state()
    with patch("subprocess.run") as mock_run, \
         patch("sys.platform", "linux"), \
         patch("shutil.which", return_value="/usr/bin/notify-send"):
        notify(state, force=True)
        mock_run.assert_called_once()


def test_notify_fires_when_env_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LEM_NOTIFY", "1")
    state = _make_state()
    with patch("subprocess.run") as mock_run, \
         patch("sys.platform", "linux"), \
         patch("shutil.which", return_value="/usr/bin/notify-send"):
        notify(state)
        mock_run.assert_called_once()


def test_notify_macos_uses_osascript(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LEM_NOTIFY", "1")
    state = _make_state(status="completed")
    with patch("subprocess.run") as mock_run, \
         patch("sys.platform", "darwin"), \
         patch("shutil.which", return_value="/usr/bin/osascript"):
        notify(state)
        args = mock_run.call_args[0][0]
        assert args[0] == "osascript"
        assert "display notification" in args[2]
        assert "lem run completed" in args[2]


def test_notify_linux_uses_notify_send(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LEM_NOTIFY", "1")
    state = _make_state(status="failed")
    with patch("subprocess.run") as mock_run, \
         patch("sys.platform", "linux"), \
         patch("shutil.which", return_value="/usr/bin/notify-send"):
        notify(state)
        args = mock_run.call_args[0][0]
        assert args[0] == "notify-send"
        assert "lem run failed" in args[1]


def test_notify_bell_fallback_when_no_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LEM_NOTIFY", "1")
    state = _make_state()
    with patch("subprocess.run") as mock_run, \
         patch("sys.platform", "linux"), \
         patch("shutil.which", return_value=None), \
         patch("sys.stderr") as mock_stderr:
        mock_stderr.isatty.return_value = True
        notify(state)
        mock_run.assert_not_called()
        mock_stderr.write.assert_called_once_with("\a")


def test_notify_bell_skipped_when_not_tty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LEM_NOTIFY", "1")
    state = _make_state()
    with patch("subprocess.run") as mock_run, \
         patch("sys.platform", "linux"), \
         patch("shutil.which", return_value=None), \
         patch("sys.stderr") as mock_stderr:
        mock_stderr.isatty.return_value = False
        notify(state)
        mock_run.assert_not_called()
        mock_stderr.write.assert_not_called()
