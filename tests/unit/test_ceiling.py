# pyright: strict
"""Tests for failure/ceiling.py."""

from pathlib import Path

import pytest

from lem.failure.ceiling import (
    DEFAULT_MAX_COST_USD,
    DEFAULT_MAX_WALL_CLOCK_S,
    CostProjection,
    check_cost_ceiling,
    check_wall_clock,
    project_worker_cost,
)
from lem.state.cost import RATES
from lem.types import RunState


def _make_state(
    *,
    cost_so_far: float = 0.0,
    started_at: float = 1000.0,
) -> RunState:
    return RunState(
        run_id="run-test",
        workspace_path=Path("/tmp/test-run"),
        phase="discover",
        status="running",
        started_at=started_at,
        last_event_at=started_at,
        cost_so_far=cost_so_far,
        error=None,
    )


# ── project_worker_cost ───────────────────────────────────────────────────────


def test_project_worker_cost_sonnet_arithmetic() -> None:
    rate_in, rate_out = RATES["sonnet"]
    expected = 1000 * rate_in + 500 * rate_out
    result = project_worker_cost(model="sonnet", input_estimate=1000, output_cap=500)
    assert result == pytest.approx(expected)


def test_project_worker_cost_haiku_arithmetic() -> None:
    rate_in, rate_out = RATES["haiku"]
    expected = 2000 * rate_in + 800 * rate_out
    result = project_worker_cost(model="haiku", input_estimate=2000, output_cap=800)
    assert result == pytest.approx(expected)


def test_project_worker_cost_opus_arithmetic() -> None:
    rate_in, rate_out = RATES["opus"]
    expected = 500 * rate_in + 250 * rate_out
    result = project_worker_cost(model="opus", input_estimate=500, output_cap=250)
    assert result == pytest.approx(expected)


def test_project_worker_cost_exact_value_sonnet() -> None:
    rate_in, rate_out = RATES["sonnet"]
    result = project_worker_cost(model="sonnet", input_estimate=1000, output_cap=500)
    assert result == pytest.approx(1000 * rate_in + 500 * rate_out)


# ── check_cost_ceiling: pass-through ─────────────────────────────────────────


def test_check_cost_ceiling_no_breach_under_ceiling() -> None:
    state = _make_state(cost_so_far=1.0)
    projection = check_cost_ceiling(state, 5.0, max_cost=25.0)
    assert projection.breach is False


def test_check_cost_ceiling_returns_correct_fields() -> None:
    state = _make_state(cost_so_far=10.0)
    projection = check_cost_ceiling(state, 3.0, max_cost=20.0)
    assert projection.current_spend == pytest.approx(10.0)
    assert projection.projected_worker_cost == pytest.approx(3.0)
    assert projection.projected_total == pytest.approx(13.0)
    assert projection.max_cost == pytest.approx(20.0)
    assert projection.breach is False


def test_check_cost_ceiling_projected_total_is_sum() -> None:
    state = _make_state(cost_so_far=7.5)
    projection = check_cost_ceiling(state, 2.5, max_cost=25.0)
    assert projection.projected_total == pytest.approx(10.0)


# ── check_cost_ceiling: breach ────────────────────────────────────────────────


def test_check_cost_ceiling_breach_when_projected_total_exceeds_max() -> None:
    state = _make_state(cost_so_far=20.0)
    projection = check_cost_ceiling(state, 10.0, max_cost=25.0)
    assert projection.breach is True


def test_check_cost_ceiling_breach_exact_equal_to_ceiling() -> None:
    # >= semantics: equal to ceiling counts as breach
    state = _make_state(cost_so_far=20.0)
    projection = check_cost_ceiling(state, 5.0, max_cost=25.0)
    assert projection.projected_total == pytest.approx(25.0)
    assert projection.breach is True


def test_check_cost_ceiling_no_breach_just_under_ceiling() -> None:
    state = _make_state(cost_so_far=20.0)
    projection = check_cost_ceiling(state, 4.99, max_cost=25.0)
    assert projection.projected_total == pytest.approx(24.99)
    assert projection.breach is False


# ── check_cost_ceiling: default max_cost ──────────────────────────────────────


def test_check_cost_ceiling_default_max_cost_is_25() -> None:
    assert DEFAULT_MAX_COST_USD == 25.0
    state = _make_state(cost_so_far=0.0)
    projection = check_cost_ceiling(state, 0.0)
    assert projection.max_cost == pytest.approx(25.0)


def test_check_cost_ceiling_default_no_breach_well_under() -> None:
    state = _make_state(cost_so_far=1.0)
    projection = check_cost_ceiling(state, 1.0)
    assert projection.breach is False


# ── check_cost_ceiling: pure / no mutation ────────────────────────────────────


def test_check_cost_ceiling_does_not_mutate_state() -> None:
    state = _make_state(cost_so_far=5.0)
    original_cost = state.cost_so_far
    check_cost_ceiling(state, 100.0, max_cost=25.0)
    assert state.cost_so_far == original_cost


def test_check_cost_ceiling_returns_cost_projection_instance() -> None:
    state = _make_state(cost_so_far=0.0)
    result = check_cost_ceiling(state, 1.0, max_cost=25.0)
    assert isinstance(result, CostProjection)


# ── check_wall_clock: pass-through ───────────────────────────────────────────


def test_check_wall_clock_no_breach_well_under() -> None:
    state = _make_state(started_at=1000.0)
    result = check_wall_clock(state, max_wall_clock_s=3600.0, now=2000.0)
    assert result is False


def test_check_wall_clock_no_breach_just_under() -> None:
    state = _make_state(started_at=1000.0)
    result = check_wall_clock(state, max_wall_clock_s=3600.0, now=4599.99)
    assert result is False


# ── check_wall_clock: breach ─────────────────────────────────────────────────


def test_check_wall_clock_breach_when_elapsed_exceeds_cap() -> None:
    state = _make_state(started_at=1000.0)
    result = check_wall_clock(state, max_wall_clock_s=3600.0, now=5000.0)
    assert result is True


def test_check_wall_clock_breach_exact_at_cap() -> None:
    # >= semantics: elapsed == cap counts as breach
    state = _make_state(started_at=1000.0)
    result = check_wall_clock(state, max_wall_clock_s=3600.0, now=4600.0)
    assert result is True


# ── check_wall_clock: default max_wall_clock_s ───────────────────────────────


def test_check_wall_clock_default_is_4_hours() -> None:
    assert DEFAULT_MAX_WALL_CLOCK_S == 4 * 60 * 60


def test_check_wall_clock_default_no_breach_within_4_hours() -> None:
    state = _make_state(started_at=1000.0)
    # 3 hours elapsed — no breach
    result = check_wall_clock(state, now=1000.0 + 3 * 60 * 60)
    assert result is False


def test_check_wall_clock_default_breach_after_4_hours() -> None:
    state = _make_state(started_at=1000.0)
    result = check_wall_clock(state, now=1000.0 + 4 * 60 * 60 + 1)
    assert result is True


# ── check_wall_clock: now injectable / does not mutate state ─────────────────


def test_check_wall_clock_does_not_mutate_state() -> None:
    state = _make_state(started_at=1000.0)
    original_started = state.started_at
    check_wall_clock(state, max_wall_clock_s=100.0, now=2000.0)
    assert state.started_at == original_started
