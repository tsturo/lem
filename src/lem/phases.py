# pyright: strict
"""Declarative PHASES: list[PhaseSpec]."""

from pathlib import Path
from typing import cast

from lem.schema.parser import parse_file
from lem.types import PhaseSpec, Profile, RunState, WorkerInvocation


def _intake_workers_fn(state: RunState, profile: Profile) -> list[WorkerInvocation]:
    return []


def _jtbd_workers_fn(state: RunState, profile: Profile) -> list[WorkerInvocation]:
    return [WorkerInvocation(
        role_path=profile.source_dir.parent / "process_roles" / "jtbd-extractor.md",
        workspace_path=state.workspace_path,
        output_path=state.workspace_path / "frame-shifter" / "jtbd.md",
        allowed_read_paths=[state.workspace_path / "idea.md"],
        model="sonnet",
        max_output_tokens=300,
        timeout_s=300,
        extra_context={},
    )]


def _discover_workers_fn(state: RunState, profile: Profile) -> list[WorkerInvocation]:
    invocations: list[WorkerInvocation] = []
    for spec_name in profile.specialists:
        role_path = profile.source_dir / "roles" / f"{spec_name}.md"
        invocations.append(WorkerInvocation(
            role_path=role_path,
            workspace_path=state.workspace_path,
            output_path=state.workspace_path / spec_name / "draft-1.md",
            allowed_read_paths=[
                state.workspace_path / "idea.md",
                state.workspace_path / "assumptions.yaml",
                state.workspace_path / "frame-shifter" / "jtbd.md",
            ],
            model="sonnet",
            max_output_tokens=2000,
            timeout_s=600,
            extra_context={},
        ))
    return invocations


def _disagreement_workers_fn(
    state: RunState, profile: Profile
) -> list[WorkerInvocation]:
    drafts = [state.workspace_path / s / "draft-1.md" for s in profile.specialists]
    detector = profile.source_dir.parent / "process_roles" / "disagreement-detector.md"
    return [WorkerInvocation(
        role_path=detector,
        workspace_path=state.workspace_path,
        output_path=state.workspace_path / "disagreements.md",
        allowed_read_paths=drafts,
        model="sonnet",
        max_output_tokens=1500,
        timeout_s=600,
        extra_context={},
    )]


def _reframe_workers_fn(state: RunState, profile: Profile) -> list[WorkerInvocation]:
    return []


def _explore_workers_fn(state: RunState, profile: Profile) -> list[WorkerInvocation]:
    return []


def _distill_workers_fn(state: RunState, profile: Profile) -> list[WorkerInvocation]:
    return []


def _critique_workers_fn(state: RunState, profile: Profile) -> list[WorkerInvocation]:
    return []


def _synthesize_workers_fn(state: RunState, profile: Profile) -> list[WorkerInvocation]:
    return []


def _explore_gate_fn(state: RunState) -> bool:
    path: Path = state.workspace_path / "disagreements.md"
    if not path.exists():
        return False
    try:
        doc = parse_file(path)
        axes = doc.frontmatter.get("axes_by_domain")
        if not isinstance(axes, dict) or not axes:
            return False
        typed = cast("dict[str, object]", axes)
        return any(typed[k] for k in typed)
    except Exception:
        return False


PHASES: list[PhaseSpec] = [
    PhaseSpec(id="0", name="Intake", workers_fn=_intake_workers_fn, parallel=False),
    PhaseSpec(id="0.5", name="JTBD", workers_fn=_jtbd_workers_fn, parallel=False),
    PhaseSpec(id="1", name="Discover", workers_fn=_discover_workers_fn, parallel=True),
    PhaseSpec(
        id="1.5",
        name="Disagreement",
        workers_fn=_disagreement_workers_fn,
        parallel=False,
    ),
    PhaseSpec(id="1.6", name="Reframe", workers_fn=_reframe_workers_fn, parallel=False),
    PhaseSpec(
        id="2",
        name="Explore",
        workers_fn=_explore_workers_fn,
        parallel=True,
        gate_fn=_explore_gate_fn,
    ),
    PhaseSpec(id="2.5", name="Distill", workers_fn=_distill_workers_fn, parallel=False),
    PhaseSpec(id="3", name="Critique", workers_fn=_critique_workers_fn, parallel=False),
    PhaseSpec(
        id="4", name="Synthesize", workers_fn=_synthesize_workers_fn, parallel=False
    ),
]

_PHASE_INDEX: dict[str, int] = {p.id: i for i, p in enumerate(PHASES)}


def get_phase(phase_id: str) -> PhaseSpec:
    """Return the PhaseSpec with the given id, or raise KeyError."""
    try:
        return PHASES[_PHASE_INDEX[phase_id]]
    except KeyError:
        raise KeyError(phase_id) from None


def phase_index(phase_id: str) -> int:
    """Return 0-based index of the phase in PHASES, or raise KeyError."""
    try:
        return _PHASE_INDEX[phase_id]
    except KeyError:
        raise KeyError(phase_id) from None


def next_phase(phase_id: str) -> PhaseSpec | None:
    """Return the next PhaseSpec in pipeline order, or None if last."""
    idx = phase_index(phase_id)
    next_idx = idx + 1
    if next_idx >= len(PHASES):
        return None
    return PHASES[next_idx]
