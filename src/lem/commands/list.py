"""`lem list`."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

import typer

from lem.state.run_state import read_state

app = typer.Typer()

_VERDICT_GLYPHS: dict[str, str] = {
    "completed": "✓",
    "failed": "✗",
    "cancelled": "✗",
    "cost-aborted": "✗",
    "wall-clock-aborted": "✗",
    "running": "…",
}


def _xdg_runs_dir() -> Path:
    xdg = os.environ.get("XDG_DATA_HOME")
    base = Path(xdg) if xdg else Path.home() / ".local" / "share"
    return base / "lem" / "runs"


def _verdict_glyph(status: str, phase: str) -> str:
    if status == "completed":
        if phase in ("synthesize", "5"):
            return "✓"
        return "—"
    return _VERDICT_GLYPHS.get(status, "?")


def _iter_runs(runs_dir: Path) -> list[Path]:
    if not runs_dir.is_dir():
        return []
    return sorted(runs_dir.iterdir())


def _idea_snippet(workspace_path: Path) -> str:
    idea_path = workspace_path / "idea.md"
    if not idea_path.exists():
        return ""
    text = idea_path.read_text(encoding="utf-8")
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            return line[:60]
    return ""


@app.command(name="list")
def list_runs(
    running: bool = typer.Option(False, "--running", help="Show only running runs"),
    grep: Optional[str] = typer.Option(
        None, "--grep", help="Filter by substring in idea.md"
    ),
    json_out: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """List all lem runs."""
    runs_dir = _xdg_runs_dir()
    workspaces = _iter_runs(runs_dir)

    rows: list[dict[str, str]] = []
    for ws in workspaces:
        state_path = ws / "meta" / "state.json"
        if not state_path.exists():
            continue
        try:
            state = read_state(ws)
        except Exception:
            continue

        if running and state.status != "running":
            continue

        idea = _idea_snippet(ws)
        if grep and grep.lower() not in idea.lower():
            continue

        rows.append({
            "name": state.run_id,
            "status": state.status,
            "phase": state.phase,
            "idea": idea,
            "glyph": _verdict_glyph(state.status, state.phase),
        })

    if json_out:
        typer.echo(json.dumps(rows, indent=2))
        return

    if not rows:
        typer.echo("No runs found.")
        return

    name_w = max(len(r["name"]) for r in rows)
    status_w = max(len(r["status"]) for r in rows)
    for row in rows:
        line = (
            f"{row['glyph']} {row['name']:<{name_w}}"
            f"  {row['status']:<{status_w}}  {row['idea']}"
        )
        typer.echo(line)
