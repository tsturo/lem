# pyright: strict
"""Integration tests for orchestrator.py — full pipeline with stubbed workers."""

from __future__ import annotations

import dataclasses
import json
import threading
import time
from pathlib import Path
from typing import Any

import pytest

from lem.control import write_control
from lem.orchestrator import OrchestratorConfig, run_orchestrator
from lem.phases import PHASES
from lem.state.run_state import read_state
from lem.types import Profile, Role, RunState, WorkerInvocation, WorkerResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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


def _fail_result(inv: WorkerInvocation) -> WorkerResult:
    return WorkerResult(
        exit_code=1,
        output_path=inv.output_path,
        tokens_in=0,
        tokens_out=0,
        cost_usd=0.0,
        duration_s=0.01,
        stop_reason="error",
        schema_valid=False,
        schema_errors=["failed"],
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


def _patch_phase_workers(
    monkeypatch: pytest.MonkeyPatch,
    phase_id: str,
    workers_fn: Any,
    *,
    gate_fn: Any = ...,
) -> None:
    """Replace workers_fn (and optionally gate_fn) on the named phase in lem.orchestrator.PHASES."""
    import lem.orchestrator as _orch
    patched = []
    for p in _orch.PHASES:
        if p.id == phase_id:
            kwargs: dict[str, Any] = {"workers_fn": workers_fn}
            if gate_fn is not ...:
                kwargs["gate_fn"] = gate_fn
            patched.append(dataclasses.replace(p, **kwargs))
        else:
            patched.append(p)
    monkeypatch.setattr("lem.orchestrator.PHASES", patched)


def _patch_all_phases_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set every phase's workers_fn to return [] for isolation."""
    empty: Any = lambda s, p: []
    patched = [dataclasses.replace(p, workers_fn=empty) for p in PHASES]
    monkeypatch.setattr("lem.orchestrator.PHASES", patched)


# ---------------------------------------------------------------------------
# 1. Full pipeline runs end-to-end
# ---------------------------------------------------------------------------


def test_full_pipeline_completes(
    tmp_path: Path, stub_profile: Profile, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "lem.orchestrator.dispatch_worker",
        lambda inv, sp, tools, output_schema=None: _ok_result(inv),
    )

    state = run_orchestrator(tmp_path, stub_profile)
    assert state.status == "completed"

    persisted = read_state(tmp_path)
    assert persisted.status == "completed"


def test_full_pipeline_iterates_all_phases(
    tmp_path: Path, stub_profile: Profile, monkeypatch: pytest.MonkeyPatch
) -> None:
    dispatched: list[str] = []

    def fake_dispatch(
        inv: WorkerInvocation, sp: str, tools: list[str], *, output_schema: Any = None
    ) -> WorkerResult:
        dispatched.append(inv.role_path.stem)
        return _ok_result(inv)

    inv = _make_invocation(tmp_path)
    _patch_all_phases_empty(monkeypatch)
    _patch_phase_workers(monkeypatch, "0", lambda s, p: [inv])
    monkeypatch.setattr("lem.orchestrator.dispatch_worker", fake_dispatch)

    state = run_orchestrator(tmp_path, stub_profile)
    assert state.status == "completed"
    assert len(dispatched) == 1


# ---------------------------------------------------------------------------
# 2. Pause / resume via control.json
# ---------------------------------------------------------------------------


def test_pause_then_resume(
    tmp_path: Path, stub_profile: Profile, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "lem.orchestrator.dispatch_worker",
        lambda i, sp, t, output_schema=None: _ok_result(i),
    )

    write_control(tmp_path, "pause")
    threading.Timer(0.3, lambda: write_control(tmp_path, "resume")).start()

    state = run_orchestrator(tmp_path, stub_profile)
    assert state.status == "completed"


# ---------------------------------------------------------------------------
# 3. Cancel via control.json
# ---------------------------------------------------------------------------


def test_cancel_stops_run(
    tmp_path: Path, stub_profile: Profile, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "lem.orchestrator.dispatch_worker",
        lambda i, sp, t, output_schema=None: _ok_result(i),
    )

    write_control(tmp_path, "cancel")
    state = run_orchestrator(tmp_path, stub_profile)

    assert state.status == "cancelled"
    persisted = read_state(tmp_path)
    assert persisted.status == "cancelled"


# ---------------------------------------------------------------------------
# 4. gate_fn=False skips phase, no workers dispatched, log entry written
# ---------------------------------------------------------------------------


def test_gate_fn_false_skips_phase(
    tmp_path: Path, stub_profile: Profile, monkeypatch: pytest.MonkeyPatch
) -> None:
    dispatched: list[WorkerInvocation] = []

    def fake_dispatch(
        inv: WorkerInvocation, sp: str, tools: list[str], *, output_schema: Any = None
    ) -> WorkerResult:
        dispatched.append(inv)
        return _ok_result(inv)

    inv = _make_invocation(tmp_path)
    _patch_all_phases_empty(monkeypatch)
    _patch_phase_workers(monkeypatch, "0", lambda s, p: [inv], gate_fn=lambda s: False)
    monkeypatch.setattr("lem.orchestrator.dispatch_worker", fake_dispatch)

    state = run_orchestrator(tmp_path, stub_profile)
    assert state.status == "completed"
    assert dispatched == []

    log_path = tmp_path / "meta" / "log.jsonl"
    assert log_path.exists()
    lines = [json.loads(ln) for ln in log_path.read_text().splitlines() if ln.strip()]
    skipped = [ln for ln in lines if ln.get("event") == "phase_skipped"]
    assert any(ln["phase"] == "0" for ln in skipped)


# ---------------------------------------------------------------------------
# 5. Phase failure: >50% workers fail → status="failed"
# ---------------------------------------------------------------------------


def test_phase_failure_aborts_run(
    tmp_path: Path, stub_profile: Profile, monkeypatch: pytest.MonkeyPatch
) -> None:
    base = _make_invocation(tmp_path)
    invs = [
        dataclasses.replace(base, output_path=tmp_path / f"out{i}.json")
        for i in range(3)
    ]

    _patch_phase_workers(monkeypatch, "0", lambda s, p: invs)
    monkeypatch.setattr(
        "lem.orchestrator.dispatch_worker",
        lambda inv, sp, t, output_schema=None: _fail_result(inv),
    )

    state = run_orchestrator(tmp_path, stub_profile)
    assert state.status == "failed"
    assert state.error is not None
    assert "0" in state.error


# ---------------------------------------------------------------------------
# 6. Wall-clock cap aborts run
# ---------------------------------------------------------------------------


def test_wall_clock_cap_aborts(
    tmp_path: Path, stub_profile: Profile, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "lem.orchestrator.dispatch_worker",
        lambda i, sp, t, output_schema=None: _ok_result(i),
    )

    cfg = OrchestratorConfig(max_wall_clock_s=0.0)
    state = run_orchestrator(tmp_path, stub_profile, config=cfg)

    assert state.status == "wall-clock-aborted"
    assert state.error is not None


# ---------------------------------------------------------------------------
# 7. on_complete and on_error hooks
# ---------------------------------------------------------------------------


def test_on_complete_called_on_success(
    tmp_path: Path, stub_profile: Profile, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "lem.orchestrator.dispatch_worker",
        lambda i, sp, t, output_schema=None: _ok_result(i),
    )

    completed: list[RunState] = []
    errored: list[RunState] = []

    cfg = OrchestratorConfig(on_complete=completed.append, on_error=errored.append)
    state = run_orchestrator(tmp_path, stub_profile, config=cfg)

    assert state.status == "completed"
    assert len(completed) == 1
    assert len(errored) == 0
    assert completed[0].status == "completed"


def test_on_error_called_on_failure(
    tmp_path: Path, stub_profile: Profile, monkeypatch: pytest.MonkeyPatch
) -> None:
    inv = _make_invocation(tmp_path)
    _patch_phase_workers(monkeypatch, "0", lambda s, p: [inv])
    monkeypatch.setattr(
        "lem.orchestrator.dispatch_worker",
        lambda i, sp, t, output_schema=None: _fail_result(i),
    )

    completed: list[RunState] = []
    errored: list[RunState] = []

    cfg = OrchestratorConfig(on_complete=completed.append, on_error=errored.append)
    state = run_orchestrator(tmp_path, stub_profile, config=cfg)

    assert state.status == "failed"
    assert len(errored) == 1
    assert len(completed) == 0


# ---------------------------------------------------------------------------
# 8. Webhook called with correct payload
# ---------------------------------------------------------------------------


def test_webhook_called_on_completion(
    tmp_path: Path, stub_profile: Profile, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "lem.orchestrator.dispatch_worker",
        lambda i, sp, t, output_schema=None: _ok_result(i),
    )

    captured_payloads: list[dict[str, Any]] = []

    class FakeResponse:
        def read(self) -> bytes:
            return b""

    def fake_urlopen(req: Any, timeout: int = 10) -> FakeResponse:
        body = req.data
        captured_payloads.append(json.loads(body))
        return FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    cfg = OrchestratorConfig(webhook_url="http://example.com/hook")
    state = run_orchestrator(tmp_path, stub_profile, config=cfg)

    assert state.status == "completed"
    assert len(captured_payloads) == 1
    payload = captured_payloads[0]
    assert payload["run_id"] == tmp_path.name
    assert payload["status"] == "completed"
    assert "cost" in payload
    assert "duration" in payload


# ---------------------------------------------------------------------------
# 9. Parallel phase dispatches all workers; semaphore limits concurrency
# ---------------------------------------------------------------------------


def test_parallel_phase_dispatches_all(
    tmp_path: Path, stub_profile: Profile, monkeypatch: pytest.MonkeyPatch
) -> None:
    base = _make_invocation(tmp_path)
    invs = [
        dataclasses.replace(base, output_path=tmp_path / f"out{i}.json")
        for i in range(4)
    ]
    dispatched: list[WorkerInvocation] = []

    def fake_dispatch(
        inv: WorkerInvocation, sp: str, tools: list[str], *, output_schema: Any = None
    ) -> WorkerResult:
        dispatched.append(inv)
        return _ok_result(inv)

    # Phase "1" (Discover) is parallel=True
    _patch_all_phases_empty(monkeypatch)
    _patch_phase_workers(monkeypatch, "1", lambda s, p: invs)
    monkeypatch.setattr("lem.orchestrator.dispatch_worker", fake_dispatch)

    state = run_orchestrator(tmp_path, stub_profile)
    assert state.status == "completed"
    assert len(dispatched) == 4


def test_parallel_phase_respects_max_concurrent(
    tmp_path: Path, stub_profile: Profile, monkeypatch: pytest.MonkeyPatch
) -> None:
    base = _make_invocation(tmp_path)
    invs = [
        dataclasses.replace(base, output_path=tmp_path / f"out{i}.json")
        for i in range(4)
    ]

    active = 0
    peak = 0
    lock = threading.Lock()

    def slow_dispatch(
        inv: WorkerInvocation, sp: str, tools: list[str], *, output_schema: Any = None
    ) -> WorkerResult:
        nonlocal active, peak
        with lock:
            active += 1
            if active > peak:
                peak = active
        time.sleep(0.05)
        with lock:
            active -= 1
        return _ok_result(inv)

    _patch_phase_workers(monkeypatch, "1", lambda s, p: invs)
    monkeypatch.setattr("lem.orchestrator.dispatch_worker", slow_dispatch)

    cfg = OrchestratorConfig(max_concurrent=2)
    state = run_orchestrator(tmp_path, stub_profile, config=cfg)

    assert state.status == "completed"
    assert peak <= 2


# ---------------------------------------------------------------------------
# 10. Cancel during pause unblocks the orchestrator
# ---------------------------------------------------------------------------


def test_cancel_during_pause(
    tmp_path: Path, stub_profile: Profile, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "lem.orchestrator.dispatch_worker",
        lambda i, sp, t, output_schema=None: _ok_result(i),
    )

    write_control(tmp_path, "pause")
    threading.Timer(0.3, lambda: write_control(tmp_path, "cancel")).start()

    state = run_orchestrator(tmp_path, stub_profile)
    assert state.status == "cancelled"


# ---------------------------------------------------------------------------
# 11. Phase with zero workers is skipped cleanly (no dispatch)
# ---------------------------------------------------------------------------


def test_empty_workers_fn_skips_dispatch(
    tmp_path: Path, stub_profile: Profile, monkeypatch: pytest.MonkeyPatch
) -> None:
    dispatched: list[WorkerInvocation] = []

    def fake_dispatch(
        inv: WorkerInvocation, sp: str, tools: list[str], *, output_schema: Any = None
    ) -> WorkerResult:
        dispatched.append(inv)
        return _ok_result(inv)

    _patch_all_phases_empty(monkeypatch)
    monkeypatch.setattr("lem.orchestrator.dispatch_worker", fake_dispatch)

    state = run_orchestrator(tmp_path, stub_profile)
    assert state.status == "completed"
    assert dispatched == []


# ---------------------------------------------------------------------------
# 12. state.json updated at phase boundaries
# ---------------------------------------------------------------------------


def test_state_updated_after_phase(
    tmp_path: Path, stub_profile: Profile, monkeypatch: pytest.MonkeyPatch
) -> None:
    inv = _make_invocation(tmp_path)
    _patch_phase_workers(monkeypatch, "0", lambda s, p: [inv])
    monkeypatch.setattr(
        "lem.orchestrator.dispatch_worker",
        lambda i, sp, t, output_schema=None: _ok_result(i),
    )

    run_orchestrator(tmp_path, stub_profile)
    persisted = read_state(tmp_path)

    assert persisted.phase == "4"
    assert persisted.status == "completed"


# ---------------------------------------------------------------------------
# 13. Jinja2 rendering: extra_context substituted into system_prompt
# ---------------------------------------------------------------------------


def _make_role_with_prompt(name: str, system_prompt: str) -> Role:
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
        system_prompt=system_prompt,
        source_path=Path("/stub"),
    )


def test_extra_context_substituted_into_system_prompt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """dispatch_worker must receive the rendered prompt, not the raw template."""
    captured: list[str] = []

    def fake_dispatch(
        inv: WorkerInvocation, sp: str, tools: list[str], *, output_schema: Any = None
    ) -> WorkerResult:
        captured.append(sp)
        return _ok_result(inv)

    role = _make_role_with_prompt("tmpl-role", "Hello {{prompt_fragment}} world")
    profile = Profile(
        name="stub",
        description="",
        specialists=[],
        verdict_options=[],
        default_deliverables=[],
        flag_gated_deliverables={},
        roles={"tmpl-role": role},
        process_roles={name: _make_role(name) for name in _PROCESS_ROLE_NAMES},
        intake_prompt="",
        source_dir=Path("/stub"),
    )

    inv = WorkerInvocation(
        role_path=tmp_path / "tmpl-role.md",
        workspace_path=tmp_path,
        output_path=tmp_path / "out.json",
        allowed_read_paths=[],
        model="haiku",
        max_output_tokens=1024,
        timeout_s=30,
        extra_context={"prompt_fragment": "FRAGMENT_TEXT"},
    )

    _patch_all_phases_empty(monkeypatch)
    _patch_phase_workers(monkeypatch, "0", lambda s, p: [inv])
    monkeypatch.setattr("lem.orchestrator.dispatch_worker", fake_dispatch)

    state = run_orchestrator(tmp_path, profile)
    assert state.status == "completed"
    assert len(captured) == 1
    assert "FRAGMENT_TEXT" in captured[0]
    assert "{{prompt_fragment}}" not in captured[0]


def test_undefined_extra_context_var_renders_as_empty_string(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Missing extra_context keys must not raise — they render as empty string."""
    captured: list[str] = []

    def fake_dispatch(
        inv: WorkerInvocation, sp: str, tools: list[str], *, output_schema: Any = None
    ) -> WorkerResult:
        captured.append(sp)
        return _ok_result(inv)

    role = _make_role_with_prompt("tmpl-role", "Before {{undefined_var}} after")
    profile = Profile(
        name="stub",
        description="",
        specialists=[],
        verdict_options=[],
        default_deliverables=[],
        flag_gated_deliverables={},
        roles={"tmpl-role": role},
        process_roles={name: _make_role(name) for name in _PROCESS_ROLE_NAMES},
        intake_prompt="",
        source_dir=Path("/stub"),
    )

    inv = WorkerInvocation(
        role_path=tmp_path / "tmpl-role.md",
        workspace_path=tmp_path,
        output_path=tmp_path / "out.json",
        allowed_read_paths=[],
        model="haiku",
        max_output_tokens=1024,
        timeout_s=30,
        extra_context={},
    )

    _patch_all_phases_empty(monkeypatch)
    _patch_phase_workers(monkeypatch, "0", lambda s, p: [inv])
    monkeypatch.setattr("lem.orchestrator.dispatch_worker", fake_dispatch)

    state = run_orchestrator(tmp_path, profile)
    assert state.status == "completed"
    assert len(captured) == 1
    assert captured[0] == "Before  after"
    assert "{{undefined_var}}" not in captured[0]


# ---------------------------------------------------------------------------
# 14. Cost-ceiling: low max_cost aborts run
# ---------------------------------------------------------------------------


def test_cost_ceiling_aborts_run(
    tmp_path: Path, stub_profile: Profile, monkeypatch: pytest.MonkeyPatch
) -> None:
    inv = _make_invocation(tmp_path)
    _patch_all_phases_empty(monkeypatch)
    _patch_phase_workers(monkeypatch, "0", lambda s, p: [inv])
    monkeypatch.setattr(
        "lem.orchestrator.dispatch_worker",
        lambda i, sp, t, output_schema=None: _ok_result(i),
    )

    cfg = OrchestratorConfig(max_cost=0.0001)
    state = run_orchestrator(tmp_path, stub_profile, config=cfg)

    assert state.status == "cost-aborted"
    assert state.error is not None
    assert "cost ceiling breach" in state.error


def test_generous_cost_ceiling_completes(
    tmp_path: Path, stub_profile: Profile, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "lem.orchestrator.dispatch_worker",
        lambda i, sp, t, output_schema=None: _ok_result(i),
    )

    cfg = OrchestratorConfig(max_cost=1000.0)
    state = run_orchestrator(tmp_path, stub_profile, config=cfg)

    assert state.status == "completed"
