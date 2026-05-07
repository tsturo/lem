"""`lem cancel`."""

from __future__ import annotations

import os
import time

import typer

from lem.control import write_control
from lem.paths import resolve_workspace
from lem.state.run_state import read_state, write_state

app = typer.Typer()


@app.command()
def cancel(
    run_id: str = typer.Argument(help="Run ID to cancel"),
) -> None:
    """Cancel a running or stalled run."""
    workspace_path = resolve_workspace(run_id=run_id)

    state_path = workspace_path / "meta" / "state.json"
    if not state_path.exists():
        typer.echo(f"No run found at: {workspace_path}", err=True)
        raise typer.Exit(1)

    state = read_state(workspace_path)

    if state.status != "running":
        typer.echo(f"Run is not running (status={state.status})", err=True)
        raise typer.Exit(1)

    pid_path = workspace_path / "meta" / "pid"
    if pid_path.exists():
        try:
            pid = int(pid_path.read_text(encoding="utf-8").strip())
            _is_alive = _process_alive(pid)
        except Exception:
            _is_alive = False
    else:
        _is_alive = False

    if _is_alive:
        write_control(workspace_path, "cancel")
        typer.echo(f"Cancel signal sent to run: {run_id}")
    else:
        state.status = "cancelled"
        state.last_event_at = time.time()
        write_state(state)
        typer.echo(f"Run marked as cancelled (process was not running): {run_id}")


def _process_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False
