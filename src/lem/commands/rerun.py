"""`lem rerun`."""

from __future__ import annotations

import typer

from lem.daemon import daemonize
from lem.orchestrator import OrchestratorConfig, run_orchestrator
from lem.paths import make_run_id, resolve_workspace
from lem.profile import load_profile
from lem.state.run_state import read_state

app = typer.Typer()


@app.command()
def rerun(
    run_id: str = typer.Argument(help="Run ID of the run to repeat"),
) -> None:
    """Start a new run with the same idea and flags as an existing run."""
    workspace_path = resolve_workspace(run_id=run_id)

    read_state(workspace_path)  # validates the workspace has a valid state

    idea_path = workspace_path / "idea.md"
    if not idea_path.exists():
        typer.echo("idea.md not found in original run workspace", err=True)
        raise typer.Exit(1)

    idea = idea_path.read_text(encoding="utf-8").strip()

    profile_name = "app-idea"
    profile_obj = load_profile(profile_name)

    new_run_id = make_run_id(name=None, idea=idea)
    new_workspace = resolve_workspace(run_id=new_run_id)
    new_workspace.mkdir(parents=True, exist_ok=True)

    idea_path_new = new_workspace / "idea.md"
    idea_path_new.write_text(idea_path.read_text(encoding="utf-8"), encoding="utf-8")

    assumptions_src = workspace_path / "assumptions.yaml"
    if assumptions_src.exists():
        (new_workspace / "assumptions.yaml").write_text(
            assumptions_src.read_text(encoding="utf-8"), encoding="utf-8"
        )

    config = OrchestratorConfig()

    actual_run_id = daemonize(
        new_workspace,
        lambda: run_orchestrator(new_workspace, profile_obj, config),
    )
    typer.echo(actual_run_id)
