# pyright: strict
"""Median x 3 stalled-worker detection."""

import dataclasses
import statistics
from collections import defaultdict
from pathlib import Path

from lem.state.timeline import read_timeline

DEFAULT_BASELINE_S: float = 60.0
DEFAULT_MULTIPLIER: float = 3.0


@dataclasses.dataclass(frozen=True, kw_only=True)
class StalledCheck:
    stalled: bool
    median_s: float
    threshold_s: float


def compute_role_medians(
    runs_dir: Path,
    *,
    baseline_s: float = DEFAULT_BASELINE_S,
) -> dict[str, float]:
    """Read every <runs_dir>/<run-id>/meta/timeline.jsonl, compute per-role
    median duration_s. Roles with no history get baseline_s."""
    if not runs_dir.exists():
        return {}

    durations: dict[str, list[float]] = defaultdict(list)
    for timeline_file in runs_dir.glob("*/meta/timeline.jsonl"):
        workspace_path = timeline_file.parent.parent
        try:
            for event in read_timeline(workspace_path):
                durations[event.role].append(event.duration_s)
        except Exception:
            continue

    return {
        role: statistics.median(samples) if samples else baseline_s
        for role, samples in durations.items()
    }


def is_stalled(
    *,
    role: str,
    elapsed_s: float,
    medians: dict[str, float],
    baseline_s: float = DEFAULT_BASELINE_S,
    multiplier: float = DEFAULT_MULTIPLIER,
) -> StalledCheck:
    """Return whether the worker is stalled. threshold_s = median × multiplier.
    Stalled when elapsed_s > threshold_s (strict greater-than)."""
    median_s = medians.get(role, baseline_s)
    threshold_s = median_s * multiplier
    return StalledCheck(
        stalled=elapsed_s > threshold_s,
        median_s=median_s,
        threshold_s=threshold_s,
    )
