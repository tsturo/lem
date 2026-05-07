"""`lem logs`."""

from __future__ import annotations

from typing import Optional

import typer

from lem.paths import resolve_workspace
from lem.state.log import read_log
from lem.types import LogEvent

app = typer.Typer()


@app.command()
def logs(
    run_id: str = typer.Argument(help="Run ID"),
    phase: Optional[str] = typer.Option(None, "--phase", help="Filter by phase name"),
    role: Optional[str] = typer.Option(None, "--role", help="Filter by role name"),
    errors_only: bool = typer.Option(
        False, "--errors-only", help="Show only error-level events"
    ),
) -> None:
    """Tail the structured log for a run."""
    workspace_path = resolve_workspace(run_id=run_id)
    log_path = workspace_path / "meta" / "log.jsonl"

    if not log_path.exists():
        typer.echo(f"No log found at: {log_path}", err=True)
        raise typer.Exit(1)

    for event in read_log(workspace_path):
        if not _matches(event, phase=phase, role=role, errors_only=errors_only):
            continue
        typer.echo(_format_event(event))


def _matches(
    event: LogEvent,
    *,
    phase: Optional[str],
    role: Optional[str],
    errors_only: bool,
) -> bool:
    if errors_only and event.level != "error":
        return False
    if phase is not None and event.phase != phase:
        return False
    if role is not None and event.role != role:
        return False
    return True


def _format_event(event: LogEvent) -> str:
    parts = [f"[{event.level.upper():>7}]", event.event]
    if event.phase:
        parts.append(f"phase={event.phase}")
    if event.role:
        parts.append(f"role={event.role}")
    if event.message:
        parts.append(event.message)
    return "  ".join(parts)
