# pyright: strict
"""Filterable log tail."""

from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Label, Select, Static

from lem.state.log import read_log
from lem.types import LogEvent

_LEVELS = ["all", "debug", "info", "warning", "error"]
_LEVEL_OPTIONS: list[tuple[str, str]] = [(lvl, lvl) for lvl in _LEVELS]


def _format_event(e: LogEvent) -> str:
    phase = e.phase or "-"
    role = e.role or "-"
    return f"[{e.level.upper():7}] [{phase}/{role}] {e.event}: {e.message}"


class LogsScreen(Screen[None]):  # pyright: ignore[reportMissingTypeArgument]
    BINDINGS = [Binding("escape", "app.pop_screen", "Back")]

    def __init__(self, workspace_path: Path) -> None:
        super().__init__()
        self._workspace_path = workspace_path
        self._level_filter = "all"
        self._phase_filter = "all"
        self._log_body = Static("")

    def compose(self) -> ComposeResult:
        yield Header()
        yield Vertical(
            Label("[bold]Logs[/bold]"),
            Horizontal(
                Label("Level: "),
                Select(  # pyright: ignore[reportUnknownMemberType]
                    options=_LEVEL_OPTIONS,
                    value="all",
                    id="level-select",
                ),
            ),
            ScrollableContainer(self._log_body),
        )
        yield Footer()

    def on_mount(self) -> None:
        self._render_logs()

    def on_select_changed(self, event: Select.Changed) -> None:  # pyright: ignore[reportUnknownMemberType]
        if event.select.id == "level-select":
            self._level_filter = str(event.value)
            self._render_logs()

    def _render_logs(self) -> None:
        events = list(read_log(self._workspace_path))
        if self._level_filter != "all":
            events = [e for e in events if e.level == self._level_filter]
        lines = [_format_event(e) for e in events[-200:]]
        body = "\n".join(lines) if lines else "[dim]No log entries[/dim]"
        self._log_body.update(body)
