# pyright: strict
"""Dataclasses: WorkerInvocation, WorkerResult, PhaseSpec, Role, Profile, RunState,
CostEvent, LogEvent."""

import dataclasses
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal


@dataclasses.dataclass(frozen=True, kw_only=True)
class WorkerInvocation:
    role_path: Path
    workspace_path: Path
    output_path: Path
    allowed_read_paths: list[Path]
    model: Literal["haiku", "sonnet", "opus"]
    max_output_tokens: int
    timeout_s: int
    extra_context: dict[str, str]


@dataclasses.dataclass(frozen=True, kw_only=True)
class WorkerResult:
    exit_code: int
    output_path: Path
    tokens_in: int
    tokens_out: int
    cost_usd: float
    duration_s: float
    stop_reason: Literal["end_turn", "max_tokens", "timeout", "error"]
    schema_valid: bool
    schema_errors: list[str]


class AuthExpired(Exception):
    """Raised when the claude CLI exits with code 69 (not authenticated)."""


@dataclasses.dataclass(kw_only=True)
class RunState:
    run_id: str
    workspace_path: Path
    phase: str
    status: Literal[
        "running", "completed", "failed",
        "cost-aborted", "wall-clock-aborted", "cancelled",
        "auth_expired",
    ]
    started_at: float
    last_event_at: float
    cost_so_far: float
    error: str | None


@dataclasses.dataclass(frozen=True, kw_only=True)
class Role:
    name: str
    description: str
    model: Literal["haiku", "sonnet", "opus"]
    worker: Literal["cli"]
    phase: str | None
    output_cap: int
    timeout_s: int
    branchable: Literal["yes", "no", "conditional"]
    output_schema: dict[str, Any]
    tools: list[str]
    system_prompt: str
    source_path: Path


@dataclasses.dataclass(frozen=True, kw_only=True)
class Profile:
    name: str
    description: str
    specialists: list[str]
    verdict_options: list[str]
    default_deliverables: list[str]
    flag_gated_deliverables: dict[str, str]
    roles: dict[str, Role]
    process_roles: dict[str, Role]
    intake_prompt: str
    source_dir: Path


@dataclasses.dataclass(frozen=True, kw_only=True)
class PhaseSpec:
    id: str
    name: str
    workers_fn: Callable[[RunState, Profile], list[WorkerInvocation]]
    parallel: bool
    gate_fn: Callable[[RunState], bool] | None = None
    # Optional pre-phase hook. Runs unconditionally BEFORE gate_fn — used for
    # cleanup / file renames / state preparation that must happen even when
    # the phase itself is skipped. Side-effecting; returns None.
    setup_fn: Callable[[RunState, Profile], None] | None = None


@dataclasses.dataclass(frozen=True, kw_only=True)
class CostEvent:
    run_id: str
    phase: str
    role: str
    model: str
    tokens_in: int
    tokens_out: int
    cost_usd: float
    duration_s: float
    timestamp: float
    attempt: int


@dataclasses.dataclass(frozen=True, kw_only=True)
class LogEvent:
    timestamp: float
    level: Literal["debug", "info", "warning", "error"]
    event: str
    phase: str | None = None
    role: str | None = None
    message: str = ""
    # Lambda factory: pyright strict infers dict[Unknown, Unknown] from bare `dict`.
    extra: dict[str, Any] = dataclasses.field(default_factory=lambda: {})
