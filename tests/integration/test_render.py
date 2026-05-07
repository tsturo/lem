"""Integration tests for `lem render` (Task 8.4)."""

from __future__ import annotations

import time
from pathlib import Path

import pytest
from typer.testing import CliRunner

from lem.cli import app
from lem.state.run_state import write_state
from lem.types import RunState


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


def _make_workspace(tmp_path: Path, *, with_summary: bool = True) -> Path:
    ws = tmp_path / "2026-01-01-1200-coffee-abc123"
    ws.mkdir()
    state = RunState(
        run_id=ws.name,
        workspace_path=ws,
        phase="synthesize",
        status="completed",  # type: ignore[arg-type]
        started_at=time.time() - 120,
        last_event_at=time.time(),
        cost_so_far=1.23,
        error=None,
    )
    write_state(state)
    if with_summary:
        deliverables = ws / "deliverables"
        deliverables.mkdir()
        (deliverables / "executive-summary.md").write_text(
            "# Executive Summary\n\nThis is a **great** idea.\n\n## Verdict\n\nBuild it.",
            encoding="utf-8",
        )
    return ws


def test_render_produces_html_file(runner: CliRunner, tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    from unittest.mock import patch
    with patch("lem.commands.render.resolve_workspace", return_value=ws):
        result = runner.invoke(app, ["render", ws.name])
    assert result.exit_code == 0
    report = ws / "report.html"
    assert report.exists()


def test_render_html_contains_run_id(runner: CliRunner, tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    from unittest.mock import patch
    with patch("lem.commands.render.resolve_workspace", return_value=ws):
        runner.invoke(app, ["render", ws.name])
    html = (ws / "report.html").read_text(encoding="utf-8")
    assert ws.name in html


def test_render_html_no_external_urls(runner: CliRunner, tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    from unittest.mock import patch
    with patch("lem.commands.render.resolve_workspace", return_value=ws):
        runner.invoke(app, ["render", ws.name])
    html = (ws / "report.html").read_text(encoding="utf-8")
    # No CDN or external script/link tags
    assert "cdn." not in html
    assert "unpkg.com" not in html
    assert "<script src=" not in html
    assert '<link rel="stylesheet" href="http' not in html


def test_render_html_contains_executive_summary_content(runner: CliRunner, tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    from unittest.mock import patch
    with patch("lem.commands.render.resolve_workspace", return_value=ws):
        runner.invoke(app, ["render", ws.name])
    html = (ws / "report.html").read_text(encoding="utf-8")
    assert "Executive Summary" in html
    assert "great" in html


def test_render_custom_output_path(runner: CliRunner, tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    out = tmp_path / "custom-report.html"
    from unittest.mock import patch
    with patch("lem.commands.render.resolve_workspace", return_value=ws):
        result = runner.invoke(app, ["render", ws.name, "-o", str(out)])
    assert result.exit_code == 0
    assert out.exists()


def test_render_missing_run_exits_nonzero(runner: CliRunner, tmp_path: Path) -> None:
    from unittest.mock import patch
    with patch("lem.commands.render.resolve_workspace", return_value=tmp_path / "ghost-run"):
        result = runner.invoke(app, ["render", "ghost-run"])
    assert result.exit_code != 0


def test_render_html_contains_cost(runner: CliRunner, tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    from unittest.mock import patch
    with patch("lem.commands.render.resolve_workspace", return_value=ws):
        runner.invoke(app, ["render", ws.name])
    html = (ws / "report.html").read_text(encoding="utf-8")
    assert "1.23" in html


def test_render_html_without_summary(runner: CliRunner, tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path, with_summary=False)
    from unittest.mock import patch
    with patch("lem.commands.render.resolve_workspace", return_value=ws):
        result = runner.invoke(app, ["render", ws.name])
    assert result.exit_code == 0
    html = (ws / "report.html").read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in html


def test_md_to_html_headings() -> None:
    from lem.render.report import _md_to_html
    html = _md_to_html("# Title\n\n## Section\n\nParagraph text.")
    assert "<h1>" in html
    assert "<h2>" in html
    assert "<p>" in html


def test_md_to_html_bold_italic() -> None:
    from lem.render.report import _md_to_html
    html = _md_to_html("**bold** and *italic*")
    assert "<strong>bold</strong>" in html
    assert "<em>italic</em>" in html


def test_md_to_html_escapes_html() -> None:
    from lem.render.report import _md_to_html
    html = _md_to_html("x < y & z > w")
    assert "&lt;" in html
    assert "&amp;" in html
    assert "&gt;" in html
