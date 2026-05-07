# pyright: strict
"""textual App entry."""

from __future__ import annotations

from pathlib import Path

from textual.app import App, ComposeResult
from textual.widgets import Footer, Header

from lem.control import read_control
from lem.tui import controls
from lem.tui.logs_view import LogsScreen
from lem.tui.main_view import MainView
from lem.tui.tree_view import TreeScreen


class LemApp(App[None]):
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("p", "pause", "Pause"),
        ("r", "resume", "Resume"),
        ("c", "cancel", "Cancel"),
        ("l", "logs", "Logs"),
        ("w", "tree", "Workspace"),
        ("escape", "back", "Back"),
    ]

    def __init__(
        self,
        workspace_path: Path,
        *,
        refresh_interval_s: float = 2.0,
        show_cost: bool = False,
    ) -> None:
        super().__init__()
        self.workspace_path = workspace_path
        self.refresh_interval_s = refresh_interval_s
        self.show_cost = show_cost

    def compose(self) -> ComposeResult:
        yield Header()
        yield MainView(self.workspace_path, show_cost=self.show_cost)
        yield Footer()

    def on_mount(self) -> None:
        self.set_interval(self.refresh_interval_s, self._refresh)

    def _refresh(self) -> None:
        self.query_one(MainView).refresh_data()
        self._update_header_subtitle()

    def _update_header_subtitle(self) -> None:
        ctrl = read_control(self.workspace_path)
        if ctrl is not None:
            self.sub_title = f"[{ctrl.action}]"
        else:
            self.sub_title = ""

    def action_pause(self) -> None:
        controls.pause(self.workspace_path)
        self._update_header_subtitle()

    def action_resume(self) -> None:
        controls.resume(self.workspace_path)
        self._update_header_subtitle()

    def action_cancel(self) -> None:
        from lem.tui.cancel_modal import CancelModal
        self.push_screen(CancelModal(self.workspace_path))

    def action_logs(self) -> None:
        self.push_screen(LogsScreen(self.workspace_path))

    def action_tree(self) -> None:
        self.push_screen(TreeScreen(self.workspace_path))

    async def action_back(self) -> None:  # pyright: ignore[reportIncompatibleMethodOverride]
        if len(self.screen_stack) > 1:
            self.pop_screen()
