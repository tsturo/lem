"""`lem show` (with --in pager|obsidian|browser)."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Optional

import typer

from lem.paths import resolve_workspace

app = typer.Typer()


@app.command()
def show(
    run_id: str = typer.Argument(help="Run ID to display"),
    viewer: Optional[str] = typer.Option(None, "--in", help="pager|obsidian|browser"),
) -> None:
    """Open the executive summary for a run."""
    workspace_path = resolve_workspace(run_id=run_id)
    summary_path = workspace_path / "deliverables" / "executive-summary.md"

    if not summary_path.exists():
        typer.echo(f"No executive summary found at: {summary_path}", err=True)
        raise typer.Exit(1)

    if viewer is None or viewer == "pager":
        _open_pager(summary_path)
    elif viewer == "obsidian":
        url = f"obsidian://open?path={summary_path}"
        typer.echo(url)
    elif viewer == "browser":
        _open_browser(workspace_path, summary_path)
    else:
        typer.echo(
            f"Unknown viewer: {viewer!r}. Use pager, obsidian, or browser.",
            err=True,
        )
        raise typer.Exit(1)


def _open_pager(path: Path) -> None:
    pager = os.environ.get("PAGER", "less")
    subprocess.run([pager, str(path)], check=False)


def _open_browser(workspace_path: Path, summary_path: Path) -> None:
    report_path = workspace_path / "report.html"
    if not report_path.exists():
        from lem.render.report import generate_report
        generate_report(workspace_path, report_path)
    import webbrowser
    webbrowser.open(report_path.as_uri())
