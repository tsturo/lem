# pyright: strict
"""meta/control.json polling for TUI commands (pause/resume/cancel)."""

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass(frozen=True)
class ControlAction:
    action: Literal["pause", "resume", "cancel"]


def _control_path(workspace_path: Path) -> Path:
    return workspace_path / "meta" / "control.json"


def read_control(workspace_path: Path) -> ControlAction | None:
    """Read meta/control.json; None if absent or malformed."""
    path = _control_path(workspace_path)
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        action = raw.get("action")
        if action not in ("pause", "resume", "cancel"):
            return None
        return ControlAction(action=action)
    except Exception:
        return None


def write_control(workspace_path: Path, action: str) -> None:
    """Atomic write of meta/control.json (used by TUI / lem cancel)."""
    meta = workspace_path / "meta"
    meta.mkdir(parents=True, exist_ok=True)
    target = _control_path(workspace_path)
    data = json.dumps({"action": action}).encode("utf-8")
    fd, tmp_path = tempfile.mkstemp(dir=meta, prefix="control.json.", suffix=".tmp")
    try:
        try:
            os.write(fd, data)
        finally:
            os.close(fd)
        os.replace(tmp_path, target)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def clear_control(workspace_path: Path) -> None:
    """Remove meta/control.json after the action is consumed."""
    path = _control_path(workspace_path)
    try:
        path.unlink()
    except FileNotFoundError:
        pass
