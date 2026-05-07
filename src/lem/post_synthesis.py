# pyright: strict
"""Post-synthesis enforcement: auto-downgrade verdict to Insufficient information.

Spec: when >50% of load-bearing assumptions (would_change_verdict_if_false in
{"yes", "maybe"}) are unconfirmed, the orchestrator MUST rewrite the
recommendation to "Insufficient information" regardless of the synthesizer's
output. The synthesizer's verdict_constraint hint is advisory; this check is
the enforcement layer.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, cast

import yaml

from lem.schema.parser import parse_file
from lem.state.log import append_log
from lem.types import LogEvent, Profile, RunState

INSUFFICIENT_INFO = "Insufficient information"


def _load_assumptions(workspace_path: Path) -> list[dict[str, Any]]:
    path = workspace_path / "assumptions.yaml"
    if not path.exists():
        return []
    try:
        data: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    if not isinstance(data, list):
        return []
    items: list[Any] = cast("list[Any]", data)
    return [a for a in items if isinstance(a, dict)]


_LOAD_BEARING_MARKERS: tuple[object, ...] = ("yes", "maybe", True)


def _load_bearing_unconfirmed_ratio(
    assumptions: list[dict[str, Any]],
) -> tuple[int, int]:
    """Return (load_bearing_count, unconfirmed_count).

    YAML parses unquoted `yes` as Python True; we accept both forms so authors
    don't need to remember to quote.
    """
    load_bearing = [
        a for a in assumptions
        if a.get("would_change_verdict_if_false") in _LOAD_BEARING_MARKERS
    ]
    unconfirmed = [a for a in load_bearing if not a.get("confirmed")]
    return len(load_bearing), len(unconfirmed)


def _atomic_write(path: Path, text: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def _serialize_frontmatter(fm: dict[str, object]) -> str:
    return yaml.safe_dump(fm, sort_keys=False, allow_unicode=True).rstrip()


def _rewrite_with_downgrade(
    target_path: Path,
    *,
    original_recommendation: str,
    original_confidence: str,
) -> None:
    """Rewrite the deliverable to flag Insufficient information + append note."""
    doc = parse_file(target_path)
    new_fm: dict[str, object] = dict(doc.frontmatter)
    new_fm["recommendation"] = INSUFFICIENT_INFO

    note = (
        "\n\n**Note**: this recommendation was auto-downgraded by the "
        "orchestrator because >50% of load-bearing assumptions are "
        f"unconfirmed. The synthesizer's stated recommendation was "
        f"'{original_recommendation}' with confidence '{original_confidence}'."
    )

    body = _replace_or_append_in_verdict(doc.body, note)
    text = "---\n" + _serialize_frontmatter(new_fm) + "\n---\n\n" + body.lstrip("\n")
    _atomic_write(target_path, text)


def _replace_or_append_in_verdict(body: str, note: str) -> str:
    """Append note to the end of the ## Verdict section if present, else to body end.

    Idempotent guard: if the note text already exists in the body, return body
    unchanged.
    """
    if "auto-downgraded by the orchestrator" in body:
        return body

    lines = body.splitlines(keepends=True)
    verdict_start: int | None = None
    next_section: int | None = None
    for i, ln in enumerate(lines):
        stripped = ln.rstrip("\n\r")
        if stripped.startswith("## Verdict"):
            verdict_start = i
            continue
        if verdict_start is not None and stripped.startswith("## "):
            next_section = i
            break

    if verdict_start is None:
        return body.rstrip("\n") + note + "\n"

    insert_at = next_section if next_section is not None else len(lines)
    inserted = list(lines[:insert_at]) + [note + "\n"] + list(lines[insert_at:])
    return "".join(inserted)


def post_synthesize_verdict_check(
    state: RunState,
    profile: Profile,
    *,
    target_path: Path | None = None,
) -> bool:
    """Enforce verdict auto-downgrade.

    Returns True if a downgrade was applied. Idempotent: re-running on an
    already-downgraded deliverable is a no-op.
    """
    _ = profile  # accepted for signature symmetry; not used today
    assumptions = _load_assumptions(state.workspace_path)
    load_bearing, unconfirmed = _load_bearing_unconfirmed_ratio(assumptions)
    if load_bearing == 0:
        return False
    if unconfirmed / load_bearing <= 0.5:
        return False

    deliverable = (
        target_path
        if target_path is not None
        else state.workspace_path / "deliverables" / "executive-summary.md"
    )
    if not deliverable.exists():
        return False

    doc = parse_file(deliverable)
    current = doc.frontmatter.get("recommendation")
    confidence = doc.frontmatter.get("confidence", "")
    current_str = str(current) if current is not None else ""
    confidence_str = str(confidence) if confidence is not None else ""
    if current_str == INSUFFICIENT_INFO:
        return False

    _rewrite_with_downgrade(
        deliverable,
        original_recommendation=current_str,
        original_confidence=confidence_str,
    )

    append_log(
        state.workspace_path,
        LogEvent(
            timestamp=time.time(),
            level="warning",
            event="verdict_auto_downgrade",
            phase="4",
            role="orchestrator",
            message=(
                f"auto-downgraded recommendation from '{current_str}' "
                f"to '{INSUFFICIENT_INFO}'"
            ),
            extra={
                "load_bearing": load_bearing,
                "unconfirmed": unconfirmed,
                "original_recommendation": current_str,
                "original_confidence": confidence_str,
            },
        ),
    )
    return True
