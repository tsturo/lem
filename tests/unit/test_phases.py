# pyright: strict
"""Tests for src/lem/phases.py."""

from pathlib import Path

import pytest

from lem.phases import PHASES, get_phase, next_phase, phase_index
from lem.types import Profile, Role, RunState, WorkerInvocation


_EXPECTED_IDS = ["0", "0.5", "1", "1.5", "1.6", "2", "2.5", "3", "4"]
_EXPECTED_NAMES = [
    "Intake", "JTBD", "Discover", "Disagreement", "Reframe",
    "Explore", "Distill", "Critique", "Synthesize",
]


def _make_state(workspace_path: Path) -> RunState:
    return RunState(
        run_id="test-run-phases",
        workspace_path=workspace_path,
        phase="0",
        status="running",
        started_at=1000.0,
        last_event_at=1001.0,
        cost_so_far=0.0,
        error=None,
    )


def _make_profile() -> Profile:
    role = Role(
        name="stub",
        description="stub",
        model="haiku",
        worker="cli",
        phase=None,
        output_cap=1024,
        timeout_s=30,
        branchable="no",
        output_schema={},
        tools=[],
        system_prompt="",
        source_path=Path("/stub"),
    )
    return Profile(
        name="stub",
        description="stub",
        specialists=[],
        verdict_options=[],
        default_deliverables=[],
        flag_gated_deliverables={},
        roles={"stub": role},
        process_roles={},
        intake_prompt="",
        source_dir=Path("/stub"),
    )


# ── structure tests ───────────────────────────────────────────────────────────


def test_phases_count() -> None:
    assert len(PHASES) == 9


def test_phases_ids_in_order() -> None:
    assert [p.id for p in PHASES] == _EXPECTED_IDS


def test_phases_names_in_order() -> None:
    assert [p.name for p in PHASES] == _EXPECTED_NAMES


def test_parallel_flags() -> None:
    parallel_by_id = {p.id: p.parallel for p in PHASES}
    assert parallel_by_id["1"] is True    # Discover
    assert parallel_by_id["2"] is True    # Explore
    for phase_id, flag in parallel_by_id.items():
        if phase_id not in ("1", "2"):
            assert flag is False, f"phase {phase_id} should not be parallel"


def test_non_explore_gate_fns_are_none() -> None:
    for phase in PHASES:
        if phase.id != "2":
            assert phase.gate_fn is None, f"phase {phase.id} should have gate_fn=None"


# ── workers_fn smoke tests ────────────────────────────────────────────────────


def test_intake_workers_fn_returns_empty_list(tmp_path: Path) -> None:
    state = _make_state(tmp_path)
    profile = _make_profile()
    result = get_phase("0").workers_fn(state, profile)
    assert result == []


def test_all_workers_fn_return_list(tmp_path: Path) -> None:
    state = _make_state(tmp_path)
    profile = _make_profile()
    for phase in PHASES:
        result: list[WorkerInvocation] = phase.workers_fn(state, profile)
        assert isinstance(result, list), f"phase {phase.id} workers_fn must return a list"


# ── worker_fn helpers ─────────────────────────────────────────────────────────


def _make_profile_with_specialists(
    source_dir: Path, specialists: list[str]
) -> Profile:
    role = Role(
        name="stub",
        description="stub",
        model="haiku",
        worker="cli",
        phase=None,
        output_cap=1024,
        timeout_s=30,
        branchable="no",
        output_schema={},
        tools=[],
        system_prompt="",
        source_path=source_dir,
    )
    return Profile(
        name="stub",
        description="stub",
        specialists=specialists,
        verdict_options=[],
        default_deliverables=[],
        flag_gated_deliverables={},
        roles={s: role for s in specialists},
        process_roles={},
        intake_prompt="",
        source_dir=source_dir,
    )


# ── Task 6.2: JTBD workers_fn ─────────────────────────────────────────────────


def test_jtbd_returns_one_invocation(tmp_path: Path) -> None:
    profile = _make_profile_with_specialists(tmp_path / "profiles" / "app-idea", [])
    state = _make_state(tmp_path / "workspace")
    result = get_phase("0.5").workers_fn(state, profile)
    assert len(result) == 1


def test_jtbd_role_path_is_jtbd_extractor(tmp_path: Path) -> None:
    profile = _make_profile_with_specialists(tmp_path / "profiles" / "app-idea", [])
    state = _make_state(tmp_path / "workspace")
    inv = get_phase("0.5").workers_fn(state, profile)[0]
    assert inv.role_path.name == "jtbd-extractor.md"
    assert inv.role_path.parent.name == "process_roles"


def test_jtbd_output_path(tmp_path: Path) -> None:
    profile = _make_profile_with_specialists(tmp_path / "profiles" / "app-idea", [])
    ws = tmp_path / "workspace"
    state = _make_state(ws)
    inv = get_phase("0.5").workers_fn(state, profile)[0]
    assert inv.output_path == ws / "frame-shifter" / "jtbd.md"


def test_jtbd_reads_idea_md(tmp_path: Path) -> None:
    profile = _make_profile_with_specialists(tmp_path / "profiles" / "app-idea", [])
    ws = tmp_path / "workspace"
    state = _make_state(ws)
    inv = get_phase("0.5").workers_fn(state, profile)[0]
    assert ws / "idea.md" in inv.allowed_read_paths


def test_jtbd_model_is_sonnet(tmp_path: Path) -> None:
    profile = _make_profile_with_specialists(tmp_path / "profiles" / "app-idea", [])
    state = _make_state(tmp_path / "workspace")
    inv = get_phase("0.5").workers_fn(state, profile)[0]
    assert inv.model == "sonnet"


# ── explore gate_fn tests ─────────────────────────────────────────────────────


def _explore_gate(tmp_path: Path) -> bool:
    phase = get_phase("2")
    assert phase.gate_fn is not None
    return phase.gate_fn(_make_state(tmp_path))


def test_explore_gate_false_when_file_missing(tmp_path: Path) -> None:
    assert _explore_gate(tmp_path) is False


def test_explore_gate_false_when_file_empty(tmp_path: Path) -> None:
    (tmp_path / "disagreements.md").write_text("", encoding="utf-8")
    assert _explore_gate(tmp_path) is False


def test_explore_gate_false_when_no_frontmatter(tmp_path: Path) -> None:
    (tmp_path / "disagreements.md").write_text("# Just a heading\n\nNo frontmatter.", encoding="utf-8")
    assert _explore_gate(tmp_path) is False


def test_explore_gate_false_when_axes_by_domain_missing(tmp_path: Path) -> None:
    content = "---\nother_key: value\n---\n\nbody"
    (tmp_path / "disagreements.md").write_text(content, encoding="utf-8")
    assert _explore_gate(tmp_path) is False


def test_explore_gate_false_when_axes_by_domain_empty_dict(tmp_path: Path) -> None:
    content = "---\naxes_by_domain: {}\n---\n\nbody"
    (tmp_path / "disagreements.md").write_text(content, encoding="utf-8")
    assert _explore_gate(tmp_path) is False


def test_explore_gate_false_when_all_values_empty(tmp_path: Path) -> None:
    content = "---\naxes_by_domain:\n  a: \"\"\n  b: \"\"\n---\n\nbody"
    (tmp_path / "disagreements.md").write_text(content, encoding="utf-8")
    assert _explore_gate(tmp_path) is False


def test_explore_gate_true_when_one_nonempty_value(tmp_path: Path) -> None:
    content = "---\naxes_by_domain:\n  domain_a: \"cost vs speed\"\n---\n\nbody"
    (tmp_path / "disagreements.md").write_text(content, encoding="utf-8")
    assert _explore_gate(tmp_path) is True


def test_explore_gate_true_when_mixed_values(tmp_path: Path) -> None:
    content = "---\naxes_by_domain:\n  a: \"\"\n  b: \"some axis\"\n---\n\nbody"
    (tmp_path / "disagreements.md").write_text(content, encoding="utf-8")
    assert _explore_gate(tmp_path) is True


def test_explore_gate_false_on_malformed_yaml(tmp_path: Path) -> None:
    content = "---\n: bad: yaml: [\n---\n\nbody"
    (tmp_path / "disagreements.md").write_text(content, encoding="utf-8")
    assert _explore_gate(tmp_path) is False


def test_explore_gate_false_on_axes_not_dict(tmp_path: Path) -> None:
    content = "---\naxes_by_domain: \"not a dict\"\n---\n\nbody"
    (tmp_path / "disagreements.md").write_text(content, encoding="utf-8")
    assert _explore_gate(tmp_path) is False


# ── helper function tests ─────────────────────────────────────────────────────


def test_get_phase_returns_correct_phase() -> None:
    phase = get_phase("1")
    assert phase.name == "Discover"
    assert phase.id == "1"


def test_get_phase_raises_key_error_for_unknown_id() -> None:
    with pytest.raises(KeyError):
        get_phase("99")


def test_phase_index_returns_correct_index() -> None:
    assert phase_index("0") == 0
    assert phase_index("0.5") == 1
    assert phase_index("4") == 8


def test_phase_index_raises_key_error_for_unknown_id() -> None:
    with pytest.raises(KeyError):
        phase_index("unknown")


def test_next_phase_returns_next() -> None:
    nxt = next_phase("0")
    assert nxt is not None
    assert nxt.id == "0.5"


def test_next_phase_returns_none_for_last() -> None:
    assert next_phase("4") is None


def test_next_phase_middle_of_pipeline() -> None:
    nxt = next_phase("1.5")
    assert nxt is not None
    assert nxt.id == "1.6"
