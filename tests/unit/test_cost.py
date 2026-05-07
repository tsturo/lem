# pyright: strict
"""Tests for state/cost.py and state/timeline.py."""

import json
import threading
import time
from pathlib import Path

import pytest

from lem.state.cost import (
    RATES,
    reset_rates_cache,
    aggregate_phase,
    append_cost,
    compute_cost,
    phase_total,
    read_cost,
    run_total,
)
from lem.state.events import write_event
from lem.state.timeline import TimelineEvent, append_timeline, read_timeline
from lem.types import CostEvent


def _make_cost_event(
    *,
    run_id: str = "run-1",
    phase: str = "discover",
    role: str = "planner",
    model: str = "sonnet",
    tokens_in: int = 100,
    tokens_out: int = 50,
    cost_usd: float = 0.001,
    duration_s: float = 1.0,
    timestamp: float = 1000.0,
    attempt: int = 1,
) -> CostEvent:
    return CostEvent(
        run_id=run_id,
        phase=phase,
        role=role,
        model=model,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost_usd=cost_usd,
        duration_s=duration_s,
        timestamp=timestamp,
        attempt=attempt,
    )


# ── compute_cost ──────────────────────────────────────────────────────────────


def test_compute_cost_haiku() -> None:
    rate_in, rate_out = RATES["haiku"]
    expected = 200 * rate_in + 100 * rate_out
    assert compute_cost(model="haiku", tokens_in=200, tokens_out=100) == pytest.approx(expected)


def test_compute_cost_sonnet() -> None:
    rate_in, rate_out = RATES["sonnet"]
    expected = 1000 * rate_in + 500 * rate_out
    assert compute_cost(model="sonnet", tokens_in=1000, tokens_out=500) == pytest.approx(expected)


def test_compute_cost_opus() -> None:
    rate_in, rate_out = RATES["opus"]
    expected = 500 * rate_in + 250 * rate_out
    assert compute_cost(model="opus", tokens_in=500, tokens_out=250) == pytest.approx(expected)


def test_compute_cost_unknown_model_returns_zero(
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = compute_cost(model="nonexistent-model", tokens_in=100, tokens_out=50)
    assert result == 0.0
    captured = capsys.readouterr()
    assert "nonexistent-model" in captured.err


# ── rate table sanity ─────────────────────────────────────────────────────────


def test_rates_opus_greater_than_sonnet_greater_than_haiku() -> None:
    assert RATES["opus"][0] > RATES["sonnet"][0] > RATES["haiku"][0]
    assert RATES["opus"][1] > RATES["sonnet"][1] > RATES["haiku"][1]


# ── LEM_RATES_FILE override ───────────────────────────────────────────────────


def test_rates_file_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    custom = {"haiku": [0.000002, 0.000010], "sonnet": [0.000006, 0.000030], "opus": [0.000030, 0.000150]}
    rates_file = tmp_path / "rates.json"
    rates_file.write_text(json.dumps(custom), encoding="utf-8")
    monkeypatch.setenv("LEM_RATES_FILE", str(rates_file))
    reset_rates_cache()
    try:
        result = compute_cost(model="haiku", tokens_in=1_000_000, tokens_out=0)
        assert result == pytest.approx(2.0)
    finally:
        reset_rates_cache()


# ── append_cost / read_cost round-trip ────────────────────────────────────────


def test_append_cost_read_cost_roundtrip(tmp_path: Path) -> None:
    event = _make_cost_event()
    append_cost(tmp_path, event)
    result = list(read_cost(tmp_path))
    assert len(result) == 1
    assert result[0] == event


def test_append_cost_jsonl_format(tmp_path: Path) -> None:
    for i in range(5):
        append_cost(tmp_path, _make_cost_event(role=f"role-{i}"))
    lines = (tmp_path / "meta" / "cost.jsonl").read_text().splitlines()
    assert len(lines) == 5
    for line in lines:
        json.loads(line)  # must not raise


def test_cost_event_fields_preserved(tmp_path: Path) -> None:
    event = _make_cost_event(
        run_id="run-xyz",
        phase="synthesize",
        role="critic",
        model="opus",
        tokens_in=999,
        tokens_out=777,
        cost_usd=0.123,
        duration_s=4.5,
        timestamp=9999.9,
        attempt=3,
    )
    append_cost(tmp_path, event)
    restored = list(read_cost(tmp_path))[0]
    assert restored.run_id == event.run_id
    assert restored.phase == event.phase
    assert restored.role == event.role
    assert restored.model == event.model
    assert restored.tokens_in == event.tokens_in
    assert restored.tokens_out == event.tokens_out
    assert restored.cost_usd == pytest.approx(event.cost_usd)
    assert restored.duration_s == pytest.approx(event.duration_s)
    assert restored.timestamp == pytest.approx(event.timestamp)
    assert restored.attempt == event.attempt


# ── aggregate_phase ───────────────────────────────────────────────────────────


def _write_event_payload(
    workspace_path: Path,
    *,
    phase: str,
    role: str,
    tokens_in: int = 100,
    tokens_out: int = 50,
    model: str = "sonnet",
    duration_s: float = 1.0,
    attempt: int = 1,
    timestamp: float = 0.0,
) -> None:
    write_event(
        workspace_path,
        phase=phase,
        role=role,
        payload={
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "model": model,
            "duration_s": duration_s,
            "attempt": attempt,
            "timestamp": timestamp,
        },
    )


def test_aggregate_phase_returns_correct_count(tmp_path: Path) -> None:
    for i in range(3):
        _write_event_payload(tmp_path, phase="discover", role=f"worker-{i}")
    for i in range(2):
        _write_event_payload(tmp_path, phase="synthesize", role=f"worker-{i}")

    results = aggregate_phase(tmp_path, "discover", "run-1")
    assert len(results) == 3
    events = list(read_cost(tmp_path))
    assert len(events) == 3


def test_aggregate_phase_preserves_hyphenated_roles(tmp_path: Path) -> None:
    """Regression: role names with hyphens (cross-skeptic, kill-case-skeptic) must
    round-trip without truncation. Earlier filename-only parse split on '-' and
    took parts[1], silently dropping everything after the first hyphen."""
    _write_event_payload(tmp_path, phase="critique", role="cross-skeptic")
    _write_event_payload(tmp_path, phase="critique", role="kill-case-skeptic")
    _write_event_payload(tmp_path, phase="critique", role="branch-skeptic")

    results = aggregate_phase(tmp_path, "critique", "run-1")
    roles = {e.role for e in results}
    assert roles == {"cross-skeptic", "kill-case-skeptic", "branch-skeptic"}


def test_aggregate_phase_only_matches_requested_phase(tmp_path: Path) -> None:
    _write_event_payload(tmp_path, phase="discover", role="alpha")
    _write_event_payload(tmp_path, phase="synthesize", role="beta")
    _write_event_payload(tmp_path, phase="discover", role="gamma")

    results = aggregate_phase(tmp_path, "discover", "run-1")
    assert len(results) == 2
    assert all(e.phase == "discover" for e in results)


def test_aggregate_both_phases(tmp_path: Path) -> None:
    for i in range(3):
        _write_event_payload(tmp_path, phase="discover", role=f"w-{i}")
    for i in range(2):
        _write_event_payload(tmp_path, phase="synthesize", role=f"w-{i}")

    aggregate_phase(tmp_path, "discover", "run-1")
    aggregate_phase(tmp_path, "synthesize", "run-1")

    all_events = list(read_cost(tmp_path))
    assert len(all_events) == 5
    discover_events = [e for e in all_events if e.phase == "discover"]
    synthesize_events = [e for e in all_events if e.phase == "synthesize"]
    assert len(discover_events) == 3
    assert len(synthesize_events) == 2


# ── phase_total / run_total ───────────────────────────────────────────────────


def test_phase_total_sums_correctly(tmp_path: Path) -> None:
    append_cost(tmp_path, _make_cost_event(phase="p1", cost_usd=0.10))
    append_cost(tmp_path, _make_cost_event(phase="p1", cost_usd=0.20))
    append_cost(tmp_path, _make_cost_event(phase="p2", cost_usd=0.50))
    assert phase_total(tmp_path, "p1") == pytest.approx(0.30)
    assert phase_total(tmp_path, "p2") == pytest.approx(0.50)


def test_run_total_sums_all(tmp_path: Path) -> None:
    append_cost(tmp_path, _make_cost_event(phase="p1", cost_usd=0.10))
    append_cost(tmp_path, _make_cost_event(phase="p2", cost_usd=0.25))
    append_cost(tmp_path, _make_cost_event(phase="p3", cost_usd=0.05))
    assert run_total(tmp_path) == pytest.approx(0.40)


# ── concurrent append_cost ────────────────────────────────────────────────────


def test_append_cost_concurrent_safe(tmp_path: Path) -> None:
    errors: list[str] = []

    def worker(tid: int) -> None:
        for i in range(100):
            try:
                append_cost(tmp_path, _make_cost_event(role=f"w-{tid}-{i}"))
            except Exception as exc:
                errors.append(str(exc))

    threads = [threading.Thread(target=worker, args=(t,)) for t in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == []
    lines = (tmp_path / "meta" / "cost.jsonl").read_text().splitlines()
    assert len(lines) == 500
    for line in lines:
        json.loads(line)  # must not raise


# ── read_cost skips malformed lines ──────────────────────────────────────────


def test_read_cost_skips_malformed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    append_cost(tmp_path, _make_cost_event(role="good-1"))
    append_cost(tmp_path, _make_cost_event(role="good-2"))
    cost_path = tmp_path / "meta" / "cost.jsonl"
    with cost_path.open("a") as fh:
        fh.write("NOT VALID JSON\n")
    append_cost(tmp_path, _make_cost_event(role="good-3"))
    result = list(read_cost(tmp_path))
    assert len(result) == 3
    captured = capsys.readouterr()
    assert "malformed" in captured.err.lower() or "cost.jsonl" in captured.err


# ── timeline round-trip ───────────────────────────────────────────────────────


def test_append_timeline_roundtrip(tmp_path: Path) -> None:
    event = TimelineEvent(
        run_id="run-1",
        phase="discover",
        role="planner",
        started_at=1000.0,
        ended_at=1005.0,
        duration_s=5.0,
        attempt=1,
    )
    append_timeline(tmp_path, event)
    result = list(read_timeline(tmp_path))
    assert len(result) == 1
    r = result[0]
    assert r.run_id == event.run_id
    assert r.phase == event.phase
    assert r.role == event.role
    assert r.started_at == pytest.approx(event.started_at)
    assert r.ended_at == pytest.approx(event.ended_at)
    assert r.duration_s == pytest.approx(event.duration_s)
    assert r.attempt == event.attempt
