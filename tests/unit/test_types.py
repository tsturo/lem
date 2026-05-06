"""Tests for src/lem/types.py dataclasses."""

import dataclasses
from pathlib import Path

import pytest

from lem.types import (
    CostEvent,
    LogEvent,
    PhaseSpec,
    Profile,
    Role,
    RunState,
    WorkerInvocation,
    WorkerResult,
)


# ---------------------------------------------------------------------------
# WorkerInvocation
# ---------------------------------------------------------------------------


def make_worker_invocation() -> WorkerInvocation:
    return WorkerInvocation(
        role_path=Path("/roles/architect.md"),
        workspace_path=Path("/runs/2024-01-01-1200-myrun-abc123/"),
        output_path=Path("/runs/2024-01-01-1200-myrun-abc123/architect.json"),
        allowed_read_paths=[Path("/src"), Path("/docs")],
        model="sonnet",
        max_output_tokens=4096,
        timeout_s=120,
        extra_context={"branch": "feature-x"},
    )


def test_worker_invocation_construction() -> None:
    inv = make_worker_invocation()
    assert inv.role_path == Path("/roles/architect.md")
    assert inv.model == "sonnet"
    assert inv.max_output_tokens == 4096
    assert inv.extra_context == {"branch": "feature-x"}


def test_worker_invocation_frozen() -> None:
    inv = make_worker_invocation()
    with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
        inv.model = "haiku"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# WorkerResult
# ---------------------------------------------------------------------------


def make_worker_result() -> WorkerResult:
    return WorkerResult(
        exit_code=0,
        output_path=Path("/runs/2024-01-01-1200-myrun-abc123/architect.json"),
        tokens_in=1000,
        tokens_out=500,
        cost_usd=0.003,
        duration_s=12.5,
        stop_reason="end_turn",
        schema_valid=True,
        schema_errors=[],
    )


def test_worker_result_construction() -> None:
    result = make_worker_result()
    assert result.exit_code == 0
    assert result.stop_reason == "end_turn"
    assert result.schema_valid is True
    assert result.schema_errors == []


def test_worker_result_frozen() -> None:
    result = make_worker_result()
    with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
        result.exit_code = 1  # type: ignore[misc]


# ---------------------------------------------------------------------------
# RunState
# ---------------------------------------------------------------------------


def make_run_state() -> RunState:
    return RunState(
        run_id="2024-01-01-1200-myrun-abc123",
        workspace_path=Path("/runs/2024-01-01-1200-myrun-abc123/"),
        phase="discover",
        status="running",
        started_at=1704067200.0,
        last_event_at=1704067260.0,
        cost_so_far=0.0,
        error=None,
    )


def test_run_state_construction() -> None:
    state = make_run_state()
    assert state.run_id == "2024-01-01-1200-myrun-abc123"
    assert state.phase == "discover"
    assert state.status == "running"
    assert state.error is None


def test_run_state_mutable() -> None:
    state = make_run_state()
    state.phase = "synthesize"
    assert state.phase == "synthesize"

    state.status = "completed"
    assert state.status == "completed"

    state.error = "something went wrong"
    assert state.error == "something went wrong"


# ---------------------------------------------------------------------------
# PhaseSpec
# ---------------------------------------------------------------------------


def make_phase_spec() -> PhaseSpec:
    def workers_fn(state: RunState, profile: Profile) -> list[WorkerInvocation]:
        return []

    return PhaseSpec(
        id="discover",
        name="Discover",
        workers_fn=workers_fn,
        parallel=True,
        gate_fn=None,
    )


def test_phase_spec_construction() -> None:
    spec = make_phase_spec()
    assert spec.id == "discover"
    assert spec.name == "Discover"
    assert spec.parallel is True
    assert spec.gate_fn is None


def test_phase_spec_gate_fn_default() -> None:
    def workers_fn(state: RunState, profile: Profile) -> list[WorkerInvocation]:
        return []

    spec = PhaseSpec(
        id="discover",
        name="Discover",
        workers_fn=workers_fn,
        parallel=False,
    )
    assert spec.gate_fn is None


def test_phase_spec_with_gate_fn() -> None:
    def workers_fn(state: RunState, profile: Profile) -> list[WorkerInvocation]:
        return []

    def gate_fn(state: RunState) -> bool:
        return state.status == "running"

    spec = PhaseSpec(
        id="synthesize",
        name="Synthesize",
        workers_fn=workers_fn,
        parallel=False,
        gate_fn=gate_fn,
    )
    assert spec.gate_fn is not None


def test_phase_spec_frozen() -> None:
    spec = make_phase_spec()
    with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
        spec.id = "other"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Role
# ---------------------------------------------------------------------------


def make_role() -> Role:
    return Role(
        name="architect",
        description="Reviews architecture",
        model="sonnet",
        worker="cli",
        phase="discover",
        output_cap=4096,
        timeout_s=120,
        branchable="no",
        output_schema={"type": "object"},
        tools=["WebFetch"],
        system_prompt="You are an architect.",
        source_path=Path("/profiles/app-idea/roles/architect.md"),
    )


def test_role_construction() -> None:
    role = make_role()
    assert role.name == "architect"
    assert role.model == "sonnet"
    assert role.worker == "cli"
    assert role.branchable == "no"
    assert role.tools == ["WebFetch"]


def test_role_phase_optional() -> None:
    role = Role(
        name="synthesizer",
        description="Synthesizes findings",
        model="haiku",
        worker="cli",
        phase=None,
        output_cap=2048,
        timeout_s=60,
        branchable="yes",
        output_schema={},
        tools=[],
        system_prompt="You synthesize.",
        source_path=Path("/profiles/app-idea/roles/synthesizer.md"),
    )
    assert role.phase is None


def test_role_frozen() -> None:
    role = make_role()
    with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
        role.name = "changed"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------


def make_profile() -> Profile:
    role = make_role()
    return Profile(
        name="app-idea",
        description="Evaluate an app idea",
        specialists=["architect"],
        verdict_options=["invest", "pass", "defer"],
        default_deliverables=["report"],
        flag_gated_deliverables={"--with-pitch": "investor-onepager"},
        roles={"architect": role},
        process_roles={},
        intake_prompt="Describe your app idea.",
        source_dir=Path("/profiles/app-idea/"),
    )


def test_profile_construction() -> None:
    profile = make_profile()
    assert profile.name == "app-idea"
    assert "architect" in profile.roles
    assert profile.verdict_options == ["invest", "pass", "defer"]
    assert profile.process_roles == {}


def test_profile_frozen() -> None:
    profile = make_profile()
    with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
        profile.name = "changed"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# CostEvent
# ---------------------------------------------------------------------------


def make_cost_event() -> CostEvent:
    return CostEvent(
        run_id="2024-01-01-1200-myrun-abc123",
        phase="discover",
        role="architect",
        model="sonnet",
        tokens_in=1000,
        tokens_out=500,
        cost_usd=0.003,
        duration_s=12.5,
        timestamp=1704067260.0,
        attempt=1,
    )


def test_cost_event_construction() -> None:
    event = make_cost_event()
    assert event.run_id == "2024-01-01-1200-myrun-abc123"
    assert event.phase == "discover"
    assert event.attempt == 1
    assert event.cost_usd == 0.003


def test_cost_event_frozen() -> None:
    event = make_cost_event()
    with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
        event.attempt = 2  # type: ignore[misc]


# ---------------------------------------------------------------------------
# LogEvent
# ---------------------------------------------------------------------------


def test_log_event_construction_full() -> None:
    event = LogEvent(
        timestamp=1704067260.0,
        level="info",
        event="worker_dispatched",
        phase="discover",
        role="architect",
        message="Dispatching architect worker",
        extra={"pid": 12345},
    )
    assert event.level == "info"
    assert event.event == "worker_dispatched"
    assert event.extra == {"pid": 12345}


def test_log_event_defaults() -> None:
    event = LogEvent(
        timestamp=1704067260.0,
        level="debug",
        event="phase_started",
    )
    assert event.phase is None
    assert event.role is None
    assert event.message == ""
    assert event.extra == {}


def test_log_event_frozen() -> None:
    event = LogEvent(
        timestamp=1704067260.0,
        level="error",
        event="worker_failed",
    )
    with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
        event.level = "info"  # type: ignore[misc]
