# pyright: strict
"""Tests for state/run_state.py, state/events.py, state/log.py."""

import json
import re
import threading
import time
from pathlib import Path

import pytest

from lem.state.events import write_event
from lem.state.log import append_log, read_log
from lem.state.run_state import read_state, update_state, write_state
from lem.types import LogEvent, RunState


def _make_state(workspace_path: Path) -> RunState:
    return RunState(
        run_id="test-run-1",
        workspace_path=workspace_path,
        phase="intake",
        status="running",
        started_at=1000.0,
        last_event_at=1001.0,
        cost_so_far=0.05,
        error=None,
    )


def _make_log_event(event: str = "test.event") -> LogEvent:
    return LogEvent(
        timestamp=time.time(),
        level="info",
        event=event,
        phase="intake",
        role="planner",
        message="hello",
        extra={"k": "v"},
    )


# ── run_state tests ──────────────────────────────────────────────────────────


def test_state_roundtrip(tmp_path: Path) -> None:
    state = _make_state(tmp_path)
    write_state(state)
    restored = read_state(tmp_path)
    assert restored.run_id == state.run_id
    assert restored.workspace_path == state.workspace_path
    assert restored.phase == state.phase
    assert restored.status == state.status
    assert restored.started_at == state.started_at
    assert restored.last_event_at == state.last_event_at
    assert restored.cost_so_far == state.cost_so_far
    assert restored.error == state.error


def test_state_atomic_concurrent(tmp_path: Path) -> None:
    state = _make_state(tmp_path)
    write_state(state)
    stop = threading.Event()
    errors: list[str] = []

    def reader() -> None:
        while not stop.is_set():
            try:
                read_state(tmp_path)
            except FileNotFoundError:
                pass
            except ValueError as exc:
                errors.append(str(exc))

    def writer() -> None:
        for i in range(100):
            s = _make_state(tmp_path)
            s.cost_so_far = float(i)
            write_state(s)
            time.sleep(0.001)

    t_reader = threading.Thread(target=reader)
    t_writer = threading.Thread(target=writer)
    t_reader.start()
    t_writer.start()
    t_writer.join()
    stop.set()
    t_reader.join()
    assert errors == [], f"Reader saw corrupt state: {errors}"


def test_state_corrupt_raises_value_error(tmp_path: Path) -> None:
    meta = tmp_path / "meta"
    meta.mkdir()
    (meta / "state.json").write_text("not json at all {{{", encoding="utf-8")
    with pytest.raises(ValueError, match="corrupt"):
        read_state(tmp_path)


def test_state_missing_raises_file_not_found(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        read_state(tmp_path)


def test_state_schema_fields(tmp_path: Path) -> None:
    state = _make_state(tmp_path)
    write_state(state)
    raw = json.loads((tmp_path / "meta" / "state.json").read_text())
    assert isinstance(raw["run_id"], str)
    assert isinstance(raw["workspace_path"], str)
    assert isinstance(raw["phase"], str)
    assert isinstance(raw["status"], str)
    assert isinstance(raw["started_at"], float)
    assert isinstance(raw["last_event_at"], float)
    assert isinstance(raw["cost_so_far"], float)
    assert raw["error"] is None
    assert len(raw) == 8


def test_state_creates_meta_dir(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    state = _make_state(workspace)
    write_state(state)
    assert (workspace / "meta" / "state.json").exists()


def test_update_state_persists(tmp_path: Path) -> None:
    state = _make_state(tmp_path)
    write_state(state)
    updated = update_state(tmp_path, phase="review")
    assert updated.phase == "review"
    restored = read_state(tmp_path)
    assert restored.phase == "review"


def test_state_path_roundtrip_is_path(tmp_path: Path) -> None:
    state = _make_state(tmp_path)
    write_state(state)
    restored = read_state(tmp_path)
    assert isinstance(restored.workspace_path, Path)


# ── events tests ─────────────────────────────────────────────────────────────


def test_write_event_creates_events_dir(tmp_path: Path) -> None:
    write_event(tmp_path, phase="intake", role="planner", payload={"x": 1})
    assert (tmp_path / "meta" / "events").is_dir()


def test_write_event_filename_format(tmp_path: Path) -> None:
    path = write_event(tmp_path, phase="intake", role="planner", payload={})
    assert re.match(r"intake-planner-\d+(-[0-9a-f]{6})?\.json$", path.name)


def test_write_event_collision_handling(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fixed_ms = 1_700_000_000_000
    call_count = 0

    def fake_time_ns() -> int:
        nonlocal call_count
        call_count += 1
        return fixed_ms * 1_000_000

    monkeypatch.setattr(time, "time_ns", fake_time_ns)
    p1 = write_event(tmp_path, phase="intake", role="planner", payload={"n": 1})
    p2 = write_event(tmp_path, phase="intake", role="planner", payload={"n": 2})
    assert p1 != p2
    assert p1.exists()
    assert p2.exists()


def test_write_event_payload_roundtrip(tmp_path: Path) -> None:
    payload = {"run_id": "abc", "tokens": 42, "nested": {"k": True}}
    path = write_event(tmp_path, phase="review", role="critic", payload=payload)
    loaded = json.loads(path.read_text())
    assert loaded == payload


# ── log tests ────────────────────────────────────────────────────────────────


def test_append_log_creates_meta_and_file(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    workspace.mkdir()
    append_log(workspace, _make_log_event())
    assert (workspace / "meta" / "log.jsonl").exists()


def test_append_log_one_line_per_call(tmp_path: Path) -> None:
    for i in range(5):
        append_log(tmp_path, _make_log_event(event=f"ev.{i}"))
    lines = (tmp_path / "meta" / "log.jsonl").read_text().splitlines()
    assert len(lines) == 5


def test_append_log_concurrent_no_torn_lines(tmp_path: Path) -> None:
    errors: list[str] = []

    def worker(tid: int) -> None:
        for i in range(100):
            try:
                append_log(tmp_path, _make_log_event(event=f"ev.{tid}.{i}"))
            except Exception as exc:
                errors.append(str(exc))

    threads = [threading.Thread(target=worker, args=(t,)) for t in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == []
    lines = (tmp_path / "meta" / "log.jsonl").read_text().splitlines()
    assert len(lines) == 500
    for line in lines:
        json.loads(line)  # must not raise


def test_read_log_roundtrip(tmp_path: Path) -> None:
    events = [_make_log_event(event=f"ev.{i}") for i in range(3)]
    for ev in events:
        append_log(tmp_path, ev)
    restored = list(read_log(tmp_path))
    assert len(restored) == 3
    for orig, rest in zip(events, restored):
        assert rest.event == orig.event
        assert rest.level == orig.level
        assert rest.phase == orig.phase
        assert rest.message == orig.message


def test_read_log_skips_malformed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    meta = tmp_path / "meta"
    meta.mkdir()
    log_path = meta / "log.jsonl"
    for i in range(3):
        append_log(tmp_path, _make_log_event(event=f"ev.{i}"))
    with log_path.open("a") as fh:
        fh.write("THIS IS NOT JSON\n")
    result = list(read_log(tmp_path))
    assert len(result) == 3
    captured = capsys.readouterr()
    assert "log.jsonl" in captured.err or "malformed" in captured.err.lower()
