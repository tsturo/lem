# pyright: strict
"""Main run loop, phase iteration, daemon entry."""

from __future__ import annotations

import asyncio
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lem.control import ControlAction, clear_control, read_control
from lem.failure import breaker
from lem.failure.ceiling import check_wall_clock
from lem.phases import PHASES
from lem.state.cost import aggregate_phase, run_total
from lem.state.log import append_log
from lem.state.run_state import write_state
from lem.types import (
    LogEvent,
    PhaseSpec,
    Profile,
    RunState,
    WorkerInvocation,
    WorkerResult,
)
from lem.workers.dispatch import dispatch_worker


@dataclass(frozen=True)
class OrchestratorConfig:
    max_concurrent: int = 4
    max_cost: float = 25.0
    max_wall_clock_s: float = 4 * 60 * 60
    on_complete: Callable[[RunState], None] | None = None
    on_error: Callable[[RunState], None] | None = None
    webhook_url: str | None = None


def run_orchestrator(
    workspace_path: Path,
    profile: Profile,
    config: OrchestratorConfig | None = None,
) -> RunState:
    """Run the full pipeline. Returns the final RunState."""
    cfg = config or OrchestratorConfig()
    state = _initialize_state(workspace_path, profile)
    write_state(state)
    try:
        for phase in PHASES:
            action = read_control(workspace_path)
            if action and action.action == "pause":
                resume_action = _wait_for_resume(workspace_path)
                if resume_action.action == "cancel":
                    state.status = "cancelled"
                    break
                clear_control(workspace_path)

            elif action and action.action == "cancel":
                state.status = "cancelled"
                break

            if check_wall_clock(state, max_wall_clock_s=cfg.max_wall_clock_s):
                state.status = "wall-clock-aborted"
                state.error = "max wall-clock exceeded"
                break

            if phase.gate_fn and not phase.gate_fn(state):
                state.phase = phase.id
                _log(workspace_path, "phase_skipped", phase=phase.id)
                continue

            invocations = phase.workers_fn(state, profile)
            if not invocations:
                state.phase = phase.id
                continue

            results = _dispatch_phase(invocations, profile, phase, cfg)

            aggregate_phase(workspace_path, phase.id, state.run_id)

            verdict = breaker.evaluate_phase(phase.id, results)
            if verdict.should_abort:
                state.status = "failed"
                state.error = verdict.reason
                break

            state.phase = phase.id
            state.cost_so_far = run_total(workspace_path)
            state.last_event_at = time.time()
            write_state(state)
        else:
            state.status = "completed"

        if state.status == "completed" and cfg.on_complete:
            cfg.on_complete(state)
        elif state.status != "completed" and cfg.on_error:
            cfg.on_error(state)

        if cfg.webhook_url:
            _post_webhook(cfg.webhook_url, state)

    except Exception as exc:
        state.status = "failed"
        state.error = f"orchestrator crashed: {exc}"
        if cfg.on_error:
            try:
                cfg.on_error(state)
            except Exception:
                pass

    write_state(state)
    return state


def _initialize_state(workspace_path: Path, profile: Profile) -> RunState:
    run_id = workspace_path.name
    now = time.time()
    return RunState(
        run_id=run_id,
        workspace_path=workspace_path,
        phase="0",
        status="running",
        started_at=now,
        last_event_at=now,
        cost_so_far=0.0,
        error=None,
    )


def _wait_for_resume(workspace_path: Path) -> ControlAction:
    while True:
        action: ControlAction | None = read_control(workspace_path)
        if action and action.action in ("resume", "cancel"):
            return action
        time.sleep(1)


def _dispatch_phase(
    invocations: list[WorkerInvocation],
    profile: Profile,
    phase: PhaseSpec,
    config: OrchestratorConfig,
) -> list[WorkerResult]:
    if phase.parallel:
        return asyncio.run(_dispatch_parallel(invocations, profile, config))
    return _dispatch_sequential(invocations, profile)


async def _dispatch_parallel(
    invocations: list[WorkerInvocation],
    profile: Profile,
    config: OrchestratorConfig,
) -> list[WorkerResult]:
    sem = asyncio.Semaphore(config.max_concurrent)

    async def _one(inv: WorkerInvocation) -> WorkerResult:
        async with sem:
            sys_prompt, tools = _resolve_role(inv, profile)
            schema = _resolve_schema(inv, profile)
            return await asyncio.to_thread(
                dispatch_worker, inv, sys_prompt, tools, output_schema=schema
            )

    results: list[WorkerResult] = list(
        await asyncio.gather(*(_one(inv) for inv in invocations))
    )
    return results


def _dispatch_sequential(
    invocations: list[WorkerInvocation],
    profile: Profile,
) -> list[WorkerResult]:
    results: list[WorkerResult] = []
    for inv in invocations:
        sys_prompt, tools = _resolve_role(inv, profile)
        schema = _resolve_schema(inv, profile)
        results.append(dispatch_worker(inv, sys_prompt, tools, output_schema=schema))
    return results


def _resolve_role(inv: WorkerInvocation, profile: Profile) -> tuple[str, list[str]]:
    role_name = inv.role_path.stem
    role = profile.roles.get(role_name) or profile.process_roles.get(role_name)
    if role is None:
        raise ValueError(f"role not found in profile: {role_name}")
    return role.system_prompt, role.tools


def _resolve_schema(
    inv: WorkerInvocation, profile: Profile
) -> dict[str, object] | None:
    role_name = inv.role_path.stem
    role = profile.roles.get(role_name) or profile.process_roles.get(role_name)
    return role.output_schema if role else None


def _log(workspace_path: Path, event: str, *, phase: str) -> None:
    append_log(
        workspace_path,
        LogEvent(
            timestamp=time.time(),
            level="info",
            event=event,
            phase=phase,
        ),
    )


def _post_webhook(url: str, state: RunState) -> None:
    import json
    import urllib.request

    payload: dict[str, Any] = {
        "run_id": state.run_id,
        "verdict": state.status,
        "cost": state.cost_so_far,
        "duration": state.last_event_at - state.started_at,
        "deliverables_path": str(state.workspace_path / "deliverables"),
        "status": state.status,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}
    )
    try:
        urllib.request.urlopen(req, timeout=10).read()
    except Exception as exc:
        print(f"webhook failed: {exc}", file=sys.stderr)
