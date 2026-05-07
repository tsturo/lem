# pyright: strict
"""Per-worker drill-down."""

from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import ScrollableContainer, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Label, Static

from lem.state.cost import read_cost
from lem.state.log import read_log


class WorkerScreen(Screen[None]):  # pyright: ignore[reportMissingTypeArgument]
    BINDINGS = [Binding("escape", "app.pop_screen", "Back")]

    def __init__(self, workspace_path: Path, role: str, phase: str) -> None:
        super().__init__()
        self._workspace_path = workspace_path
        self._role = role
        self._phase = phase

    def compose(self) -> ComposeResult:
        yield Header()
        yield ScrollableContainer(
            Vertical(
                Label(f"[bold]Worker: {self._role}[/bold]"),
                Label(f"Phase: {self._phase}"),
                self._build_cost_info(),
                Label("[bold]Log entries:[/bold]"),
                self._build_log_widget(),
            )
        )
        yield Footer()

    def _build_cost_info(self) -> Static:
        events = [
            e for e in read_cost(self._workspace_path)
            if e.role == self._role and e.phase == self._phase
        ]
        if not events:
            return Static("[dim]No cost data[/dim]")
        total_in = sum(e.tokens_in for e in events)
        total_out = sum(e.tokens_out for e in events)
        total_cost = sum(e.cost_usd for e in events)
        model = events[-1].model
        lines = [
            f"Model: {model}",
            f"Tokens in: {total_in:,} | Tokens out: {total_out:,}",
            f"Cost: ${total_cost:.4f}",
            f"Attempts: {len(events)}",
        ]
        return Static("\n".join(lines))

    def _build_log_widget(self) -> Static:
        events = [
            e for e in read_log(self._workspace_path)
            if e.role == self._role and e.phase == self._phase
        ]
        if not events:
            return Static("[dim]No log entries[/dim]")
        lines = [
            f"[{e.level.upper()}] {e.event}: {e.message}"
            for e in events[-50:]
        ]
        return Static("\n".join(lines))
