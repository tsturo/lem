# pyright: strict
"""Phase-level circuit breaker."""

from __future__ import annotations

from dataclasses import dataclass

from lem.types import WorkerResult

DEFAULT_THRESHOLD = 0.5
SYNTHESIZE_PHASE_ID = "4"


@dataclass(frozen=True)
class BreakerVerdict:
    should_abort: bool
    reason: str
    failure_rate: float
    failed_count: int
    total_count: int


def _is_failed(result: WorkerResult) -> bool:
    if result.exit_code != 0:
        return True
    if result.stop_reason in ("error", "timeout"):
        return True
    if not result.schema_valid and result.schema_errors:
        return True
    return False


def evaluate_phase(
    phase_id: str,
    results: list[WorkerResult],
    *,
    threshold: float = DEFAULT_THRESHOLD,
) -> BreakerVerdict:
    """Evaluate phase health from worker results.

    Returns should_abort=False when results is empty or phase is the synthesize
    phase (single-worker, breaker exempt).

    Otherwise computes failure rate and returns should_abort=(rate > threshold).
    """
    if phase_id == SYNTHESIZE_PHASE_ID:
        return BreakerVerdict(
            should_abort=False,
            reason=(
                "synthesize phase exempt from breaker"
                " (single worker, retry handles it)"
            ),
            failure_rate=0.0,
            failed_count=0,
            total_count=len(results),
        )

    total = len(results)
    if total == 0:
        return BreakerVerdict(
            should_abort=False,
            reason="no results to evaluate",
            failure_rate=0.0,
            failed_count=0,
            total_count=0,
        )

    failed = sum(1 for r in results if _is_failed(r))
    rate = failed / total
    should_abort = rate > threshold

    if should_abort:
        reason = (
            f"phase {phase_id} failure rate {rate:.0%}"
            f" ({failed}/{total}) exceeds threshold {threshold:.0%}"
        )
    else:
        reason = f"phase {phase_id} failure rate {rate:.0%} within threshold"

    return BreakerVerdict(
        should_abort=should_abort,
        reason=reason,
        failure_rate=rate,
        failed_count=failed,
        total_count=total,
    )
