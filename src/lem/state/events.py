# pyright: strict
"""meta/events/*.json writer."""

import json
import os
import secrets
import tempfile
import time
from pathlib import Path


def _events_dir(workspace_path: Path) -> Path:
    return workspace_path / "meta" / "events"


def _make_path(events_dir: Path, phase: str, role: str, suffix: str = "") -> Path:
    ms = time.time_ns() // 1_000_000
    name = f"{phase}-{role}-{ms}{suffix}.json"
    return events_dir / name


def write_event(
    workspace_path: Path, *, phase: str, role: str, payload: dict[str, object]
) -> Path:
    """Write a per-worker event JSON file. Returns the path it was written to."""
    events_dir = _events_dir(workspace_path)
    events_dir.mkdir(parents=True, exist_ok=True)
    data = json.dumps(payload, indent=2).encode("utf-8")
    target = _make_path(events_dir, phase, role)
    for _ in range(4):
        if not target.exists():
            break
        target = _make_path(events_dir, phase, role, suffix=f"-{secrets.token_hex(3)}")
    else:
        if target.exists():
            raise RuntimeError(
                f"Could not find unique event filename after retries: {target}"
            )
    fd, tmp_path = tempfile.mkstemp(dir=events_dir, prefix=".evt.", suffix=".tmp")
    try:
        os.write(fd, data)
        os.close(fd)
        os.replace(tmp_path, target)
    except Exception:
        os.close(fd)
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
    return target
