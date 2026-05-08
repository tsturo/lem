# pyright: strict
"""Integration tests for Task 9.3: control protocol."""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

from lem.control import read_control
from lem.tui import controls


def _write_state(workspace: Path) -> None:
    meta = workspace / "meta"
    meta.mkdir(parents=True, exist_ok=True)
    (meta / "state.json").write_text(
        json.dumps({
            "run_id": "test-run",
            "workspace_path": str(workspace),
            "phase": "Discover",
            "status": "running",
            "started_at": time.time(),
            "last_event_at": time.time(),
            "cost_so_far": 0.0,
            "error": None,
        }),
        encoding="utf-8",
    )


def test_controls_pause_writes_control_json(tmp_path: Path) -> None:
    controls.pause(tmp_path)
    ctrl = read_control(tmp_path)
    assert ctrl is not None
    assert ctrl.action == "pause"


def test_controls_resume_writes_control_json(tmp_path: Path) -> None:
    controls.resume(tmp_path)
    ctrl = read_control(tmp_path)
    assert ctrl is not None
    assert ctrl.action == "resume"


def test_controls_cancel_confirmed_writes_control_json(tmp_path: Path) -> None:
    controls.cancel(tmp_path, confirmed=True)
    ctrl = read_control(tmp_path)
    assert ctrl is not None
    assert ctrl.action == "cancel"


def test_controls_cancel_not_confirmed_does_not_write(tmp_path: Path) -> None:
    controls.cancel(tmp_path, confirmed=False)
    ctrl = read_control(tmp_path)
    assert ctrl is None


def test_controls_kill_worker_writes_control_json(tmp_path: Path) -> None:
    controls.kill_worker(tmp_path, "market-123")
    ctrl_path = tmp_path / "meta" / "control.json"
    assert ctrl_path.exists()
    data = json.loads(ctrl_path.read_text(encoding="utf-8"))
    assert data["action"] == "cancel"
    assert data["target"] == "market-123"


def test_p_key_writes_pause(tmp_path: Path) -> None:
    from lem.tui.app import LemApp

    _write_state(tmp_path)

    async def run() -> None:
        app = LemApp(tmp_path, refresh_interval_s=9999.0)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await pilot.press("p")
            await pilot.pause()

    asyncio.run(run())
    ctrl = read_control(tmp_path)
    assert ctrl is not None
    assert ctrl.action == "pause"


def test_r_key_writes_resume(tmp_path: Path) -> None:
    from lem.tui.app import LemApp

    _write_state(tmp_path)

    async def run() -> None:
        app = LemApp(tmp_path, refresh_interval_s=9999.0)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await pilot.press("r")
            await pilot.pause()

    asyncio.run(run())
    ctrl = read_control(tmp_path)
    assert ctrl is not None
    assert ctrl.action == "resume"


def test_c_key_shows_cancel_modal(tmp_path: Path) -> None:
    from lem.tui.app import LemApp
    from lem.tui.cancel_modal import CancelModal

    _write_state(tmp_path)

    async def run() -> bool:
        app = LemApp(tmp_path, refresh_interval_s=9999.0)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await pilot.press("c")
            await pilot.pause()
            return isinstance(app.screen, CancelModal)

    result = asyncio.run(run())
    assert result
