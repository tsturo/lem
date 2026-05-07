# pyright: strict
"""Workspace file browser."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import DirectoryTree, Footer, Header


class TreeScreen(Screen[None]):  # pyright: ignore[reportMissingTypeArgument]
    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("o", "open_editor", "Open in $EDITOR"),
        Binding("b", "open_obsidian", "Open in Obsidian"),
    ]

    def __init__(self, workspace_path: Path) -> None:
        super().__init__()
        self._workspace_path = workspace_path
        self._selected_path: Path | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield DirectoryTree(str(self._workspace_path))
        yield Footer()

    def on_directory_tree_file_selected(
        self, event: DirectoryTree.FileSelected
    ) -> None:
        self._selected_path = Path(str(event.path))

    def action_open_editor(self) -> None:
        if self._selected_path is None:
            return
        editor = os.environ.get("EDITOR", "vi")
        with self.app.suspend():  # pyright: ignore[reportUnknownMemberType] # textual App type param
            subprocess.run([editor, str(self._selected_path)], check=False)  # noqa: S603

    def action_open_obsidian(self) -> None:
        if self._selected_path is None:
            return
        uri = f"obsidian://open?path={self._selected_path}"
        subprocess.run(["open", uri], check=False)  # noqa: S603
