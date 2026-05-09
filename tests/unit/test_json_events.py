"""Tests for _JsonEventPrinter in lem refine."""

from __future__ import annotations

import io
import json

import pytest

from lem.commands.refine import _JsonEventPrinter
from lem.orchestrator import ProgressEvent


def _capture_events(events: list[ProgressEvent]) -> list[dict]:
    buf = io.StringIO()
    printer = _JsonEventPrinter()

    original_write = None
    import sys

    original_stdout = sys.stdout
    sys.stdout = buf
    try:
        for event in events:
            printer.on_event(event)
    finally:
        sys.stdout = original_stdout

    lines = [line for line in buf.getvalue().splitlines() if line.strip()]
    return [json.loads(line) for line in lines]


def test_phase_start_produces_valid_json() -> None:
    events = [ProgressEvent(kind="phase_start", phase_id="1", roles=("architect", "designer"))]
    records = _capture_events(events)

    assert len(records) == 1
    r = records[0]
    assert r["kind"] == "phase_start"
    assert r["phase_id"] == "1"
    assert r["roles"] == ["architect", "designer"]
    assert r["duration_s"] == 0.0
    assert r["cost_usd"] == 0.0
    assert r["success"] is True
    assert "timestamp" in r
    assert isinstance(r["timestamp"], float)


def test_phase_done_produces_valid_json() -> None:
    events = [
        ProgressEvent(
            kind="phase_done",
            phase_id="2.1",
            roles=("market",),
            duration_s=12.5,
            cost_usd=0.0042,
            success=True,
        )
    ]
    records = _capture_events(events)

    assert len(records) == 1
    r = records[0]
    assert r["kind"] == "phase_done"
    assert r["phase_id"] == "2.1"
    assert r["roles"] == ["market"]
    assert r["duration_s"] == pytest.approx(12.5)
    assert r["cost_usd"] == pytest.approx(0.0042)
    assert r["success"] is True


def test_phase_done_failure_success_false() -> None:
    events = [
        ProgressEvent(
            kind="phase_done",
            phase_id="3",
            success=False,
            duration_s=5.0,
        )
    ]
    records = _capture_events(events)

    assert len(records) == 1
    assert records[0]["success"] is False


def test_phase_skipped_produces_valid_json() -> None:
    events = [ProgressEvent(kind="phase_skipped", phase_id="2.1")]
    records = _capture_events(events)

    assert len(records) == 1
    r = records[0]
    assert r["kind"] == "phase_skipped"
    assert r["phase_id"] == "2.1"
    assert r["roles"] == []


def test_multiple_events_each_on_own_line() -> None:
    events = [
        ProgressEvent(kind="phase_start", phase_id="0.5"),
        ProgressEvent(kind="phase_done", phase_id="0.5", duration_s=3.0),
        ProgressEvent(kind="phase_skipped", phase_id="2.1"),
    ]
    records = _capture_events(events)

    assert len(records) == 3
    assert records[0]["kind"] == "phase_start"
    assert records[1]["kind"] == "phase_done"
    assert records[2]["kind"] == "phase_skipped"


def test_all_required_keys_present() -> None:
    required_keys = {"kind", "phase_id", "roles", "duration_s", "cost_usd", "success", "timestamp"}
    events = [
        ProgressEvent(kind="phase_start", phase_id="1"),
        ProgressEvent(kind="phase_done", phase_id="1", duration_s=1.0),
        ProgressEvent(kind="phase_skipped", phase_id="2.1"),
    ]
    records = _capture_events(events)

    for record in records:
        assert required_keys.issubset(record.keys()), (
            f"Missing keys: {required_keys - record.keys()}"
        )


def test_no_human_readable_output_to_stdout() -> None:
    """JSON printer must not mix human-readable text with JSON lines."""
    buf = io.StringIO()
    printer = _JsonEventPrinter()

    import sys

    original_stdout = sys.stdout
    sys.stdout = buf
    try:
        printer.on_run_start()
        printer.on_event(ProgressEvent(kind="phase_start", phase_id="1"))
        printer.on_run_end(object())
    finally:
        sys.stdout = original_stdout

    lines = [line for line in buf.getvalue().splitlines() if line.strip()]
    for line in lines:
        json.loads(line)  # must not raise — every line must be valid JSON


def test_roles_serialized_as_list_not_tuple() -> None:
    events = [ProgressEvent(kind="phase_start", phase_id="1", roles=("a", "b", "c"))]
    records = _capture_events(events)

    assert isinstance(records[0]["roles"], list)
