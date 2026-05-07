# pyright: strict
"""--max-cost + --max-wall-clock pre-checks."""

import time
from dataclasses import dataclass

from lem.state.cost import compute_cost
from lem.types import RunState

DEFAULT_MAX_COST_USD: float = 25.0
DEFAULT_MAX_WALL_CLOCK_S: float = 4 * 60 * 60


@dataclass(frozen=True)
class CostProjection:
    current_spend: float
    projected_worker_cost: float
    projected_total: float
    max_cost: float
    breach: bool


def project_worker_cost(*, model: str, input_estimate: int, output_cap: int) -> float:
    """Projected cost for an upcoming worker dispatch using cost.compute_cost."""
    return compute_cost(model=model, tokens_in=input_estimate, tokens_out=output_cap)


def check_cost_ceiling(
    state: RunState,
    projected_worker_cost: float,
    *,
    max_cost: float = DEFAULT_MAX_COST_USD,
) -> CostProjection:
    """Return a CostProjection. The orchestrator inspects .breach and decides
    whether to abort. This function is pure — does not mutate state."""
    projected_total = state.cost_so_far + projected_worker_cost
    return CostProjection(
        current_spend=state.cost_so_far,
        projected_worker_cost=projected_worker_cost,
        projected_total=projected_total,
        max_cost=max_cost,
        breach=projected_total >= max_cost,
    )


def check_wall_clock(
    state: RunState,
    *,
    max_wall_clock_s: float = DEFAULT_MAX_WALL_CLOCK_S,
    now: float | None = None,
) -> bool:
    """Return True if elapsed time since state.started_at exceeds max_wall_clock_s.
    `now` is injectable for tests; defaults to time.time()."""
    effective_now = now if now is not None else time.time()
    return (effective_now - state.started_at) >= max_wall_clock_s
