# pyright: strict
"""state.json read/write, atomic."""

import dataclasses
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from lem.types import RunState


def _meta_dir(workspace_path: Path) -> Path:
    return workspace_path / "meta"


def _state_path(workspace_path: Path) -> Path:
    return _meta_dir(workspace_path) / "state.json"


def _to_dict(state: RunState) -> dict[str, Any]:
    d = dataclasses.asdict(state)
    d["workspace_path"] = str(state.workspace_path)
    return d


def _from_dict(d: dict[str, Any]) -> RunState:
    required = {
        "run_id", "workspace_path", "phase", "status",
        "started_at", "last_event_at", "cost_so_far", "error",
    }
    missing = required - d.keys()
    if missing:
        raise ValueError(f"state.json missing keys: {missing}")
    return RunState(
        run_id=d["run_id"],
        workspace_path=Path(d["workspace_path"]),
        phase=d["phase"],
        status=d["status"],
        started_at=d["started_at"],
        last_event_at=d["last_event_at"],
        cost_so_far=d["cost_so_far"],
        error=d["error"],
    )


def write_state(state: RunState) -> None:
    """Atomically write state to <workspace_path>/meta/state.json (tmp + os.replace).
    Creates meta/ if missing."""
    meta = _meta_dir(state.workspace_path)
    meta.mkdir(parents=True, exist_ok=True)
    target = _state_path(state.workspace_path)
    data = json.dumps(_to_dict(state), indent=2).encode("utf-8")
    fd, tmp_path = tempfile.mkstemp(dir=meta, prefix="state.json.", suffix=".tmp")
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


def read_state(workspace_path: Path) -> RunState:
    """Read meta/state.json and reconstitute a RunState. Raises FileNotFoundError
    if the file doesn't exist; raises ValueError on corrupt JSON or schema mismatch."""
    path = _state_path(workspace_path)
    if not path.exists():
        raise FileNotFoundError(f"state.json not found: {path}")
    try:
        raw = path.read_text(encoding="utf-8")
        d: dict[str, Any] = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"state.json is corrupt (invalid JSON): {exc}") from exc
    except Exception as exc:
        raise ValueError(f"state.json could not be read: {exc}") from exc
    return _from_dict(d)


def update_state(workspace_path: Path, **fields: object) -> RunState:
    """Read, mutate the named fields, write back atomically.
    Returns the updated state."""
    state = read_state(workspace_path)
    for key, value in fields.items():
        setattr(state, key, value)
    write_state(state)
    return state
