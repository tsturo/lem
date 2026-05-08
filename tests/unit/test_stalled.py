# pyright: strict
"""Tests for failure/stalled.py."""

import json
from pathlib import Path

import pytest

from lem.failure.stalled import (
    DEFAULT_BASELINE_S,
    DEFAULT_MULTIPLIER,
    StalledCheck,
    compute_role_medians,
    is_stalled,
)


# ── helpers ───────────────────────────────────────────────────────────────────


def _write_timeline(path: Path, events: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for event in events:
            fh.write(json.dumps(event) + "\n")


def _event(
    role: str,
    duration_s: float,
    *,
    run_id: str = "run-1",
    phase: str = "discover",
) -> dict[str, object]:
    started_at = 1000.0
    return {
        "run_id": run_id,
        "phase": phase,
        "role": role,
        "started_at": started_at,
        "ended_at": started_at + duration_s,
        "duration_s": duration_s,
        "attempt": 1,
    }


# ── compute_role_medians: no runs_dir ─────────────────────────────────────────


def test_compute_role_medians_missing_runs_dir_returns_empty(tmp_path: Path) -> None:
    result = compute_role_medians(tmp_path / "nonexistent")
    assert result == {}


def test_compute_role_medians_empty_runs_dir_returns_empty(tmp_path: Path) -> None:
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    result = compute_role_medians(runs_dir)
    assert result == {}


# ── compute_role_medians: single run ─────────────────────────────────────────


def test_compute_role_medians_one_run_one_role_one_event(tmp_path: Path) -> None:
    runs_dir = tmp_path / "runs"
    _write_timeline(
        runs_dir / "run-1" / "meta" / "timeline.jsonl",
        [_event("alpha", 42.0)],
    )
    result = compute_role_medians(runs_dir)
    assert result == {"alpha": pytest.approx(42.0)}


def test_compute_role_medians_one_run_multiple_roles(tmp_path: Path) -> None:
    runs_dir = tmp_path / "runs"
    _write_timeline(
        runs_dir / "run-1" / "meta" / "timeline.jsonl",
        [_event("alpha", 30.0), _event("beta", 90.0)],
    )
    result = compute_role_medians(runs_dir)
    assert result["alpha"] == pytest.approx(30.0)
    assert result["beta"] == pytest.approx(90.0)


# ── compute_role_medians: multiple runs ───────────────────────────────────────


def test_compute_role_medians_multiple_runs_correct_median(tmp_path: Path) -> None:
    runs_dir = tmp_path / "runs"
    for run_id, duration in [("run-1", 10.0), ("run-2", 20.0), ("run-3", 30.0)]:
        _write_timeline(
            runs_dir / run_id / "meta" / "timeline.jsonl",
            [_event("alpha", duration, run_id=run_id)],
        )
    result = compute_role_medians(runs_dir)
    assert result["alpha"] == pytest.approx(20.0)


def test_compute_role_medians_aggregates_across_runs(tmp_path: Path) -> None:
    runs_dir = tmp_path / "runs"
    _write_timeline(
        runs_dir / "run-1" / "meta" / "timeline.jsonl",
        [
            _event("alpha", 10.0, run_id="run-1"),
            _event("alpha", 20.0, run_id="run-1"),
        ],
    )
    _write_timeline(
        runs_dir / "run-2" / "meta" / "timeline.jsonl",
        [
            _event("alpha", 30.0, run_id="run-2"),
            _event("alpha", 40.0, run_id="run-2"),
        ],
    )
    _write_timeline(
        runs_dir / "run-3" / "meta" / "timeline.jsonl",
        [
            _event("alpha", 50.0, run_id="run-3"),
            _event("alpha", 60.0, run_id="run-3"),
        ],
    )
    result = compute_role_medians(runs_dir)
    # 6 samples: 10, 20, 30, 40, 50, 60 → median of sorted list = (30+40)/2 = 35
    assert result["alpha"] == pytest.approx(35.0)


def test_compute_role_medians_multiple_runs_multiple_roles(tmp_path: Path) -> None:
    runs_dir = tmp_path / "runs"
    _write_timeline(
        runs_dir / "run-1" / "meta" / "timeline.jsonl",
        [_event("alpha", 10.0, run_id="run-1"), _event("beta", 100.0, run_id="run-1")],
    )
    _write_timeline(
        runs_dir / "run-2" / "meta" / "timeline.jsonl",
        [_event("alpha", 30.0, run_id="run-2"), _event("beta", 200.0, run_id="run-2")],
    )
    result = compute_role_medians(runs_dir)
    assert result["alpha"] == pytest.approx(20.0)
    assert result["beta"] == pytest.approx(150.0)


# ── compute_role_medians: malformed / missing files ───────────────────────────


def test_compute_role_medians_ignores_malformed_lines(tmp_path: Path) -> None:
    runs_dir = tmp_path / "runs"
    timeline_path = runs_dir / "run-1" / "meta" / "timeline.jsonl"
    timeline_path.parent.mkdir(parents=True, exist_ok=True)
    with timeline_path.open("w") as fh:
        fh.write("not valid json\n")
        fh.write(json.dumps(_event("alpha", 55.0)) + "\n")
    result = compute_role_medians(runs_dir)
    assert result["alpha"] == pytest.approx(55.0)


def test_compute_role_medians_tolerates_fully_malformed_file(tmp_path: Path) -> None:
    runs_dir = tmp_path / "runs"
    timeline_path = runs_dir / "run-1" / "meta" / "timeline.jsonl"
    timeline_path.parent.mkdir(parents=True, exist_ok=True)
    with timeline_path.open("w") as fh:
        fh.write("garbage\n")
    result = compute_role_medians(runs_dir)
    assert result == {}


def test_compute_role_medians_custom_baseline_not_applied_to_known_roles(
    tmp_path: Path,
) -> None:
    runs_dir = tmp_path / "runs"
    _write_timeline(
        runs_dir / "run-1" / "meta" / "timeline.jsonl",
        [_event("alpha", 99.0)],
    )
    result = compute_role_medians(runs_dir, baseline_s=999.0)
    assert result["alpha"] == pytest.approx(99.0)


# ── compute_role_medians: edge cases ─────────────────────────────────────────


def test_compute_role_medians_one_sample_median_is_that_sample(tmp_path: Path) -> None:
    runs_dir = tmp_path / "runs"
    _write_timeline(
        runs_dir / "run-1" / "meta" / "timeline.jsonl",
        [_event("alpha", 77.0)],
    )
    assert compute_role_medians(runs_dir)["alpha"] == pytest.approx(77.0)


def test_compute_role_medians_all_same_duration(tmp_path: Path) -> None:
    runs_dir = tmp_path / "runs"
    events = [_event("alpha", 50.0, run_id="run-1") for _ in range(5)]
    _write_timeline(runs_dir / "run-1" / "meta" / "timeline.jsonl", events)
    assert compute_role_medians(runs_dir)["alpha"] == pytest.approx(50.0)


# ── is_stalled: stalled ───────────────────────────────────────────────────────


def test_is_stalled_true_when_elapsed_exceeds_threshold() -> None:
    medians = {"alpha": 100.0}
    result = is_stalled(role="alpha", elapsed_s=301.0, medians=medians)
    assert result.stalled is True


def test_is_stalled_false_when_elapsed_below_threshold() -> None:
    medians = {"alpha": 100.0}
    result = is_stalled(role="alpha", elapsed_s=299.0, medians=medians)
    assert result.stalled is False


def test_is_stalled_false_at_exact_threshold() -> None:
    # strict greater-than: elapsed == threshold is NOT stalled
    medians = {"alpha": 100.0}
    result = is_stalled(role="alpha", elapsed_s=300.0, medians=medians)
    assert result.stalled is False


# ── is_stalled: unknown role ──────────────────────────────────────────────────


def test_is_stalled_unknown_role_uses_baseline() -> None:
    result = is_stalled(role="unknown", elapsed_s=1.0, medians={})
    assert result.median_s == pytest.approx(DEFAULT_BASELINE_S)
    assert result.threshold_s == pytest.approx(DEFAULT_BASELINE_S * DEFAULT_MULTIPLIER)
    assert result.stalled is False


def test_is_stalled_unknown_role_custom_baseline() -> None:
    result = is_stalled(role="x", elapsed_s=1000.0, medians={}, baseline_s=200.0)
    assert result.median_s == pytest.approx(200.0)
    assert result.threshold_s == pytest.approx(600.0)
    assert result.stalled is True


# ── is_stalled: return type and fields ───────────────────────────────────────


def test_is_stalled_returns_stalled_check_instance() -> None:
    result = is_stalled(role="alpha", elapsed_s=0.0, medians={"alpha": 10.0})
    assert isinstance(result, StalledCheck)


def test_is_stalled_all_fields_populated() -> None:
    medians = {"alpha": 40.0}
    result = is_stalled(role="alpha", elapsed_s=50.0, medians=medians, multiplier=2.0)
    assert result.median_s == pytest.approx(40.0)
    assert result.threshold_s == pytest.approx(80.0)
    assert result.stalled is False


def test_is_stalled_custom_multiplier() -> None:
    medians = {"alpha": 10.0}
    result = is_stalled(role="alpha", elapsed_s=21.0, medians=medians, multiplier=2.0)
    assert result.threshold_s == pytest.approx(20.0)
    assert result.stalled is True
