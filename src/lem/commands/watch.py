"""`lem watch`."""

from __future__ import annotations

from typing import Optional

import typer

from lem.paths import resolve_workspace
from lem.state.run_state import read_state

app = typer.Typer()


@app.command()
def watch(
    run_id: Optional[str] = typer.Argument(None, help="Run ID or omit for local .lem"),
    once: bool = typer.Option(False, "--once", help="One-shot state snapshot"),
    json_out: bool = typer.Option(False, "--json", help="Print state as JSON"),
) -> None:
    """Watch a run's progress. Use --once for a single snapshot."""
    workspace_path = resolve_workspace(run_id=run_id)
    if not (workspace_path / "meta" / "state.json").exists():
        typer.echo(f"No run found at: {workspace_path}", err=True)
        raise typer.Exit(1)

    if json_out:
        typer.echo((workspace_path / "meta" / "state.json").read_text(encoding="utf-8"))
        return

    if once:
        state = read_state(workspace_path)
        typer.echo(f"run_id:  {state.run_id}", err=True)
        typer.echo(f"status:  {state.status}", err=True)
        typer.echo(f"phase:   {state.phase}", err=True)
        typer.echo(f"cost:    ${state.cost_so_far:.4f}", err=True)
        return

    typer.echo("TUI not yet integrated; use --once for now", err=True)
    raise typer.Exit(1)
