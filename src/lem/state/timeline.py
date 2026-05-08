# pyright: strict
"""timeline.jsonl — per-worker start/end/duration tracking."""

import dataclasses
import json
import os
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any


@dataclasses.dataclass(frozen=True, kw_only=True)
class TimelineEvent:
    run_id: str
    phase: str
    role: str
    started_at: float
    ended_at: float
    duration_s: float
    attempt: int


def _timeline_path(workspace_path: Path) -> Path:
    return workspace_path / "meta" / "timeline.jsonl"


def _to_dict(event: TimelineEvent) -> dict[str, Any]:
    return dataclasses.asdict(event)


def _from_dict(d: dict[str, Any]) -> TimelineEvent:
    return TimelineEvent(
        run_id=d["run_id"],
        phase=d["phase"],
        role=d["role"],
        started_at=d["started_at"],
        ended_at=d["ended_at"],
        duration_s=d["duration_s"],
        attempt=d["attempt"],
    )


def append_timeline(workspace_path: Path, event: TimelineEvent) -> None:
    """Append a TimelineEvent to meta/timeline.jsonl."""
    path = _timeline_path(workspace_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(_to_dict(event)) + "\n"
    fd = os.open(str(path), os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
    try:
        os.write(fd, line.encode("utf-8"))
    finally:
        os.close(fd)


def read_timeline(workspace_path: Path) -> Iterator[TimelineEvent]:
    """Iterate timeline.jsonl as TimelineEvents. Skip malformed lines to stderr."""
    path = _timeline_path(workspace_path)
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
                    f"timeline.jsonl line {lineno} skipped (malformed): {exc}",
                    file=sys.stderr,
                )
