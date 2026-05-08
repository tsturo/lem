# pyright: strict
"""Install profile role symlinks into .claude/agents/ for Claude Code @agent access."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


def install_agents(
    profile_dir: Path,
    target_dir: Path = Path(".claude/agents"),
) -> list[Path]:
    """Create symlinks (or copies on Windows) for the active profile's roles +
    process_roles into .claude/agents/.

    profile_dir: e.g. profiles/app-idea
    target_dir: defaults to .claude/agents (relative to project root)

    Returns list of created/verified paths.
    """
    target_dir.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []

    sources = _collect_sources(profile_dir)
    for src in sources:
        dest = target_dir / src.name
        _install_one(src, dest)
        created.append(dest)

    return created


def _collect_sources(profile_dir: Path) -> list[Path]:
    sources: list[Path] = []
    roles_dir = profile_dir / "roles"
    if roles_dir.is_dir():
        sources.extend(sorted(roles_dir.glob("*.md")))
    process_roles_dir = profile_dir.parent.parent / "process_roles"
    if process_roles_dir.is_dir():
        sources.extend(sorted(process_roles_dir.glob("*.md")))
    return sources


def _install_one(src: Path, dest: Path) -> None:
    if dest.is_symlink():
        if dest.resolve() == src.resolve():
            return
        dest.unlink()
    elif dest.exists():
        raise FileExistsError(f"{dest} exists and is not a symlink")

    if sys.platform == "win32":
        shutil.copyfile(src, dest)
    else:
        os.symlink(src.resolve(), dest)
