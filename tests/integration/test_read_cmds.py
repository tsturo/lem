"""Integration tests for read commands: watch, list, show, logs (Task 8.2)."""

from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from lem.cli import app
from lem.state.run_state import write_state
from lem.state.log import append_log
from lem.types import LogEvent, RunState


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


def _make_state(workspace: Path, *, status: str = "completed", phase: str = "5") -> RunState:
    state = RunState(
        run_id=workspace.name,
        workspace_path=workspace,
        phase=phase,
        status=status,  # type: ignore[arg-type]
        started_at=time.time() - 60,
        last_event_at=time.time(),
        cost_so_far=0.12,
        error=None,
    )
    write_state(state)
    return state


# --- watch ---

def test_watch_once_prints_snapshot(runner: CliRunner, tmp_path: Path) -> None:
    ws = tmp_path / "my-run"
    ws.mkdir()
    _make_state(ws)
    with patch("lem.commands.watch.resolve_workspace", return_value=ws):
        result = runner.invoke(app, ["watch", "my-run", "--once"])
    assert result.exit_code == 0


def test_watch_json_prints_state_json(runner: CliRunner, tmp_path: Path) -> None:
    ws = tmp_path / "my-run"
    ws.mkdir()
    _make_state(ws)
    with patch("lem.commands.watch.resolve_workspace", return_value=ws):
        result = runner.invoke(app, ["watch", "my-run", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["status"] == "completed"


def test_watch_missing_run_exits_nonzero(runner: CliRunner, tmp_path: Path) -> None:
    with patch("lem.commands.watch.resolve_workspace", return_value=tmp_path / "no-run"):
        result = runner.invoke(app, ["watch", "no-run", "--once"])
    assert result.exit_code != 0


def test_watch_no_flags_prints_tui_stub(runner: CliRunner, tmp_path: Path) -> None:
    ws = tmp_path / "my-run"
    ws.mkdir()
    _make_state(ws)
    with patch("lem.commands.watch.resolve_workspace", return_value=ws):
        result = runner.invoke(app, ["watch", "my-run"])
    assert result.exit_code != 0
    assert "TUI" in result.output or "tui" in result.output.lower() or "--once" in result.output


# --- list ---

def test_list_empty_runs_dir(runner: CliRunner, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "no runs" in result.output.lower()


def test_list_populated_runs(runner: CliRunner, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    runs_dir = tmp_path / "lem" / "runs"
    ws = runs_dir / "2026-01-01-1200-coffee-abc123"
    ws.mkdir(parents=True)
    _make_state(ws)
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "2026-01-01-1200-coffee-abc123" in result.output


def test_list_json_output(runner: CliRunner, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    runs_dir = tmp_path / "lem" / "runs"
    ws = runs_dir / "2026-01-01-1200-coffee-abc123"
    ws.mkdir(parents=True)
    _make_state(ws)
    result = runner.invoke(app, ["list", "--json"])
    assert result.exit_code == 0
    rows = json.loads(result.output)
    assert isinstance(rows, list)
    assert rows[0]["name"] == "2026-01-01-1200-coffee-abc123"


def test_list_running_filter(runner: CliRunner, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    runs_dir = tmp_path / "lem" / "runs"

    ws1 = runs_dir / "run-completed"
    ws1.mkdir(parents=True)
    _make_state(ws1, status="completed")

    ws2 = runs_dir / "run-running"
    ws2.mkdir(parents=True)
    _make_state(ws2, status="running")

    result = runner.invoke(app, ["list", "--running"])
    assert result.exit_code == 0
    assert "run-running" in result.output
    assert "run-completed" not in result.output


# --- show ---

def test_show_obsidian_prints_url(runner: CliRunner, tmp_path: Path) -> None:
    ws = tmp_path / "my-run"
    ws.mkdir()
    deliverables = ws / "deliverables"
    deliverables.mkdir()
    (deliverables / "executive-summary.md").write_text("# Summary\n\nContent here.", encoding="utf-8")
    _make_state(ws)
    with patch("lem.commands.show.resolve_workspace", return_value=ws):
        result = runner.invoke(app, ["show", "my-run", "--in", "obsidian"])
    assert result.exit_code == 0
    assert "obsidian://" in result.output


def test_show_missing_run_exits_nonzero(runner: CliRunner, tmp_path: Path) -> None:
    with patch("lem.commands.show.resolve_workspace", return_value=tmp_path / "no-run"):
        result = runner.invoke(app, ["show", "no-run"])
    assert result.exit_code != 0


def test_show_unknown_viewer_exits_nonzero(runner: CliRunner, tmp_path: Path) -> None:
    ws = tmp_path / "my-run"
    ws.mkdir()
    deliverables = ws / "deliverables"
    deliverables.mkdir()
    (deliverables / "executive-summary.md").write_text("# Summary\n", encoding="utf-8")
    _make_state(ws)
    with patch("lem.commands.show.resolve_workspace", return_value=ws):
        result = runner.invoke(app, ["show", "my-run", "--in", "notepad"])
    assert result.exit_code != 0


def test_show_pager_invokes_subprocess(runner: CliRunner, tmp_path: Path) -> None:
    ws = tmp_path / "my-run"
    ws.mkdir()
    deliverables = ws / "deliverables"
    deliverables.mkdir()
    (deliverables / "executive-summary.md").write_text("# Summary\n\nContent.", encoding="utf-8")
    _make_state(ws)
    with patch("lem.commands.show.resolve_workspace", return_value=ws), \
         patch("lem.commands.show.subprocess.run") as mock_run:
        result = runner.invoke(app, ["show", "my-run"])
    assert result.exit_code == 0
    mock_run.assert_called_once()


# --- logs ---

def test_logs_shows_events(runner: CliRunner, tmp_path: Path) -> None:
    ws = tmp_path / "my-run"
    ws.mkdir()
    event = LogEvent(
        timestamp=time.time(), level="info", event="phase_start",
        phase="discover", role="architect", message="starting",
    )
    append_log(ws, event)
    with patch("lem.commands.logs.resolve_workspace", return_value=ws):
        result = runner.invoke(app, ["logs", "my-run"])
    assert result.exit_code == 0
    assert "phase_start" in result.output


def test_logs_phase_filter(runner: CliRunner, tmp_path: Path) -> None:
    ws = tmp_path / "my-run"
    ws.mkdir()
    append_log(ws, LogEvent(timestamp=time.time(), level="info", event="ev1", phase="discover"))
    append_log(ws, LogEvent(timestamp=time.time(), level="info", event="ev2", phase="synthesize"))
    with patch("lem.commands.logs.resolve_workspace", return_value=ws):
        result = runner.invoke(app, ["logs", "my-run", "--phase", "discover"])
    assert result.exit_code == 0
    assert "ev1" in result.output
    assert "ev2" not in result.output


def test_logs_errors_only(runner: CliRunner, tmp_path: Path) -> None:
    ws = tmp_path / "my-run"
    ws.mkdir()
    append_log(ws, LogEvent(timestamp=time.time(), level="info", event="info_ev"))
    append_log(ws, LogEvent(timestamp=time.time(), level="error", event="error_ev"))
    with patch("lem.commands.logs.resolve_workspace", return_value=ws):
        result = runner.invoke(app, ["logs", "my-run", "--errors-only"])
    assert result.exit_code == 0
    assert "error_ev" in result.output
    assert "info_ev" not in result.output


def test_logs_role_filter(runner: CliRunner, tmp_path: Path) -> None:
    ws = tmp_path / "my-run"
    ws.mkdir()
    append_log(ws, LogEvent(timestamp=time.time(), level="info", event="ev1", role="architect"))
    append_log(ws, LogEvent(timestamp=time.time(), level="info", event="ev2", role="market"))
    with patch("lem.commands.logs.resolve_workspace", return_value=ws):
        result = runner.invoke(app, ["logs", "my-run", "--role", "architect"])
    assert result.exit_code == 0
    assert "ev1" in result.output
    assert "ev2" not in result.output


def test_logs_missing_log_exits_nonzero(runner: CliRunner, tmp_path: Path) -> None:
    ws = tmp_path / "no-log-run"
    ws.mkdir()
    with patch("lem.commands.logs.resolve_workspace", return_value=ws):
        result = runner.invoke(app, ["logs", "no-log-run"])
    assert result.exit_code != 0
