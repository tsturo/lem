# pyright: strict
"""Inline rendered markdown."""

from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import ScrollableContainer
from textual.screen import Screen
from textual.widgets import Footer, Header, Markdown


class ArtifactScreen(Screen[None]):  # pyright: ignore[reportMissingTypeArgument]
    BINDINGS = [Binding("escape", "app.pop_screen", "Back")]

    def __init__(self, artifact_path: Path) -> None:
        super().__init__()
        self._artifact_path = artifact_path

    def compose(self) -> ComposeResult:
        yield Header()
        content = self._read_content()
        yield ScrollableContainer(Markdown(content))
        yield Footer()

    def _read_content(self) -> str:
        if not self._artifact_path.exists():
            return f"*File not found: {self._artifact_path}*"
        try:
            return self._artifact_path.read_text(encoding="utf-8")
        except OSError as exc:
            return f"*Error reading file: {exc}*"
