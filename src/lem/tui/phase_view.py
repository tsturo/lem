# pyright: strict
"""Per-phase drill-down."""

from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import ScrollableContainer, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Label, Static

from lem.state.cost import phase_total, read_cost
from lem.state.timeline import read_timeline


class PhaseScreen(Screen[None]):  # pyright: ignore[reportMissingTypeArgument]
    BINDINGS = [Binding("escape", "app.pop_screen", "Back")]

    def __init__(self, workspace_path: Path, phase: str) -> None:
        super().__init__()
        self._workspace_path = workspace_path
        self._phase = phase

    def compose(self) -> ComposeResult:
        yield Header()
        yield ScrollableContainer(
            Vertical(
                Label(f"[bold]Phase: {self._phase}[/bold]"),
                self._build_timeline_widget(),
                self._build_cost_widget(),
                self._build_artifacts_widget(),
            )
        )
        yield Footer()

    def _build_timeline_widget(self) -> Static:
        events = [
            e for e in read_timeline(self._workspace_path)
            if e.phase == self._phase
        ]
        if not events:
            return Static("[dim]No timeline data[/dim]")
        lines = ["[bold]Workers:[/bold]"]
        total_s = sum(e.duration_s for e in events)
        for e in events:
            lines.append(f"  {e.role} — {e.duration_s:.1f}s (attempt {e.attempt})")
        lines.append(f"Total time: {total_s:.1f}s")
        return Static("\n".join(lines))

    def _build_cost_widget(self) -> Static:
        cost = phase_total(self._workspace_path, self._phase)
        events = [
            e for e in read_cost(self._workspace_path)
            if e.phase == self._phase
        ]
        total_in = sum(e.tokens_in for e in events)
        total_out = sum(e.tokens_out for e in events)
        return Static(
            f"Tokens in: {total_in:,} | Tokens out: {total_out:,} | Cost: ${cost:.4f}"
        )

    def _build_artifacts_widget(self) -> Static:
        phase_dir = self._workspace_path / self._phase
        if not phase_dir.exists():
            return Static("[dim]No artifacts directory[/dim]")
        files = sorted(phase_dir.iterdir())
        if not files:
            return Static("[dim]No artifacts[/dim]")
        lines = ["[bold]Artifacts:[/bold]"]
        for f in files:
            lines.append(f"  {f.name}")
        return Static("\n".join(lines))
