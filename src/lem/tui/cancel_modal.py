# pyright: strict
"""Confirmation modal for cancel action."""

from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label

from lem.tui import controls


class CancelModal(ModalScreen[None]):  # pyright: ignore[reportMissingTypeArgument]
    BINDINGS = [Binding("escape", "dismiss", "Cancel")]

    def __init__(self, workspace_path: Path) -> None:
        super().__init__()
        self._workspace_path = workspace_path

    def compose(self) -> ComposeResult:
        yield Vertical(
            Label("[bold red]Cancel run?[/bold red]"),
            Label("This will write a cancel control action. Press Y to confirm."),
            Button("Yes, cancel", id="confirm", variant="error"),
            Button("No, go back", id="dismiss_btn"),
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm":
            controls.cancel(self._workspace_path, confirmed=True)
        self.dismiss()
