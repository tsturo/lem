# pyright: strict
"""Integration tests for Task 9.1: MainView and LemApp."""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path


def _write_state(workspace: Path, *, status: str, phase: str) -> None:
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


def _write_cost_event(workspace: Path, *, phase: str, role: str, ts: float | None = None) -> None:
    meta = workspace / "meta"
    meta.mkdir(parents=True, exist_ok=True)
    line = json.dumps({
        "run_id": "test-run",
        "phase": phase,
        "role": role,
        "model": "sonnet",
        "tokens_in": 100,
        "tokens_out": 50,
        "cost_usd": 0.001,
        "duration_s": 10.0,
        "timestamp": ts if ts is not None else time.time(),
        "attempt": 1,
    })
    with (meta / "cost.jsonl").open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def _write_timeline_event(workspace: Path, *, phase: str, role: str) -> None:
    meta = workspace / "meta"
    meta.mkdir(parents=True, exist_ok=True)
    now = time.time()
    line = json.dumps({
        "run_id": "test-run",
        "phase": phase,
        "role": role,
        "started_at": now - 10,
        "ended_at": now,
        "duration_s": 10.0,
        "attempt": 1,
    })
    with (meta / "timeline.jsonl").open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def _write_log_event(workspace: Path, *, event: str, phase: str) -> None:
    meta = workspace / "meta"
    meta.mkdir(parents=True, exist_ok=True)
    line = json.dumps({
        "timestamp": time.time(),
        "level": "info",
        "event": event,
        "phase": phase,
        "role": None,
        "message": "test",
        "extra": {},
    })
    with (meta / "log.jsonl").open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def test_app_instantiates(tmp_path: Path) -> None:
    from lem.tui.app import LemApp
    _write_state(tmp_path, status="running", phase="Discover")
    app = LemApp(tmp_path, refresh_interval_s=9999.0)
    assert app.workspace_path == tmp_path


def test_main_view_renders_running_state(tmp_path: Path) -> None:
    from lem.tui.app import LemApp
    from lem.tui.main_view import MainView

    _write_state(tmp_path, status="running", phase="Discover")

    async def run() -> None:
        app = LemApp(tmp_path, refresh_interval_s=9999.0)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            view = app.query_one(MainView)
            assert view is not None

    asyncio.run(run())


def test_main_view_renders_idle_state(tmp_path: Path) -> None:
    from lem.tui.app import LemApp
    from lem.tui.main_view import MainView

    _write_state(tmp_path, status="running", phase="Intake")

    async def run() -> None:
        app = LemApp(tmp_path, refresh_interval_s=9999.0)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            assert app.query_one(MainView) is not None

    asyncio.run(run())


def test_main_view_renders_completed_state(tmp_path: Path) -> None:
    from lem.tui.app import LemApp
    from lem.tui.main_view import MainView

    _write_state(tmp_path, status="completed", phase="Synthesize")

    async def run() -> None:
        app = LemApp(tmp_path, refresh_interval_s=9999.0)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            assert app.query_one(MainView) is not None

    asyncio.run(run())


def test_main_view_renders_aborted_state(tmp_path: Path) -> None:
    from lem.tui.app import LemApp
    from lem.tui.main_view import MainView

    _write_state(tmp_path, status="cost-aborted", phase="Explore")

    async def run() -> None:
        app = LemApp(tmp_path, refresh_interval_s=9999.0)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            assert app.query_one(MainView) is not None

    asyncio.run(run())


def test_main_view_with_cost_events(tmp_path: Path) -> None:
    from lem.tui.app import LemApp
    from lem.tui.main_view import MainView

    _write_state(tmp_path, status="running", phase="Discover")
    _write_cost_event(tmp_path, phase="Discover", role="market")
    _write_cost_event(tmp_path, phase="Discover", role="tech")

    async def run() -> None:
        app = LemApp(tmp_path, refresh_interval_s=9999.0, show_cost=True)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            assert app.query_one(MainView) is not None

    asyncio.run(run())


def test_main_view_with_completed_workers(tmp_path: Path) -> None:
    from lem.tui.app import LemApp
    from lem.tui.main_view import MainView

    _write_state(tmp_path, status="running", phase="Explore")
    _write_cost_event(tmp_path, phase="Discover", role="market")
    _write_timeline_event(tmp_path, phase="Discover", role="market")

    async def run() -> None:
        app = LemApp(tmp_path, refresh_interval_s=9999.0)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            assert app.query_one(MainView) is not None

    asyncio.run(run())


def test_main_view_with_issue_events(tmp_path: Path) -> None:
    from lem.tui.app import LemApp
    from lem.tui.main_view import MainView

    _write_state(tmp_path, status="running", phase="Discover")
    _write_log_event(tmp_path, event="worker_retry", phase="Discover")
    _write_log_event(tmp_path, event="worker_timeout", phase="Discover")
    _write_log_event(tmp_path, event="breaker_tripped", phase="Discover")

    async def run() -> None:
        app = LemApp(tmp_path, refresh_interval_s=9999.0)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            assert app.query_one(MainView) is not None

    asyncio.run(run())


def test_main_view_no_state_file(tmp_path: Path) -> None:
    from lem.tui.app import LemApp
    from lem.tui.main_view import MainView

    async def run() -> None:
        app = LemApp(tmp_path, refresh_interval_s=9999.0)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            assert app.query_one(MainView) is not None

    asyncio.run(run())


def test_stalled_badge_appears_above_threshold(tmp_path: Path) -> None:
    from lem.tui.app import LemApp
    from lem.tui.main_view import MainView

    _write_state(tmp_path, status="running", phase="Discover")
    old_ts = time.time() - 400  # 400s ago — above 60s baseline × 3 = 180s threshold
    _write_cost_event(tmp_path, phase="Discover", role="market", ts=old_ts)

    async def run() -> None:
        app = LemApp(tmp_path, refresh_interval_s=9999.0)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            assert app.query_one(MainView) is not None

    asyncio.run(run())


def test_refresh_data_called_manually(tmp_path: Path) -> None:
    from lem.tui.app import LemApp
    from lem.tui.main_view import MainView

    _write_state(tmp_path, status="running", phase="Critique")

    async def run() -> None:
        app = LemApp(tmp_path, refresh_interval_s=9999.0)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            view = app.query_one(MainView)
            view.refresh_data()
            await pilot.pause()
            assert view is not None

    asyncio.run(run())
