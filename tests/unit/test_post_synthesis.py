# pyright: strict
"""Tests for src/lem/post_synthesis.py."""

from __future__ import annotations

import json
from pathlib import Path

from lem.post_synthesis import post_synthesize_verdict_check
from lem.types import Profile, Role, RunState


def _make_state(workspace_path: Path) -> RunState:
    return RunState(
        run_id="run-test",
        workspace_path=workspace_path,
        phase="4",
        status="running",
        started_at=1000.0,
        last_event_at=1000.0,
        cost_so_far=0.0,
        error=None,
    )


def _make_profile() -> Profile:
    role = Role(
        name="stub", description="", model="haiku", worker="cli",
        phase=None, output_cap=1024, timeout_s=30, branchable="no",
        output_schema={}, tools=[], system_prompt="", source_path=Path("/stub"),
    )
    return Profile(
        name="stub", description="", specialists=[], verdict_options=[],
        default_deliverables=[], flag_gated_deliverables={}, roles={"stub": role},
        process_roles={}, intake_prompt="", source_dir=Path("/stub"),
    )


def _write_assumptions(ws: Path, *, load_bearing: int, unconfirmed: int) -> None:
    rows: list[str] = []
    for i in range(unconfirmed):
        rows.append(
            f"- description: a{i}\n"
            f"  would_change_verdict_if_false: yes\n"
            f"  confirmed: false\n"
        )
    for i in range(load_bearing - unconfirmed):
        rows.append(
            f"- description: c{i}\n"
            f"  would_change_verdict_if_false: yes\n"
            f"  confirmed: true\n"
        )
    (ws / "assumptions.yaml").write_text("".join(rows), encoding="utf-8")


def _write_summary(
    ws: Path,
    *,
    recommendation: str,
    confidence: str = "medium",
) -> Path:
    out = ws / "meta" / "synthesis.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        f"---\n"
        f"recommendation: {recommendation}\n"
        f"confidence: {confidence}\n"
        f"---\n\n"
        f"## Verdict\n\n"
        f"**{recommendation}.**\n\n"
        f"Body paragraph here.\n",
        encoding="utf-8",
    )
    return out


def test_no_load_bearing_no_change(tmp_path: Path) -> None:
    ws = tmp_path
    _write_assumptions(ws, load_bearing=0, unconfirmed=0)
    out = _write_summary(ws, recommendation="Build")
    before = out.read_text(encoding="utf-8")
    applied = post_synthesize_verdict_check(_make_state(ws), _make_profile())
    assert applied is False
    assert out.read_text(encoding="utf-8") == before


def test_low_unconfirmed_no_override(tmp_path: Path) -> None:
    ws = tmp_path
    _write_assumptions(ws, load_bearing=4, unconfirmed=2)
    out = _write_summary(ws, recommendation="Build")
    applied = post_synthesize_verdict_check(_make_state(ws), _make_profile())
    assert applied is False
    assert "recommendation: Build" in out.read_text(encoding="utf-8")


def test_high_unconfirmed_already_insufficient_idempotent(tmp_path: Path) -> None:
    ws = tmp_path
    _write_assumptions(ws, load_bearing=4, unconfirmed=3)
    out = _write_summary(ws, recommendation="Insufficient information")
    before = out.read_text(encoding="utf-8")
    applied = post_synthesize_verdict_check(_make_state(ws), _make_profile())
    assert applied is False
    assert out.read_text(encoding="utf-8") == before


def test_high_unconfirmed_with_build_triggers_rewrite(tmp_path: Path) -> None:
    ws = tmp_path
    _write_assumptions(ws, load_bearing=4, unconfirmed=3)
    out = _write_summary(ws, recommendation="Build", confidence="high")
    applied = post_synthesize_verdict_check(_make_state(ws), _make_profile())
    assert applied is True
    text = out.read_text(encoding="utf-8")
    assert "recommendation: Insufficient information" in text
    assert "auto-downgraded by the orchestrator" in text
    # Original recommendation preserved in the note.
    assert "'Build'" in text
    assert "'high'" in text


def test_maybe_load_bearing_counted(tmp_path: Path) -> None:
    """maybe-load-bearing counts as load-bearing per synthesizer rule."""
    ws = tmp_path
    (ws / "assumptions.yaml").write_text(
        "- description: a\n  would_change_verdict_if_false: maybe\n  confirmed: false\n"
        "- description: b\n  would_change_verdict_if_false: maybe\n  confirmed: false\n"
        "- description: c\n  would_change_verdict_if_false: yes\n  confirmed: true\n",
        encoding="utf-8",
    )
    _write_summary(ws, recommendation="Build")
    applied = post_synthesize_verdict_check(_make_state(ws), _make_profile())
    assert applied is True


def test_log_event_written_on_override(tmp_path: Path) -> None:
    ws = tmp_path
    _write_assumptions(ws, load_bearing=4, unconfirmed=3)
    _write_summary(ws, recommendation="Build", confidence="high")
    post_synthesize_verdict_check(_make_state(ws), _make_profile())
    log_path = ws / "meta" / "log.jsonl"
    assert log_path.exists()
    lines = [
        json.loads(ln) for ln in log_path.read_text(encoding="utf-8").splitlines()
        if ln.strip()
    ]
    overrides = [ln for ln in lines if ln["event"] == "verdict_auto_downgrade"]
    assert len(overrides) == 1
    assert overrides[0]["extra"]["load_bearing"] == 4
    assert overrides[0]["extra"]["unconfirmed"] == 3
    assert overrides[0]["extra"]["original_recommendation"] == "Build"


def test_missing_deliverable_no_op(tmp_path: Path) -> None:
    ws = tmp_path
    _write_assumptions(ws, load_bearing=4, unconfirmed=3)
    applied = post_synthesize_verdict_check(_make_state(ws), _make_profile())
    assert applied is False


def test_target_path_override(tmp_path: Path) -> None:
    """target_path lets callers route to a non-default deliverable file."""
    ws = tmp_path
    _write_assumptions(ws, load_bearing=4, unconfirmed=3)
    custom = ws / "custom-summary.md"
    custom.write_text(
        "---\nrecommendation: Build\nconfidence: medium\n---\n\n## Verdict\n\nBody.\n",
        encoding="utf-8",
    )
    applied = post_synthesize_verdict_check(
        _make_state(ws), _make_profile(), target_path=custom
    )
    assert applied is True
    assert "Insufficient information" in custom.read_text(encoding="utf-8")


def test_exact_50pct_no_override(tmp_path: Path) -> None:
    """ratio == 0.5 must not trigger; threshold is strictly > 0.5."""
    ws = tmp_path
    _write_assumptions(ws, load_bearing=4, unconfirmed=2)
    _write_summary(ws, recommendation="Build")
    applied = post_synthesize_verdict_check(_make_state(ws), _make_profile())
    assert applied is False
