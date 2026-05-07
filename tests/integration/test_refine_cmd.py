"""Integration tests for `lem refine` (Task 8.1)."""

from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from lem.cli import app


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


def test_refine_dry_run_prints_estimate(runner: CliRunner, tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["refine", "an app for dog walkers", "--dry-run", "--profile", "app-idea",
         "--workspace", str(tmp_path)],
    )
    assert result.exit_code == 0
    output = result.output.lower()
    assert "estimate" in output or "tokens" in output


def test_refine_dry_run_shows_roles_count(runner: CliRunner, tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["refine", "coffee delivery app", "--dry-run", "--workspace", str(tmp_path)],
    )
    assert result.exit_code == 0
    assert "roles:" in result.output.lower()


def test_refine_dry_run_shows_cost(runner: CliRunner, tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["refine", "meditation timer app", "--dry-run", "--workspace", str(tmp_path)],
    )
    assert result.exit_code == 0
    assert "$" in result.output


def test_run_id_format() -> None:
    from lem.paths import make_run_id
    run_id = make_run_id(name=None, idea="an app for dog walkers")
    # format: YYYY-MM-DD-HHMM-<slug>-<6hex>
    assert re.match(r"^\d{4}-\d{2}-\d{2}-\d{4}-[a-z0-9-]+-[0-9a-f]{6}$", run_id), run_id


def test_run_id_with_name() -> None:
    from lem.paths import make_run_id
    run_id = make_run_id(name="my-project", idea="some idea here")
    assert "my-project" in run_id
    assert re.match(r"^\d{4}-\d{2}-\d{2}-\d{4}-my-project-[0-9a-f]{6}$", run_id), run_id


def test_run_id_slug_uses_first_three_words() -> None:
    from lem.paths import make_run_id
    run_id = make_run_id(name=None, idea="coffee delivery app for offices")
    assert "coffee-delivery-app" in run_id


def test_workspace_flag_takes_priority(runner: CliRunner, tmp_path: Path) -> None:
    ws = tmp_path / "my-workspace"
    with patch("lem.commands.refine.run_intake") as mock_intake, \
         patch("lem.commands.refine.daemonize") as mock_daemon:
        mock_intake.return_value = MagicMock()
        mock_daemon.return_value = "fake-run-id"
        result = runner.invoke(
            app,
            ["refine", "dog walking app", "--workspace", str(ws), "--skip-intake"],
        )
    assert result.exit_code == 0
    assert ws.exists()


def test_daemon_path_prints_run_id(runner: CliRunner, tmp_path: Path) -> None:
    with patch("lem.commands.refine.run_intake") as mock_intake, \
         patch("lem.commands.refine.daemonize") as mock_daemon:
        mock_intake.return_value = MagicMock()
        mock_daemon.return_value = "2026-01-01-1200-dog-walking-abc123"
        result = runner.invoke(
            app,
            ["refine", "dog walking app", "--workspace", str(tmp_path), "--skip-intake"],
        )
    assert result.exit_code == 0
    assert "2026-01-01-1200-dog-walking-abc123" in result.output


def test_attach_flag_runs_foreground(runner: CliRunner, tmp_path: Path) -> None:
    fake_state = MagicMock()
    fake_state.status = "completed"
    fake_state.run_id = "test-run"

    with patch("lem.commands.refine.run_intake") as mock_intake, \
         patch("lem.commands.refine.run_orchestrator") as mock_orch:
        mock_intake.return_value = MagicMock()
        mock_orch.return_value = fake_state
        result = runner.invoke(
            app,
            ["refine", "dog walking app", "--workspace", str(tmp_path),
             "--skip-intake", "--attach"],
        )
    assert result.exit_code == 0
    assert "complete" in result.output.lower()


def test_workspace_resolution_xdg(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    from lem.paths import resolve_workspace
    ws = resolve_workspace(run_id="test-run-id")
    assert str(tmp_path) in str(ws)
    assert "test-run-id" in str(ws)
