"""Integration tests for lifecycle commands: rerun, cancel (Task 8.3)."""

from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from lem.cli import app
from lem.state.run_state import read_state, write_state
from lem.types import RunState


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


def _make_workspace(base: Path, run_id: str, status: str = "running") -> Path:
    ws = base / run_id
    ws.mkdir(parents=True)
    state = RunState(
        run_id=run_id,
        workspace_path=ws,
        phase="discover",
        status=status,  # type: ignore[arg-type]
        started_at=time.time() - 60,
        last_event_at=time.time(),
        cost_so_far=0.05,
        error=None,
    )
    write_state(state)
    (ws / "idea.md").write_text("# Idea\n\nA dog walking app for busy owners.", encoding="utf-8")
    return ws


# --- rerun ---

def test_rerun_dispatches_new_run(runner: CliRunner, tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path, "original-run")
    with patch("lem.commands.rerun.resolve_workspace", side_effect=[ws, tmp_path / "new-run"]), \
         patch("lem.commands.rerun.daemonize") as mock_daemon, \
         patch("lem.commands.rerun.load_profile") as mock_profile:
        mock_daemon.return_value = "new-run-id-abc123"
        mock_profile.return_value = MagicMock()
        result = runner.invoke(app, ["rerun", "original-run"])
    assert result.exit_code == 0
    assert "new-run-id-abc123" in result.output


def test_rerun_missing_idea_exits_nonzero(runner: CliRunner, tmp_path: Path) -> None:
    ws = tmp_path / "no-idea-run"
    ws.mkdir()
    state = RunState(
        run_id="no-idea-run",
        workspace_path=ws,
        phase="discover",
        status="completed",  # type: ignore[arg-type]
        started_at=time.time(),
        last_event_at=time.time(),
        cost_so_far=0.0,
        error=None,
    )
    write_state(state)
    # no idea.md written
    with patch("lem.commands.rerun.resolve_workspace", return_value=ws):
        result = runner.invoke(app, ["rerun", "no-idea-run"])
    assert result.exit_code != 0


def test_rerun_copies_idea_to_new_workspace(runner: CliRunner, tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path, "src-run")
    new_ws = tmp_path / "dest-run"

    def side_effects(run_id: str | None = None, **_: object) -> Path:
        if run_id == "src-run":
            return ws
        return new_ws

    with patch("lem.commands.rerun.resolve_workspace", side_effect=side_effects), \
         patch("lem.commands.rerun.daemonize") as mock_daemon, \
         patch("lem.commands.rerun.load_profile") as mock_profile:
        mock_daemon.return_value = "dest-run"
        mock_profile.return_value = MagicMock()
        runner.invoke(app, ["rerun", "src-run"])

    assert (new_ws / "idea.md").exists()


# --- cancel ---

def test_cancel_sends_control_signal(runner: CliRunner, tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path, "running-run")
    pid_path = ws / "meta" / "pid"
    # write a PID that is alive (our own process)
    import os
    pid_path.write_text(str(os.getpid()), encoding="utf-8")

    with patch("lem.commands.cancel.resolve_workspace", return_value=ws):
        result = runner.invoke(app, ["cancel", "running-run"])
    assert result.exit_code == 0
    control_path = ws / "meta" / "control.json"
    assert control_path.exists()
    data = json.loads(control_path.read_text())
    assert data["action"] == "cancel"


def test_cancel_dead_orchestrator_writes_state(runner: CliRunner, tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path, "dead-run")
    # no pid file → treated as dead

    with patch("lem.commands.cancel.resolve_workspace", return_value=ws):
        result = runner.invoke(app, ["cancel", "dead-run"])
    assert result.exit_code == 0
    state = read_state(ws)
    assert state.status == "cancelled"


def test_cancel_nonrunning_run_exits_nonzero(runner: CliRunner, tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path, "done-run", status="completed")

    with patch("lem.commands.cancel.resolve_workspace", return_value=ws):
        result = runner.invoke(app, ["cancel", "done-run"])
    assert result.exit_code != 0


def test_cancel_missing_run_exits_nonzero(runner: CliRunner, tmp_path: Path) -> None:
    with patch("lem.commands.cancel.resolve_workspace", return_value=tmp_path / "ghost-run"):
        result = runner.invoke(app, ["cancel", "ghost-run"])
    assert result.exit_code != 0
