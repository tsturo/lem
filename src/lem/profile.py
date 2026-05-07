"""Profile loader (profile.yaml + roles)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import yaml

from lem.schema.parser import parse_file
from lem.types import Profile, Role


def _profiles_root() -> Path:
    return Path(__file__).parent.parent.parent / "profiles"


def _process_roles_root() -> Path:
    return Path(__file__).parent.parent.parent / "process_roles"


def _load_role(path: Path) -> Role:
    doc = parse_file(path)
    fm = doc.frontmatter
    return Role(
        name=str(fm["name"]),
        description=str(fm.get("description", "")),
        model=cast(Any, str(fm.get("model", "sonnet"))),
        worker=cast(Any, str(fm.get("worker", "cli"))),
        phase=str(fm["phase"]) if "phase" in fm else None,
        output_cap=int(cast(Any, fm.get("output_cap", 4096))),
        timeout_s=int(cast(Any, fm.get("timeout_s", 600))),
        branchable=cast(Any, str(fm.get("branchable", "no"))),
        output_schema=cast(Any, fm.get("output_schema", {})),
        tools=cast(Any, fm.get("tools", [])),
        system_prompt=doc.body,
        source_path=path,
    )


def load_profile(name: str = "app-idea") -> Profile:
    profile_dir = _profiles_root() / name
    raw = yaml.safe_load((profile_dir / "profile.yaml").read_text(encoding="utf-8"))
    intake_prompt = (profile_dir / "intake-prompt.md").read_text(encoding="utf-8")

    roles: dict[str, Role] = {}
    roles_dir = profile_dir / "roles"
    if roles_dir.is_dir():
        for role_file in sorted(roles_dir.glob("*.md")):
            role = _load_role(role_file)
            roles[role.name] = role

    process_roles: dict[str, Role] = {}
    proc_dir = _process_roles_root()
    if proc_dir.is_dir():
        for role_file in sorted(proc_dir.glob("*.md")):
            role = _load_role(role_file)
            process_roles[role.name] = role

    return Profile(
        name=str(raw["name"]),
        description=str(raw.get("description", "")),
        specialists=cast(Any, raw.get("specialists", [])),
        verdict_options=cast(Any, raw.get("verdict_options", [])),
        default_deliverables=cast(Any, raw.get("default_deliverables", [])),
        flag_gated_deliverables=cast(Any, raw.get("flag_gated_deliverables", {})),
        roles=roles,
        process_roles=process_roles,
        intake_prompt=intake_prompt,
        source_dir=profile_dir,
    )
