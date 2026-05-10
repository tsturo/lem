# pyright: strict
"""Main run loop, phase iteration, daemon entry."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, NamedTuple

import jinja2

from lem.control import ControlAction, clear_control, read_control
from lem.failure import breaker
from lem.failure.ceiling import (
    check_cost_ceiling,
    check_wall_clock,
    project_worker_cost,
)
from lem.hooks import fire_on_complete, fire_on_error, load_hook_config, post_webhook
from lem.notify import notify
from lem.phases import PHASES, archive_pruner_losers
from lem.post_synthesis import post_synthesize_verdict_check
from lem.render.deliverables import render_deliverables
from lem.state.cost import aggregate_phase, run_total
from lem.state.events import write_event
from lem.state.log import append_log
from lem.state.run_state import write_state
from lem.types import (
    AuthExpired,
    LogEvent,
    PhaseSpec,
    Profile,
    RunState,
    WorkerInvocation,
    WorkerResult,
)
from lem.workers.dispatch import dispatch_worker


class ProgressEvent(NamedTuple):
    """Lightweight progress signal for live status output (`lem refine --attach`).

    Emitted at phase boundaries. Worker-level events stay in meta/log.jsonl;
    this stream is only the phase-grain summary intended for terminal display.
    """

    kind: Literal["phase_start", "phase_done", "phase_skipped"]
    phase_id: str
    roles: tuple[str, ...] = ()
    duration_s: float = 0.0
    cost_usd: float = 0.0
    success: bool = True


@dataclass(frozen=True)
class OrchestratorConfig:
    max_concurrent: int = 4
    # max_cost: dollar ceiling for users on metered API billing. None = off
    # (the default for Claude Max users, where dollar costs are notional).
    # The cost-tracking machinery still records cost.jsonl regardless; only
    # the abort behavior is gated on this being set.
    max_cost: float | None = None
    max_wall_clock_s: float = 4 * 60 * 60
    on_complete: Callable[[RunState], None] | None = None
    on_error: Callable[[RunState], None] | None = None
    progress_cb: Callable[[ProgressEvent], None] | None = None
    webhook_url: str | None = None
    # Flags forwarded to the deliverable render pass to enable flag-gated
    # deliverables. Members map to keys in profile.flag_gated_deliverables
    # (e.g. "--with-pitch", "--with-roadmap", "--with-techstack").
    requested_flags: frozenset[str] = frozenset()
    parent_run_id: str | None = None
    branch_label: str | None = None
    iteration_context_file: Path | None = None


def run_orchestrator(
    workspace_path: Path,
    profile: Profile,
    config: OrchestratorConfig | None = None,
) -> RunState:
    """Run the full pipeline. Returns the final RunState."""
    cfg = config or OrchestratorConfig()
    hook_config = load_hook_config(workspace_path)
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

            if phase.setup_fn is not None:
                phase.setup_fn(state, profile)

            if phase.gate_fn and not phase.gate_fn(state):
                state.phase = phase.id
                _log(workspace_path, "phase_skipped", phase=phase.id)
                _emit_progress(
                    cfg, ProgressEvent(kind="phase_skipped", phase_id=phase.id)
                )
                continue

            invocations = phase.workers_fn(state, profile)
            if not invocations:
                state.phase = phase.id
                _emit_progress(
                    cfg, ProgressEvent(kind="phase_skipped", phase_id=phase.id)
                )
                continue

            if cfg.max_cost is not None:
                projected_phase_cost = sum(
                    project_worker_cost(
                        model=inv.model,
                        input_estimate=_estimate_input_tokens(inv),
                        output_cap=inv.max_output_tokens,
                    )
                    for inv in invocations
                )
                cost_verdict = check_cost_ceiling(
                    state, projected_phase_cost, max_cost=cfg.max_cost
                )
                if cost_verdict.breach:
                    state.status = "cost-aborted"
                    state.error = (
                        f"cost ceiling breach: "
                        f"current={cost_verdict.current_spend:.4f} + "
                        f"projected={cost_verdict.projected_worker_cost:.4f} > "
                        f"max={cost_verdict.max_cost:.2f}"
                    )
                    break

            phase_roles = tuple(inv.role_path.stem for inv in invocations)
            _emit_progress(
                cfg,
                ProgressEvent(kind="phase_start", phase_id=phase.id, roles=phase_roles),
            )
            phase_t0 = time.time()
            cost_before = state.cost_so_far

            results = _dispatch_phase(invocations, profile, phase, cfg, workspace_path)

            aggregate_phase(workspace_path, phase.id, state.run_id)

            if phase.id == "2.3":
                archive_pruner_losers(state, profile)

            if phase.id == "4":
                downgraded = post_synthesize_verdict_check(state, profile)
                # Render after the verdict-check so meta/synthesis.md is the
                # authoritative source for both the recommendation field and
                # the rendered deliverables.
                synth_path = workspace_path / "meta" / "synthesis.md"
                if synth_path.exists():
                    render_deliverables(
                        workspace_path,
                        profile,
                        requested_flags=set(cfg.requested_flags),
                    )
                _ = downgraded

            verdict = breaker.evaluate_phase(phase.id, results)
            state.cost_so_far = run_total(workspace_path)
            _emit_progress(
                cfg,
                ProgressEvent(
                    kind="phase_done",
                    phase_id=phase.id,
                    roles=phase_roles,
                    duration_s=time.time() - phase_t0,
                    cost_usd=state.cost_so_far - cost_before,
                    success=not verdict.should_abort,
                ),
            )
            if verdict.should_abort:
                state.status = "failed"
                state.error = verdict.reason
                break

            state.phase = phase.id
            state.last_event_at = time.time()
            write_state(state)
        else:
            state.status = "completed"

        if state.status == "completed":
            if cfg.on_complete:
                cfg.on_complete(state)
            fire_on_complete(state, hook_config)
        else:
            if cfg.on_error:
                cfg.on_error(state)
            fire_on_error(state, hook_config)

        if cfg.webhook_url:
            post_webhook(cfg.webhook_url, state)

    except AuthExpired:
        state.status = "auth_expired"
        state.error = "auth_expired: claude CLI not authenticated (exit 69)"
        if cfg.on_error:
            try:
                cfg.on_error(state)
            except Exception:
                pass
        fire_on_error(state, hook_config)

    except Exception as exc:
        state.status = "failed"
        state.error = f"orchestrator crashed: {exc}"
        if cfg.on_error:
            try:
                cfg.on_error(state)
            except Exception:
                pass
        fire_on_error(state, hook_config)

    write_state(state)
    notify(state)
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


def _estimate_input_tokens(inv: WorkerInvocation) -> int:
    total_chars = 0
    for p in inv.allowed_read_paths:
        try:
            total_chars += p.stat().st_size
        except OSError:
            pass
    return total_chars // 4


def _record_event(
    workspace_path: Path, phase_id: str, inv: WorkerInvocation, result: WorkerResult
) -> None:
    write_event(
        workspace_path,
        phase=phase_id,
        role=inv.role_path.stem,
        payload={
            "role": inv.role_path.stem,
            "model": inv.model,
            "tokens_in": result.tokens_in,
            "tokens_out": result.tokens_out,
            "duration_s": result.duration_s,
            "attempt": 1,
            "timestamp": time.time(),
        },
    )


def _dispatch_phase(
    invocations: list[WorkerInvocation],
    profile: Profile,
    phase: PhaseSpec,
    config: OrchestratorConfig,
    workspace_path: Path,
) -> list[WorkerResult]:
    if phase.parallel:
        return asyncio.run(
            _dispatch_parallel(invocations, profile, config, workspace_path, phase.id)
        )
    return _dispatch_sequential(invocations, profile, workspace_path, phase.id)


async def _dispatch_parallel(
    invocations: list[WorkerInvocation],
    profile: Profile,
    config: OrchestratorConfig,
    workspace_path: Path,
    phase_id: str,
) -> list[WorkerResult]:
    sem = asyncio.Semaphore(config.max_concurrent)

    async def _one(inv: WorkerInvocation) -> WorkerResult:
        async with sem:
            sys_prompt, tools = _resolve_role(inv, profile)
            schema = _resolve_schema(inv, profile)
            result = await asyncio.to_thread(
                dispatch_worker, inv, sys_prompt, tools, output_schema=schema
            )
            _record_event(workspace_path, phase_id, inv, result)
            return result

    results: list[WorkerResult] = list(
        await asyncio.gather(*(_one(inv) for inv in invocations))
    )
    return results


def _dispatch_sequential(
    invocations: list[WorkerInvocation],
    profile: Profile,
    workspace_path: Path,
    phase_id: str,
) -> list[WorkerResult]:
    results: list[WorkerResult] = []
    for inv in invocations:
        sys_prompt, tools = _resolve_role(inv, profile)
        schema = _resolve_schema(inv, profile)
        result = dispatch_worker(inv, sys_prompt, tools, output_schema=schema)
        _record_event(workspace_path, phase_id, inv, result)
        results.append(result)
    return results


def _resolve_role(inv: WorkerInvocation, profile: Profile) -> tuple[str, list[str]]:
    role_name = inv.role_path.stem
    role = profile.roles.get(role_name) or profile.process_roles.get(role_name)
    if role is None:
        raise ValueError(f"role not found in profile: {role_name}")
    # ChainableUndefined: missing vars render as empty string, not an exception.
    template = jinja2.Template(role.system_prompt, undefined=jinja2.ChainableUndefined)
    system_prompt = template.render(**inv.extra_context)
    return system_prompt, role.tools


def _resolve_schema(
    inv: WorkerInvocation, profile: Profile
) -> dict[str, object] | None:
    role_name = inv.role_path.stem
    role = profile.roles.get(role_name) or profile.process_roles.get(role_name)
    return role.output_schema if role else None


def _emit_progress(cfg: OrchestratorConfig, event: ProgressEvent) -> None:
    if cfg.progress_cb is None:
        return
    try:
        cfg.progress_cb(event)
    except Exception:
        pass


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


