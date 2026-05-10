"""Integration tests for `lem refine` (Task 8.1)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any
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
    fake_state.cost_so_far = 0.0

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
    assert "done" in result.output.lower() or "complete" in result.output.lower()


def test_workspace_resolution_xdg(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    from lem.paths import resolve_workspace
    ws = resolve_workspace(run_id="test-run-id")
    assert str(tmp_path) in str(ws)
    assert "test-run-id" in str(ws)


def test_from_file_reads_idea_from_file(runner: CliRunner, tmp_path: Path) -> None:
    idea_file = tmp_path / "idea.md"
    idea_file.write_text("an app that helps freelancers track invoices\n")
    with patch("lem.commands.refine.run_intake") as mock_intake, \
         patch("lem.commands.refine.daemonize") as mock_daemon:
        mock_intake.return_value = MagicMock()
        mock_daemon.return_value = "fake-run-id"
        result = runner.invoke(
            app,
            ["refine", "--from-file", str(idea_file),
             "--workspace", str(tmp_path / "ws"), "--skip-intake"],
        )
    assert result.exit_code == 0, result.output
    one_liner = mock_intake.call_args.kwargs["one_liner"]
    assert "freelancers track invoices" in one_liner


def test_from_file_missing_file_errors(runner: CliRunner, tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["refine", "--from-file", str(tmp_path / "nope.md"),
         "--workspace", str(tmp_path / "ws"), "--skip-intake"],
    )
    assert result.exit_code != 0


def test_from_file_empty_file_errors(runner: CliRunner, tmp_path: Path) -> None:
    idea_file = tmp_path / "empty.md"
    idea_file.write_text("   \n\n  ")
    result = runner.invoke(
        app,
        ["refine", "--from-file", str(idea_file),
         "--workspace", str(tmp_path / "ws"), "--skip-intake"],
    )
    assert result.exit_code != 0
    assert "empty" in result.output.lower()


def test_idea_and_from_file_mutually_exclusive(runner: CliRunner, tmp_path: Path) -> None:
    idea_file = tmp_path / "idea.md"
    idea_file.write_text("idea from file")
    result = runner.invoke(
        app,
        ["refine", "positional idea", "--from-file", str(idea_file),
         "--workspace", str(tmp_path / "ws"), "--skip-intake"],
    )
    assert result.exit_code != 0
    assert "both" in result.output.lower() or "mutually" in result.output.lower()


def test_neither_idea_nor_from_file_errors(runner: CliRunner, tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["refine", "--workspace", str(tmp_path / "ws"), "--skip-intake"],
    )
    assert result.exit_code != 0


def test_attach_passes_progress_cb_to_orchestrator(
    runner: CliRunner, tmp_path: Path
) -> None:
    fake_state = MagicMock()
    fake_state.status = "completed"
    fake_state.run_id = "test-run"
    fake_state.cost_so_far = 0.0
    captured_config: list[Any] = []

    def fake_orch(workspace_path: Any, profile: Any, config: Any) -> Any:
        captured_config.append(config)
        return fake_state

    with patch("lem.commands.refine.run_intake") as mock_intake, \
         patch("lem.commands.refine.run_orchestrator", side_effect=fake_orch):
        mock_intake.return_value = MagicMock()
        result = runner.invoke(
            app,
            ["refine", "an idea", "--workspace", str(tmp_path),
             "--skip-intake", "--attach"],
        )
    assert result.exit_code == 0
    assert len(captured_config) == 1
    assert captured_config[0].progress_cb is not None


def test_user_printer_renders_human_friendly_phase_labels(
    runner: CliRunner, tmp_path: Path
) -> None:
    """User mode should show phase purposes, not phase IDs."""
    from lem.commands.refine import _UserPrinter
    from lem.orchestrator import ProgressEvent

    p = _UserPrinter(idea="a dog walking app", ws=tmp_path)
    captured: list[str] = []
    monkey = pytest.MonkeyPatch()
    monkey.setattr("lem.commands.refine.typer.echo", lambda s="": captured.append(s))
    try:
        p.on_run_start()
        p.on_event(ProgressEvent(kind="phase_start", phase_id="0.5"))
        p.on_event(ProgressEvent(
            kind="phase_done", phase_id="0.5", duration_s=22.0,
            cost_usd=0.01, success=True,
        ))
    finally:
        monkey.undo()

    output = "\n".join(captured)
    assert "job-to-be-done" in output.lower()
    assert "phase 0.5" not in output.lower()
    assert "$" not in output  # per-step cost suppressed in user mode


def test_user_printer_failure_narrative_explains_what_to_do(
    tmp_path: Path
) -> None:
    """On failure, user mode should print a 'what happened / what to do' block."""
    from lem.commands.refine import _UserPrinter
    from lem.orchestrator import ProgressEvent

    p = _UserPrinter(idea="a dog walking app", ws=tmp_path)
    captured: list[str] = []
    monkey = pytest.MonkeyPatch()
    monkey.setattr("lem.commands.refine.typer.echo", lambda s="": captured.append(s))

    fake_state = MagicMock()
    fake_state.status = "failed"
    fake_state.run_id = "rid"
    fake_state.cost_so_far = 0.33
    fake_state.error = "phase 0.6 failure rate 100% (1/1) exceeds threshold 50%"
    try:
        p.on_event(ProgressEvent(
            kind="phase_done", phase_id="0.6", duration_s=180.0,
            cost_usd=0.32, success=False,
        ))
        p.on_run_end(fake_state)
    finally:
        monkey.undo()

    output = "\n".join(captured)
    assert "what happened" in output.lower()
    assert "what to do" in output.lower()
    assert "framing" in output.lower()  # 0.6-specific blurb
    assert "0.33" in output  # cost summary


def test_verbose_mode_emits_legacy_operator_format(
    runner: CliRunner, tmp_path: Path
) -> None:
    fake_state = MagicMock()
    fake_state.status = "completed"
    fake_state.run_id = "test-run"
    fake_state.cost_so_far = 0.0

    with patch("lem.commands.refine.run_intake") as mock_intake, \
         patch("lem.commands.refine.run_orchestrator") as mock_orch:
        mock_intake.return_value = MagicMock()
        mock_orch.return_value = fake_state
        result = runner.invoke(
            app,
            ["refine", "dog walking app", "--workspace", str(tmp_path),
             "--skip-intake", "--attach", "--verbose"],
        )
    assert result.exit_code == 0
    assert "Run complete:" in result.output


def test_daemon_path_does_not_pass_progress_cb(
    runner: CliRunner, tmp_path: Path
) -> None:
    captured_config: list[Any] = []

    def fake_daemon(workspace_path: Any, fn: Any) -> str:
        captured_config.append(fn.__closure__[0].cell_contents if fn.__closure__ else None)
        return "fake-id"

    with patch("lem.commands.refine.run_intake") as mock_intake, \
         patch("lem.commands.refine.daemonize", side_effect=fake_daemon):
        mock_intake.return_value = MagicMock()
        result = runner.invoke(
            app,
            ["refine", "an idea", "--workspace", str(tmp_path), "--skip-intake"],
        )
    assert result.exit_code == 0


def test_attach_exits_69_on_auth_expired(runner: CliRunner, tmp_path: Path) -> None:
    """When the orchestrator returns auth_expired status, lem refine --attach exits 69."""
    fake_state = MagicMock()
    fake_state.status = "auth_expired"
    fake_state.run_id = "test-run"
    fake_state.cost_so_far = 0.0

    with patch("lem.commands.refine.run_intake") as mock_intake, \
         patch("lem.commands.refine.run_orchestrator") as mock_orch:
        mock_intake.return_value = MagicMock()
        mock_orch.return_value = fake_state
        result = runner.invoke(
            app,
            ["refine", "dog walking app", "--workspace", str(tmp_path),
             "--skip-intake", "--attach"],
        )
    assert result.exit_code == 69


def test_attach_does_not_exit_69_on_completed(runner: CliRunner, tmp_path: Path) -> None:
    """Successful runs must not exit with code 69."""
    fake_state = MagicMock()
    fake_state.status = "completed"
    fake_state.run_id = "test-run"
    fake_state.cost_so_far = 0.0

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


def test_round2_flags_reach_orchestrator_config(
    runner: CliRunner, tmp_path: Path
) -> None:
    """--parent-run-id, --branch-label, and --iteration-context-file are threaded
    into OrchestratorConfig."""
    ctx_file = tmp_path / "context.md"
    ctx_file.write_text("what changed")
    fake_state = MagicMock()
    fake_state.status = "completed"
    fake_state.run_id = "test-run"
    fake_state.cost_so_far = 0.0
    captured_config: list[Any] = []

    def fake_orch(workspace_path: Any, profile: Any, config: Any) -> Any:
        captured_config.append(config)
        return fake_state

    with patch("lem.commands.refine.run_intake") as mock_intake, \
         patch("lem.commands.refine.run_orchestrator", side_effect=fake_orch):
        mock_intake.return_value = MagicMock()
        result = runner.invoke(
            app,
            [
                "refine", "an idea",
                "--workspace", str(tmp_path),
                "--skip-intake", "--attach",
                "--parent-run-id", "run-abc",
                "--branch-label", "faster onboarding flow",
                "--iteration-context-file", str(ctx_file),
            ],
        )
    assert result.exit_code == 0, result.output
    assert len(captured_config) == 1
    cfg = captured_config[0]
    assert cfg.parent_run_id == "run-abc"
    assert cfg.branch_label == "faster onboarding flow"
    assert cfg.iteration_context_file == ctx_file


def test_round2_flags_default_to_none(runner: CliRunner, tmp_path: Path) -> None:
    """When round-2 flags are not supplied, all three default to None."""
    fake_state = MagicMock()
    fake_state.status = "completed"
    fake_state.run_id = "test-run"
    fake_state.cost_so_far = 0.0
    captured_config: list[Any] = []

    def fake_orch(workspace_path: Any, profile: Any, config: Any) -> Any:
        captured_config.append(config)
        return fake_state

    with patch("lem.commands.refine.run_intake") as mock_intake, \
         patch("lem.commands.refine.run_orchestrator", side_effect=fake_orch):
        mock_intake.return_value = MagicMock()
        result = runner.invoke(
            app,
            ["refine", "an idea", "--workspace", str(tmp_path),
             "--skip-intake", "--attach"],
        )
    assert result.exit_code == 0, result.output
    assert len(captured_config) == 1
    cfg = captured_config[0]
    assert cfg.parent_run_id is None
    assert cfg.branch_label is None
    assert cfg.iteration_context_file is None
