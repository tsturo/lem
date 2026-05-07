"""`lem render` (CLI command -- distinct from src/lem/render/report.py)."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from lem.paths import resolve_workspace
from lem.render.report import generate_report

app = typer.Typer()


@app.command()
def render(
    run_id: str = typer.Argument(help="Run ID to render"),
    output: Optional[Path] = typer.Option(
        None, "-o", "--output", help="Output path for report.html"
    ),
) -> None:
    """Generate a self-contained HTML report for a run."""
    workspace_path = resolve_workspace(run_id=run_id)

    if not (workspace_path / "meta" / "state.json").exists():
        typer.echo(f"No run found at: {workspace_path}", err=True)
        raise typer.Exit(1)

    output_path = output or workspace_path / "report.html"
    generate_report(workspace_path, output_path)
    typer.echo(str(output_path))
