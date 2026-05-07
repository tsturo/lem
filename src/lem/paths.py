"""XDG resolution, workspace location, run-id generation."""

from __future__ import annotations

import os
import re
import secrets
from datetime import datetime
from pathlib import Path


def _xdg_data_home() -> Path:
    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        return Path(xdg)
    return Path.home() / ".local" / "share"


def _lem_runs_dir() -> Path:
    return _xdg_data_home() / "lem" / "runs"


def _slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"\s+", "-", text.strip())
    return re.sub(r"-{2,}", "-", text)


def _slug_from_idea(idea: str) -> str:
    words = idea.split()[:3]
    return _slugify(" ".join(words)) or "run"


def make_run_id(*, name: str | None, idea: str, when: datetime | None = None) -> str:
    ts = (when or datetime.now()).strftime("%Y-%m-%d-%H%M")
    slug = _slugify(name) if name else _slug_from_idea(idea)
    hex6 = secrets.token_hex(3)
    return f"{ts}-{slug}-{hex6}"


def _find_dot_lem_upward() -> Path | None:
    cwd = Path.cwd()
    for parent in [cwd, *cwd.parents]:
        candidate = parent / ".lem"
        if candidate.is_dir():
            return candidate
    return None


def resolve_workspace(
    *,
    name: str | None = None,
    workspace_arg: Path | None = None,
    run_id: str | None = None,
) -> Path:
    """Resolution order:
    1. --workspace flag → that path
    2. ./.lem if it exists in cwd OR an ancestor (git-style upward walk)
    3. $XDG_DATA_HOME/lem/runs/<run-id>
    """
    if workspace_arg is not None:
        return workspace_arg

    dot_lem = _find_dot_lem_upward()
    if dot_lem is not None:
        return dot_lem

    effective_run_id = run_id or (name or "run")
    return _lem_runs_dir() / effective_run_id
