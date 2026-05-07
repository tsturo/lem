# pyright: strict
"""Integration tests for Task 9.2: drill-down panes."""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path


def _write_state(workspace: Path, *, status: str = "running", phase: str = "Discover") -> None:
    meta = workspace / "meta"
    meta.mkdir(parents=True, exist_ok=True)
    (meta / "state.json").write_text(
        json.dumps({
            "run_id": "test-run",
            "workspace_path": str(workspace),
            "phase": phase,
            "status": status,
            "started_at": time.time(),
            "last_event_at": time.time(),
            "cost_so_far": 0.0,
            "error": None,
        }),
        encoding="utf-8",
    )


def test_worker_screen_renders(tmp_path: Path) -> None:
    from lem.tui.app import LemApp
    from lem.tui.worker_view import WorkerScreen

    _write_state(tmp_path)

    async def run() -> None:
        app = LemApp(tmp_path, refresh_interval_s=9999.0)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await app.push_screen(WorkerScreen(tmp_path, "market", "Discover"))
            await pilot.pause()
            assert isinstance(app.screen, WorkerScreen)

    asyncio.run(run())


def test_worker_screen_escape_returns(tmp_path: Path) -> None:
    from lem.tui.app import LemApp
    from lem.tui.worker_view import WorkerScreen

    _write_state(tmp_path)

    async def run() -> None:
        app = LemApp(tmp_path, refresh_interval_s=9999.0)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await app.push_screen(WorkerScreen(tmp_path, "market", "Discover"))
            await pilot.pause()
            await pilot.press("escape")
            await pilot.pause()
            assert not isinstance(app.screen, WorkerScreen)

    asyncio.run(run())


def test_phase_screen_renders(tmp_path: Path) -> None:
    from lem.tui.app import LemApp
    from lem.tui.phase_view import PhaseScreen

    _write_state(tmp_path)

    async def run() -> None:
        app = LemApp(tmp_path, refresh_interval_s=9999.0)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await app.push_screen(PhaseScreen(tmp_path, "Discover"))
            await pilot.pause()
            assert isinstance(app.screen, PhaseScreen)

    asyncio.run(run())


def test_phase_screen_escape_returns(tmp_path: Path) -> None:
    from lem.tui.app import LemApp
    from lem.tui.phase_view import PhaseScreen

    _write_state(tmp_path)

    async def run() -> None:
        app = LemApp(tmp_path, refresh_interval_s=9999.0)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await app.push_screen(PhaseScreen(tmp_path, "Discover"))
            await pilot.pause()
            await pilot.press("escape")
            await pilot.pause()
            assert not isinstance(app.screen, PhaseScreen)

    asyncio.run(run())


def test_artifact_screen_renders_existing_file(tmp_path: Path) -> None:
    from lem.tui.app import LemApp
    from lem.tui.artifact_view import ArtifactScreen

    _write_state(tmp_path)
    artifact = tmp_path / "decision.md"
    artifact.write_text("# Decision\n\nSome content here.", encoding="utf-8")

    async def run() -> None:
        app = LemApp(tmp_path, refresh_interval_s=9999.0)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await app.push_screen(ArtifactScreen(artifact))
            await pilot.pause()
            assert isinstance(app.screen, ArtifactScreen)

    asyncio.run(run())


def test_artifact_screen_missing_file(tmp_path: Path) -> None:
    from lem.tui.app import LemApp
    from lem.tui.artifact_view import ArtifactScreen

    _write_state(tmp_path)
    missing = tmp_path / "nonexistent.md"

    async def run() -> None:
        app = LemApp(tmp_path, refresh_interval_s=9999.0)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await app.push_screen(ArtifactScreen(missing))
            await pilot.pause()
            assert isinstance(app.screen, ArtifactScreen)

    asyncio.run(run())


def test_logs_screen_renders(tmp_path: Path) -> None:
    from lem.tui.app import LemApp
    from lem.tui.logs_view import LogsScreen

    _write_state(tmp_path)
    meta = tmp_path / "meta"
    meta.mkdir(parents=True, exist_ok=True)
    line = json.dumps({
        "timestamp": time.time(),
        "level": "info",
        "event": "worker_started",
        "phase": "Discover",
        "role": "market",
        "message": "starting",
        "extra": {},
    })
    (meta / "log.jsonl").write_text(line + "\n", encoding="utf-8")

    async def run() -> None:
        app = LemApp(tmp_path, refresh_interval_s=9999.0)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await app.push_screen(LogsScreen(tmp_path))
            await pilot.pause()
            assert isinstance(app.screen, LogsScreen)

    asyncio.run(run())


def test_logs_screen_escape_returns(tmp_path: Path) -> None:
    from lem.tui.app import LemApp
    from lem.tui.logs_view import LogsScreen

    _write_state(tmp_path)

    async def run() -> None:
        app = LemApp(tmp_path, refresh_interval_s=9999.0)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await app.push_screen(LogsScreen(tmp_path))
            await pilot.pause()
            await pilot.press("escape")
            await pilot.pause()
            assert not isinstance(app.screen, LogsScreen)

    asyncio.run(run())


def test_tree_screen_renders(tmp_path: Path) -> None:
    from lem.tui.app import LemApp
    from lem.tui.tree_view import TreeScreen

    _write_state(tmp_path)
    (tmp_path / "idea.md").write_text("# My idea", encoding="utf-8")

    async def run() -> None:
        app = LemApp(tmp_path, refresh_interval_s=9999.0)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await app.push_screen(TreeScreen(tmp_path))
            await pilot.pause()
            assert isinstance(app.screen, TreeScreen)

    asyncio.run(run())


def test_tree_screen_escape_returns(tmp_path: Path) -> None:
    from lem.tui.app import LemApp
    from lem.tui.tree_view import TreeScreen

    _write_state(tmp_path)

    async def run() -> None:
        app = LemApp(tmp_path, refresh_interval_s=9999.0)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await app.push_screen(TreeScreen(tmp_path))
            await pilot.pause()
            await pilot.press("escape")
            await pilot.pause()
            assert not isinstance(app.screen, TreeScreen)

    asyncio.run(run())
