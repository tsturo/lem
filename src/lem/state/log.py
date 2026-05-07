# pyright: strict
"""log.jsonl structured logging."""

import dataclasses
import json
import os
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from lem.types import LogEvent


def _log_path(workspace_path: Path) -> Path:
    return workspace_path / "meta" / "log.jsonl"


def _to_dict(event: LogEvent) -> dict[str, Any]:
    return dataclasses.asdict(event)


def _from_dict(d: dict[str, Any]) -> LogEvent:
    return LogEvent(
        timestamp=d["timestamp"],
        level=d["level"],
        event=d["event"],
        phase=d.get("phase"),
        role=d.get("role"),
        message=d.get("message", ""),
        extra=d.get("extra", {}),
    )


def append_log(workspace_path: Path, event: LogEvent) -> None:
    """Append a LogEvent to <workspace_path>/meta/log.jsonl as a single JSONL line.
    Uses O_APPEND for atomic per-line writes on POSIX."""
    path = _log_path(workspace_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(_to_dict(event)) + "\n"
    fd = os.open(str(path), os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
    try:
        os.write(fd, line.encode("utf-8"))
    finally:
        os.close(fd)


def read_log(workspace_path: Path) -> Iterator[LogEvent]:
    """Iterate the log line by line. Skip malformed lines but log them to stderr."""
    path = _log_path(workspace_path)
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
                    f"log.jsonl line {lineno} skipped (malformed): {exc}",
                    file=sys.stderr,
                )
