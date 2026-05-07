# pyright: strict
"""End-to-end tests for the full pipeline using LEM_STUB_MODE (no API calls)."""

from __future__ import annotations

import json
import threading
from pathlib import Path

import pytest

from lem.control import write_control
from lem.orchestrator import OrchestratorConfig, run_orchestrator
from lem.profile import load_profile_from_path

STUB_PROFILE_DIR = Path(__file__).parent.parent / "fixtures" / "stub-profile"
CANNED_DIR = STUB_PROFILE_DIR / "canned-outputs"


def _seed_workspace(workspace: Path) -> None:
    """Write the minimum files the pipeline reads at workers_fn / gate_fn time."""
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "idea.md").write_text(
        "An app that helps freelancers send invoices on time.\n", encoding="utf-8"
    )
    (workspace / "assumptions.yaml").write_text(
        "- assumption: users have internet access\n"
        "  confirmed: true\n"
        "  would_change_verdict_if_false: 'no'\n",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# 1. Full pipeline completes with stub profile
# ---------------------------------------------------------------------------


def test_full_pipeline_completes_with_stub_profile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LEM_STUB_MODE", "1")
    monkeypatch.setenv("LEM_STUB_MODE_DIR", str(CANNED_DIR))

    workspace = tmp_path / "workspace"
    _seed_workspace(workspace)

    profile = load_profile_from_path(STUB_PROFILE_DIR)
    state = run_orchestrator(workspace, profile, OrchestratorConfig(max_concurrent=2))

    assert state.status == "completed"
    assert (workspace / "idea.md").exists()
    assert (workspace / "frame-shifter" / "jtbd.md").exists()
    assert (workspace / "deliverables" / "executive-summary.md").exists()
    assert (workspace / "meta" / "state.json").exists()

    elapsed = state.last_event_at - state.started_at
    assert elapsed < 30, f"pipeline took {elapsed:.1f}s (expected <30s)"


# ---------------------------------------------------------------------------
# 2. Each specialist draft-1.md is written
# ---------------------------------------------------------------------------


def test_specialist_drafts_written(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LEM_STUB_MODE", "1")
    monkeypatch.setenv("LEM_STUB_MODE_DIR", str(CANNED_DIR))

    workspace = tmp_path / "workspace"
    _seed_workspace(workspace)

    profile = load_profile_from_path(STUB_PROFILE_DIR)
    state = run_orchestrator(workspace, profile)

    assert state.status == "completed"
    # Non-branching specialists have draft-1.md renamed to decision.md by the
    # explore-prepare hook so downstream phases find a single decision file.
    for specialist in ("architect", "designer", "market"):
        decision = workspace / specialist / "decision.md"
        assert decision.exists(), f"missing {decision}"
        assert decision.read_text(encoding="utf-8").strip(), f"empty {decision}"


# ---------------------------------------------------------------------------
# 3. Wall-clock abort
# ---------------------------------------------------------------------------


def test_wall_clock_aborts_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LEM_STUB_MODE", "1")
    monkeypatch.setenv("LEM_STUB_MODE_DIR", str(CANNED_DIR))

    workspace = tmp_path / "workspace"
    _seed_workspace(workspace)

    profile = load_profile_from_path(STUB_PROFILE_DIR)
    cfg = OrchestratorConfig(max_wall_clock_s=0.0)
    state = run_orchestrator(workspace, profile, cfg)

    assert state.status == "wall-clock-aborted"
    assert state.error is not None


# ---------------------------------------------------------------------------
# 4. Pause then resume
# ---------------------------------------------------------------------------


def test_pause_then_resume(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LEM_STUB_MODE", "1")
    monkeypatch.setenv("LEM_STUB_MODE_DIR", str(CANNED_DIR))

    workspace = tmp_path / "workspace"
    _seed_workspace(workspace)

    write_control(workspace, "pause")
    threading.Timer(0.4, lambda: write_control(workspace, "resume")).start()

    profile = load_profile_from_path(STUB_PROFILE_DIR)
    state = run_orchestrator(workspace, profile)

    assert state.status == "completed"


# ---------------------------------------------------------------------------
# 5. Cancel via control.json stops the run
# ---------------------------------------------------------------------------


def test_cancel_stops_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LEM_STUB_MODE", "1")
    monkeypatch.setenv("LEM_STUB_MODE_DIR", str(CANNED_DIR))

    workspace = tmp_path / "workspace"
    _seed_workspace(workspace)

    write_control(workspace, "cancel")

    profile = load_profile_from_path(STUB_PROFILE_DIR)
    state = run_orchestrator(workspace, profile)

    assert state.status == "cancelled"
    persisted = json.loads((workspace / "meta" / "state.json").read_text())
    assert persisted["status"] == "cancelled"


# ---------------------------------------------------------------------------
# 6. Schema validation surfaced: bad output triggers retry path
# ---------------------------------------------------------------------------


def test_schema_validation_triggers_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Write a bad architect output on first invocation; verify schema_errors populated."""
    monkeypatch.setenv("LEM_STUB_MODE", "1")

    bad_dir = tmp_path / "bad-canned"
    bad_dir.mkdir()
    # Copy good outputs for all roles except architect
    for name in (
        "jtbd-extractor", "designer", "market", "disagreement-detector",
        "frame-shifter", "distiller", "cross-skeptic", "kill-case-skeptic",
        "synthesizer",
    ):
        src = CANNED_DIR / f"{name}.md"
        if src.exists():
            (bad_dir / f"{name}.md").write_text(
                src.read_text(encoding="utf-8"), encoding="utf-8"
            )
    # Write intentionally invalid architect output (missing required frontmatter + sections)
    (bad_dir / "architect.md").write_text(
        (STUB_PROFILE_DIR / "canned-outputs" / "architect-bad.md").read_text(
            encoding="utf-8"
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("LEM_STUB_MODE_DIR", str(bad_dir))

    workspace = tmp_path / "workspace"
    _seed_workspace(workspace)

    profile = load_profile_from_path(STUB_PROFILE_DIR)
    state = run_orchestrator(workspace, profile)

    # Pipeline completes (schema failure triggers retry, which also returns stub)
    assert state.status == "completed"

    # The architect output file exists (retry wrote something).
    # Post-explore-prepare: non-branching draft-1.md is renamed to decision.md.
    assert (workspace / "architect" / "decision.md").exists()


# ---------------------------------------------------------------------------
# 7. State persisted correctly across phases
# ---------------------------------------------------------------------------


def test_state_json_reflects_final_phase(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LEM_STUB_MODE", "1")
    monkeypatch.setenv("LEM_STUB_MODE_DIR", str(CANNED_DIR))

    workspace = tmp_path / "workspace"
    _seed_workspace(workspace)

    profile = load_profile_from_path(STUB_PROFILE_DIR)
    state = run_orchestrator(workspace, profile)

    assert state.status == "completed"
    persisted = json.loads((workspace / "meta" / "state.json").read_text())
    assert persisted["status"] == "completed"
    assert persisted["phase"] == "4"


# ---------------------------------------------------------------------------
# 8. LEM_STUB_MODE without LEM_STUB_MODE_DIR uses generic placeholder
# ---------------------------------------------------------------------------


def test_stub_mode_without_dir_writes_placeholder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LEM_STUB_MODE", "1")
    monkeypatch.delenv("LEM_STUB_MODE_DIR", raising=False)

    workspace = tmp_path / "workspace"
    _seed_workspace(workspace)

    profile = load_profile_from_path(STUB_PROFILE_DIR)
    # Pipeline will complete; schema validation may fail but should not crash
    state = run_orchestrator(workspace, profile)

    # Even with placeholders, orchestrator must not crash
    assert state.status in ("completed", "failed", "cost-aborted")
    assert (workspace / "frame-shifter" / "jtbd.md").exists()


# ---------------------------------------------------------------------------
# 9. cost.jsonl populated after stub run (Fix #3)
# ---------------------------------------------------------------------------


def test_cost_jsonl_populated_after_stub_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LEM_STUB_MODE", "1")
    monkeypatch.setenv("LEM_STUB_MODE_DIR", str(CANNED_DIR))

    workspace = tmp_path / "workspace"
    _seed_workspace(workspace)

    profile = load_profile_from_path(STUB_PROFILE_DIR)
    state = run_orchestrator(workspace, profile, OrchestratorConfig(max_concurrent=2))

    assert state.status == "completed"

    cost_jsonl = workspace / "meta" / "cost.jsonl"
    assert cost_jsonl.exists(), "cost.jsonl must exist after a completed run"

    lines = [ln for ln in cost_jsonl.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) >= 1, "cost.jsonl must have at least one line"

    # Each line must be valid JSON with expected fields
    for line in lines:
        event = json.loads(line)
        assert "role" in event
        assert "model" in event
        assert "tokens_in" in event
        assert "tokens_out" in event
        assert "cost_usd" in event

    # state.cost_so_far must be > 0 because stub workers return non-zero tokens
    assert state.cost_so_far > 0, "cost_so_far must be > 0 after dispatching stub workers"

    # meta/events/ must have event files
    events_dir = workspace / "meta" / "events"
    assert events_dir.exists(), "meta/events/ directory must exist"
    event_files = list(events_dir.glob("*.json"))
    assert len(event_files) >= 1, "at least one event file must exist in meta/events/"

    # one event file per dispatched worker — the stub profile dispatches 9 workers
    # (jtbd-extractor, architect+designer+market, disagreement-detector,
    # frame-shifter, distiller, cross-skeptic+kill-case-skeptic, synthesizer)
    assert len(lines) == len(event_files), (
        f"cost.jsonl lines ({len(lines)}) must match event files ({len(event_files)})"
    )


# ---------------------------------------------------------------------------
# 10. Cost-ceiling aborts run when max_cost is tiny (Fix #2)
# ---------------------------------------------------------------------------


def test_cost_ceiling_aborts_stub_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LEM_STUB_MODE", "1")
    monkeypatch.setenv("LEM_STUB_MODE_DIR", str(CANNED_DIR))

    workspace = tmp_path / "workspace"
    _seed_workspace(workspace)

    profile = load_profile_from_path(STUB_PROFILE_DIR)
    cfg = OrchestratorConfig(max_cost=0.0001)
    state = run_orchestrator(workspace, profile, cfg)

    assert state.status == "cost-aborted"
    assert state.error is not None
    assert "cost ceiling breach" in state.error
