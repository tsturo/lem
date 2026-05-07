# pyright: strict
"""Tests for failure/breaker.py — phase-level circuit breaker."""

from __future__ import annotations

from pathlib import Path

import pytest

from lem.failure.breaker import DEFAULT_THRESHOLD, SYNTHESIZE_PHASE_ID, evaluate_phase
from lem.types import WorkerResult


def _ok(*, path: str = "out.json") -> WorkerResult:
    return WorkerResult(
        exit_code=0,
        output_path=Path(path),
        tokens_in=10,
        tokens_out=5,
        cost_usd=0.0,
        duration_s=0.01,
        stop_reason="end_turn",
        schema_valid=True,
        schema_errors=[],
    )


def _fail(*, path: str = "out.json") -> WorkerResult:
    return WorkerResult(
        exit_code=1,
        output_path=Path(path),
        tokens_in=0,
        tokens_out=0,
        cost_usd=0.0,
        duration_s=0.01,
        stop_reason="error",
        schema_valid=False,
        schema_errors=["failed"],
    )


# ---------------------------------------------------------------------------
# 1. Empty results
# ---------------------------------------------------------------------------


def test_empty_results_no_abort() -> None:
    verdict = evaluate_phase("1", [])
    assert verdict.should_abort is False
    assert verdict.total_count == 0
    assert verdict.failed_count == 0
    assert verdict.failure_rate == 0.0


# ---------------------------------------------------------------------------
# 2. 0% failure
# ---------------------------------------------------------------------------


def test_zero_percent_failure_no_abort() -> None:
    results = [_ok(path=f"out{i}.json") for i in range(4)]
    verdict = evaluate_phase("1", results)
    assert verdict.should_abort is False
    assert verdict.failure_rate == 0.0
    assert verdict.failed_count == 0
    assert verdict.total_count == 4


# ---------------------------------------------------------------------------
# 3. 25% failure (1/4) — below threshold
# ---------------------------------------------------------------------------


def test_25_percent_failure_no_abort() -> None:
    results = [_ok(path=f"out{i}.json") for i in range(3)] + [_fail(path="out3.json")]
    verdict = evaluate_phase("1", results)
    assert verdict.should_abort is False
    assert verdict.failure_rate == pytest.approx(0.25)
    assert verdict.failed_count == 1
    assert verdict.total_count == 4


# ---------------------------------------------------------------------------
# 4. 50% failure — exactly equal to threshold does NOT abort (strict >)
# ---------------------------------------------------------------------------


def test_50_percent_failure_no_abort() -> None:
    results = [_ok(path=f"ok{i}.json") for i in range(2)] + [
        _fail(path=f"fail{i}.json") for i in range(2)
    ]
    verdict = evaluate_phase("1", results)
    # DEFAULT_THRESHOLD is 0.5; > is strict so exactly 0.5 does not abort
    assert DEFAULT_THRESHOLD == 0.5
    assert verdict.failure_rate == pytest.approx(0.5)
    assert verdict.should_abort is False


# ---------------------------------------------------------------------------
# 5. 75% failure — abort, reason mentions phase and rate
# ---------------------------------------------------------------------------


def test_75_percent_failure_aborts() -> None:
    results = [_ok(path="ok0.json")] + [_fail(path=f"fail{i}.json") for i in range(3)]
    verdict = evaluate_phase("2", results)
    assert verdict.should_abort is True
    assert "2" in verdict.reason
    assert "75%" in verdict.reason
    assert verdict.failure_rate == pytest.approx(0.75)
    assert verdict.failed_count == 3
    assert verdict.total_count == 4


# ---------------------------------------------------------------------------
# 6. 100% failure
# ---------------------------------------------------------------------------


def test_100_percent_failure_aborts() -> None:
    results = [_fail(path=f"fail{i}.json") for i in range(4)]
    verdict = evaluate_phase("1", results)
    assert verdict.should_abort is True
    assert verdict.failure_rate == pytest.approx(1.0)
    assert verdict.failed_count == 4


# ---------------------------------------------------------------------------
# 7. Synthesize exemption: phase_id="4" with 100% failure → no abort
# ---------------------------------------------------------------------------


def test_synthesize_exempt_no_abort() -> None:
    results = [_fail(path=f"fail{i}.json") for i in range(4)]
    verdict = evaluate_phase(SYNTHESIZE_PHASE_ID, results)
    assert verdict.should_abort is False
    assert "synthesize" in verdict.reason.lower()
    assert "exempt" in verdict.reason.lower()


# ---------------------------------------------------------------------------
# 8. Custom threshold
# ---------------------------------------------------------------------------


def test_custom_threshold_equal_does_not_abort() -> None:
    # 25% failure with threshold=0.25: exactly equal, strict > means no abort
    results = [_ok(path=f"ok{i}.json") for i in range(3)] + [_fail(path="fail0.json")]
    verdict = evaluate_phase("1", results, threshold=0.25)
    assert verdict.failure_rate == pytest.approx(0.25)
    assert verdict.should_abort is False


def test_custom_threshold_above_aborts() -> None:
    # 50% failure with threshold=0.25: 0.5 > 0.25 → abort
    results = [_ok(path=f"ok{i}.json") for i in range(2)] + [
        _fail(path=f"fail{i}.json") for i in range(2)
    ]
    verdict = evaluate_phase("1", results, threshold=0.25)
    assert verdict.failure_rate == pytest.approx(0.5)
    assert verdict.should_abort is True


# ---------------------------------------------------------------------------
# 9. Failure detected by exit_code != 0
# ---------------------------------------------------------------------------


def test_failure_by_exit_code() -> None:
    result = WorkerResult(
        exit_code=1,
        output_path=Path("out.json"),
        tokens_in=10,
        tokens_out=5,
        cost_usd=0.0,
        duration_s=0.01,
        stop_reason="end_turn",
        schema_valid=True,
        schema_errors=[],
    )
    verdict = evaluate_phase("1", [result])
    assert verdict.failed_count == 1


# ---------------------------------------------------------------------------
# 10. Failure detected by stop_reason="error"
# ---------------------------------------------------------------------------


def test_failure_by_stop_reason_error() -> None:
    result = WorkerResult(
        exit_code=0,
        output_path=Path("out.json"),
        tokens_in=10,
        tokens_out=5,
        cost_usd=0.0,
        duration_s=0.01,
        stop_reason="error",
        schema_valid=True,
        schema_errors=[],
    )
    verdict = evaluate_phase("1", [result])
    assert verdict.failed_count == 1


# ---------------------------------------------------------------------------
# 11. Failure detected by stop_reason="timeout"
# ---------------------------------------------------------------------------


def test_failure_by_stop_reason_timeout() -> None:
    result = WorkerResult(
        exit_code=0,
        output_path=Path("out.json"),
        tokens_in=10,
        tokens_out=5,
        cost_usd=0.0,
        duration_s=0.01,
        stop_reason="timeout",
        schema_valid=True,
        schema_errors=[],
    )
    verdict = evaluate_phase("1", [result])
    assert verdict.failed_count == 1


# ---------------------------------------------------------------------------
# 12. Failure detected by schema: schema_valid=False with errors
# ---------------------------------------------------------------------------


def test_failure_by_schema_errors() -> None:
    result = WorkerResult(
        exit_code=0,
        output_path=Path("out.json"),
        tokens_in=10,
        tokens_out=5,
        cost_usd=0.0,
        duration_s=0.01,
        stop_reason="end_turn",
        schema_valid=False,
        schema_errors=["field 'x' missing"],
    )
    verdict = evaluate_phase("1", [result])
    assert verdict.failed_count == 1


# ---------------------------------------------------------------------------
# 13. Success: exit_code=0, end_turn, schema_valid=True
# ---------------------------------------------------------------------------


def test_success_not_counted_as_failed() -> None:
    result = _ok()
    verdict = evaluate_phase("1", [result])
    assert verdict.failed_count == 0
    assert verdict.should_abort is False


# ---------------------------------------------------------------------------
# 14. Edge case: schema_valid=False but schema_errors=[] → not failed
#     (schema validation was skipped, e.g. output_schema=None)
# ---------------------------------------------------------------------------


def test_schema_invalid_but_no_errors_is_not_failed() -> None:
    result = WorkerResult(
        exit_code=0,
        output_path=Path("out.json"),
        tokens_in=10,
        tokens_out=5,
        cost_usd=0.0,
        duration_s=0.01,
        stop_reason="end_turn",
        schema_valid=False,
        schema_errors=[],
    )
    verdict = evaluate_phase("1", [result])
    assert verdict.failed_count == 0
