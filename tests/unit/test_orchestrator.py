# pyright: strict
"""Tests for AuthExpired handling in orchestrator.py."""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Any

import pytest

from lem.orchestrator import OrchestratorConfig, run_orchestrator
from lem.phases import PHASES
from lem.state.run_state import read_state
from lem.types import AuthExpired, Profile, Role, RunState, WorkerInvocation, WorkerResult


def _make_role(name: str = "stub-role") -> Role:
    return Role(
        name=name,
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


_PROCESS_ROLE_NAMES = [
    "jtbd-extractor",
    "disagreement-detector",
    "frame-shifter",
    "branch-skeptic",
    "pruner",
    "distiller",
    "cross-skeptic",
    "kill-case-skeptic",
    "synthesizer",
]


@pytest.fixture
def stub_profile() -> Profile:
    role = _make_role("stub-role")
    process_roles = {name: _make_role(name) for name in _PROCESS_ROLE_NAMES}
    return Profile(
        name="stub",
        description="stub profile",
        specialists=["stub-role"],
        verdict_options=[],
        default_deliverables=[],
        flag_gated_deliverables={},
        roles={"stub-role": role},
        process_roles=process_roles,
        intake_prompt="",
        source_dir=Path("/stub"),
    )


def _make_invocation(workspace_path: Path) -> WorkerInvocation:
    return WorkerInvocation(
        role_path=workspace_path / "stub-role.md",
        workspace_path=workspace_path,
        output_path=workspace_path / "out.json",
        allowed_read_paths=[],
        model="haiku",
        max_output_tokens=1024,
        timeout_s=30,
        extra_context={},
    )


def _ok_result(inv: WorkerInvocation) -> WorkerResult:
    return WorkerResult(
        exit_code=0,
        output_path=inv.output_path,
        tokens_in=10,
        tokens_out=5,
        cost_usd=0.0,
        duration_s=0.01,
        stop_reason="end_turn",
        schema_valid=True,
        schema_errors=[],
    )


def _patch_phase_workers(
    monkeypatch: pytest.MonkeyPatch,
    phase_id: str,
    workers_fn: Any,
) -> None:
    import lem.orchestrator as _orch
    patched = [
        dataclasses.replace(p, workers_fn=workers_fn) if p.id == phase_id else p
        for p in _orch.PHASES
    ]
    monkeypatch.setattr("lem.orchestrator.PHASES", patched)


def _patch_all_phases_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    empty: Any = lambda s, p: []
    patched = [dataclasses.replace(p, workers_fn=empty) for p in PHASES]
    monkeypatch.setattr("lem.orchestrator.PHASES", patched)


def test_auth_expired_sets_status(
    tmp_path: Path, stub_profile: Profile, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When dispatch_worker raises AuthExpired, state.status must be 'auth_expired'."""
    inv = _make_invocation(tmp_path)
    _patch_all_phases_empty(monkeypatch)
    _patch_phase_workers(monkeypatch, "0", lambda s, p: [inv])

    def auth_fail(
        i: WorkerInvocation, sp: str, tools: list[str], *, output_schema: Any = None
    ) -> WorkerResult:
        raise AuthExpired()

    monkeypatch.setattr("lem.orchestrator.dispatch_worker", auth_fail)

    state = run_orchestrator(tmp_path, stub_profile)

    assert state.status == "auth_expired"
    assert state.error is not None
    assert "auth_expired" in state.error


def test_auth_expired_persisted_to_state_json(
    tmp_path: Path, stub_profile: Profile, monkeypatch: pytest.MonkeyPatch
) -> None:
    """auth_expired status must be written to state.json."""
    inv = _make_invocation(tmp_path)
    _patch_all_phases_empty(monkeypatch)
    _patch_phase_workers(monkeypatch, "0", lambda s, p: [inv])

    def auth_fail(
        i: WorkerInvocation, sp: str, tools: list[str], *, output_schema: Any = None
    ) -> WorkerResult:
        raise AuthExpired()

    monkeypatch.setattr("lem.orchestrator.dispatch_worker", auth_fail)

    run_orchestrator(tmp_path, stub_profile)

    persisted = read_state(tmp_path)
    assert persisted.status == "auth_expired"


def test_auth_expired_calls_on_error_hook(
    tmp_path: Path, stub_profile: Profile, monkeypatch: pytest.MonkeyPatch
) -> None:
    """on_error callback must be invoked on AuthExpired, not on_complete."""
    inv = _make_invocation(tmp_path)
    _patch_all_phases_empty(monkeypatch)
    _patch_phase_workers(monkeypatch, "0", lambda s, p: [inv])

    def auth_fail(
        i: WorkerInvocation, sp: str, tools: list[str], *, output_schema: Any = None
    ) -> WorkerResult:
        raise AuthExpired()

    monkeypatch.setattr("lem.orchestrator.dispatch_worker", auth_fail)

    completed: list[RunState] = []
    errored: list[RunState] = []
    cfg = OrchestratorConfig(on_complete=completed.append, on_error=errored.append)

    run_orchestrator(tmp_path, stub_profile, cfg)

    assert len(completed) == 0
    assert len(errored) == 1
    assert errored[0].status == "auth_expired"


def test_auth_expired_does_not_mask_as_orchestrator_crash(
    tmp_path: Path, stub_profile: Profile, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AuthExpired must not appear as 'orchestrator crashed' in state.error."""
    inv = _make_invocation(tmp_path)
    _patch_all_phases_empty(monkeypatch)
    _patch_phase_workers(monkeypatch, "0", lambda s, p: [inv])

    def auth_fail(
        i: WorkerInvocation, sp: str, tools: list[str], *, output_schema: Any = None
    ) -> WorkerResult:
        raise AuthExpired()

    monkeypatch.setattr("lem.orchestrator.dispatch_worker", auth_fail)

    state = run_orchestrator(tmp_path, stub_profile)

    assert "orchestrator crashed" not in (state.error or "")
