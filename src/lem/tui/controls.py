# pyright: strict
"""Key bindings, control.json writer."""

from pathlib import Path

from lem.control import write_control


def pause(workspace_path: Path) -> None:
    write_control(workspace_path, "pause")


def resume(workspace_path: Path) -> None:
    write_control(workspace_path, "resume")


def cancel(workspace_path: Path, *, confirmed: bool) -> None:
    if confirmed:
        write_control(workspace_path, "cancel")


def kill_worker(workspace_path: Path, worker_id: str) -> None:
    """Best-effort kill via structured cancel-with-target hint to orchestrator."""
    import json
    import os
    import tempfile

    meta = workspace_path / "meta"
    meta.mkdir(parents=True, exist_ok=True)
    target = meta / "control.json"
    data = json.dumps({"action": "cancel", "target": worker_id}).encode("utf-8")
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
