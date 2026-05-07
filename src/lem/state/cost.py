# pyright: strict
"""cost.jsonl + notional dollar tracking.

Rates are constants in code. Override via LEM_RATES_FILE env var pointing to a
JSON file with the schema: {"haiku": [input_rate, output_rate], ...}.
Rates are per-token in USD.
"""

import dataclasses
import json
import os
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from lem.types import CostEvent

RATES: dict[str, tuple[float, float]] = {
    "haiku":  (0.0000010, 0.0000050),
    "sonnet": (0.0000030, 0.0000150),
    "opus":   (0.0000150, 0.0000750),
}

_rates_loaded = False
_effective_rates: dict[str, tuple[float, float]] = {}


def _load_rates() -> dict[str, tuple[float, float]]:
    global _rates_loaded, _effective_rates
    if _rates_loaded:
        return _effective_rates
    rates = dict(RATES)
    override = os.environ.get("LEM_RATES_FILE")
    if override:
        p = Path(override)
        if p.exists():
            raw: dict[str, Any] = json.loads(p.read_text(encoding="utf-8"))
            for model, pair in raw.items():
                rates[model] = (float(pair[0]), float(pair[1]))
    _effective_rates = rates
    _rates_loaded = True
    return _effective_rates


def reset_rates_cache() -> None:
    """Reset the cached rates so _load_rates re-reads LEM_RATES_FILE on next call."""
    global _rates_loaded
    _rates_loaded = False


def compute_cost(*, model: str, tokens_in: int, tokens_out: int) -> float:
    """Compute notional USD cost for a single worker invocation. Unknown model → 0.0
    with a stderr warning."""
    rates = _load_rates()
    if model not in rates:
        print(
            f"compute_cost: unknown model '{model}', cost set to 0.0",
            file=sys.stderr,
        )
        return 0.0
    rate_in, rate_out = rates[model]
    return tokens_in * rate_in + tokens_out * rate_out


def _cost_path(workspace_path: Path) -> Path:
    return workspace_path / "meta" / "cost.jsonl"


def _to_dict(event: CostEvent) -> dict[str, Any]:
    return dataclasses.asdict(event)


def _from_dict(d: dict[str, Any]) -> CostEvent:
    return CostEvent(
        run_id=d["run_id"],
        phase=d["phase"],
        role=d["role"],
        model=d["model"],
        tokens_in=d["tokens_in"],
        tokens_out=d["tokens_out"],
        cost_usd=d["cost_usd"],
        duration_s=d["duration_s"],
        timestamp=d["timestamp"],
        attempt=d["attempt"],
    )


def append_cost(workspace_path: Path, event: CostEvent) -> None:
    """Append a CostEvent to <workspace_path>/meta/cost.jsonl as a single JSONL line.
    Uses O_APPEND for atomic per-line writes."""
    path = _cost_path(workspace_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(_to_dict(event)) + "\n"
    fd = os.open(str(path), os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
    try:
        os.write(fd, line.encode("utf-8"))
    finally:
        os.close(fd)


def read_cost(workspace_path: Path) -> Iterator[CostEvent]:
    """Iterate cost.jsonl line by line as CostEvents. Skip malformed lines to stderr."""
    path = _cost_path(workspace_path)
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, start=1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                d: dict[str, Any] = json.loads(raw)
                yield _from_dict(d)
            except Exception as exc:
                print(
                    f"cost.jsonl line {lineno} skipped (malformed): {exc}",
                    file=sys.stderr,
                )


def aggregate_phase(
    workspace_path: Path, phase: str, run_id: str
) -> list[CostEvent]:
    """Read meta/events/<phase>-*.json, build CostEvents, append to cost.jsonl."""
    events_dir = workspace_path / "meta" / "events"
    results: list[CostEvent] = []
    for event_file in sorted(events_dir.glob(f"{phase}-*.json")):
        stem = event_file.stem
        parts = stem.split("-")
        if len(parts) < 2:
            continue
        role = parts[1]
        try:
            payload: dict[str, Any] = json.loads(event_file.read_text(encoding="utf-8"))
        except Exception as exc:
            print(
                f"aggregate_phase: skipping {event_file.name}: {exc}",
                file=sys.stderr,
            )
            continue
        tokens_in = int(payload.get("tokens_in", 0))
        tokens_out = int(payload.get("tokens_out", 0))
        model = str(payload.get("model", "unknown"))
        duration_s = float(payload.get("duration_s", 0.0))
        attempt = int(payload.get("attempt", 1))
        timestamp = float(payload.get("timestamp", 0.0))
        cost_usd = compute_cost(model=model, tokens_in=tokens_in, tokens_out=tokens_out)
        event = CostEvent(
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
        append_cost(workspace_path, event)
        results.append(event)
    return results


def phase_total(workspace_path: Path, phase: str) -> float:
    """Sum cost_usd over all CostEvents in cost.jsonl matching the phase."""
    return sum(e.cost_usd for e in read_cost(workspace_path) if e.phase == phase)


def run_total(workspace_path: Path) -> float:
    """Sum cost_usd over all CostEvents in cost.jsonl."""
    return sum(e.cost_usd for e in read_cost(workspace_path))
