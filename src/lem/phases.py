# pyright: strict
"""Declarative PHASES: list[PhaseSpec]."""

from pathlib import Path
from typing import Any, cast

import yaml

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
                state.workspace_path / "frame-shifter" / "draft-1.md",
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
    fragment_path = profile.source_dir / "prompt-fragments" / "frame-shifter.md"
    fragment = (
        fragment_path.read_text(encoding="utf-8") if fragment_path.exists() else ""
    )
    return [WorkerInvocation(
        role_path=profile.source_dir.parent / "process_roles" / "frame-shifter.md",
        workspace_path=state.workspace_path,
        output_path=state.workspace_path / "frame-shifter" / "draft-1.md",
        allowed_read_paths=[
            state.workspace_path / "idea.md",
            state.workspace_path / "assumptions.yaml",
            state.workspace_path / "frame-shifter" / "jtbd.md",
        ],
        model="opus",
        max_output_tokens=2500,
        timeout_s=900,
        extra_context={"prompt_fragment": fragment},
    )]


def _read_axes_by_domain(state: RunState) -> dict[str, str]:
    disagreements = state.workspace_path / "disagreements.md"
    if not disagreements.exists():
        return {}
    try:
        doc = parse_file(disagreements)
    except Exception:
        return {}
    raw = doc.frontmatter.get("axes_by_domain")
    if not isinstance(raw, dict):
        return {}
    raw_dict = cast("dict[object, object]", raw)
    return {
        str(k): str(v) for k, v in raw_dict.items()
        if isinstance(v, str) and v.strip()
    }


def _branching_specialists(
    state: RunState, profile: Profile
) -> list[tuple[str, str]]:
    """Return [(spec_name, axis)] for specialists with a non-empty axis."""
    axes = _read_axes_by_domain(state)
    return [
        (s, axes[s])
        for s in profile.specialists
        if axes.get(s, "").strip()
    ]


def _explore_prepare(state: RunState, profile: Profile) -> None:
    """Pre-Phase-2 hook: rename draft-1.md → decision.md for non-branching domains.

    Runs unconditionally before the gate_fn check, so even when the gate
    skips the explore sub-phases the downstream phases (Distill, Critique,
    Synthesize) find a decision.md per specialist.

    Branching domains keep draft-1.md untouched: phase 2.3 will write
    decision.md from the pruner's output.
    """
    axes = _read_axes_by_domain(state)
    for spec_name in profile.specialists:
        domain_dir = state.workspace_path / spec_name
        decision_path = domain_dir / "decision.md"
        draft_path = domain_dir / "draft-1.md"
        is_branching = bool(axes.get(spec_name, "").strip())
        if is_branching:
            continue
        if decision_path.exists():
            continue
        if draft_path.exists():
            draft_path.rename(decision_path)


def _explore_generate_workers_fn(
    state: RunState, profile: Profile
) -> list[WorkerInvocation]:
    """Phase 2.1 — generators. One pair (option-a, option-b) per branching domain."""
    invocations: list[WorkerInvocation] = []
    for spec_name, axis in _branching_specialists(state, profile):
        domain_dir = state.workspace_path / spec_name
        draft_path = domain_dir / "draft-1.md"
        spec_role = profile.source_dir / "roles" / f"{spec_name}.md"
        for k, label in enumerate(("a", "b"), start=1):
            invocations.append(WorkerInvocation(
                role_path=spec_role,
                workspace_path=state.workspace_path,
                output_path=domain_dir / f"option-{label}.md",
                allowed_read_paths=[
                    state.workspace_path / "idea.md",
                    state.workspace_path / "assumptions.yaml",
                    state.workspace_path / "frame-shifter" / "draft-1.md",
                    draft_path,
                ],
                model="sonnet",
                max_output_tokens=2000,
                timeout_s=600,
                extra_context={"branch_axis": axis, "alternative_index": str(k)},
            ))
    return invocations


def _explore_critique_workers_fn(
    state: RunState, profile: Profile
) -> list[WorkerInvocation]:
    """Phase 2.2 — branch-skeptic per option. Reads option files written by 2.1."""
    invocations: list[WorkerInvocation] = []
    branch_skeptic_path = (
        profile.source_dir.parent / "process_roles" / "branch-skeptic.md"
    )
    for spec_name, _axis in _branching_specialists(state, profile):
        domain_dir = state.workspace_path / spec_name
        for label in ("a", "b"):
            invocations.append(WorkerInvocation(
                role_path=branch_skeptic_path,
                workspace_path=state.workspace_path,
                output_path=domain_dir / f"option-{label}.skeptic.md",
                allowed_read_paths=[domain_dir / f"option-{label}.md"],
                model="sonnet",
                max_output_tokens=1000,
                timeout_s=300,
                extra_context={"option_label": label},
            ))
    return invocations


def _explore_prune_workers_fn(
    state: RunState, profile: Profile
) -> list[WorkerInvocation]:
    """Phase 2.3 — pruner per branching domain. Reads 4 files per domain."""
    invocations: list[WorkerInvocation] = []
    pruner_path = profile.source_dir.parent / "process_roles" / "pruner.md"
    for spec_name, _axis in _branching_specialists(state, profile):
        domain_dir = state.workspace_path / spec_name
        invocations.append(WorkerInvocation(
            role_path=pruner_path,
            workspace_path=state.workspace_path,
            output_path=domain_dir / "decision.md",
            allowed_read_paths=[
                domain_dir / "option-a.md",
                domain_dir / "option-a.skeptic.md",
                domain_dir / "option-b.md",
                domain_dir / "option-b.skeptic.md",
            ],
            model="sonnet",
            max_output_tokens=2000,
            timeout_s=300,
            extra_context={"domain": spec_name},
        ))
    return invocations


def _distill_workers_fn(state: RunState, profile: Profile) -> list[WorkerInvocation]:
    decisions = [state.workspace_path / s / "decision.md" for s in profile.specialists]
    core_inputs = [
        state.workspace_path / "idea.md",
        state.workspace_path / "assumptions.yaml",
        state.workspace_path / "frame-shifter" / "draft-1.md",
    ]
    return [WorkerInvocation(
        role_path=profile.source_dir.parent / "process_roles" / "distiller.md",
        workspace_path=state.workspace_path,
        output_path=state.workspace_path / "meta" / "distilled" / "post-explore.md",
        allowed_read_paths=[*core_inputs, *(d for d in decisions if d.exists())],
        model="haiku",
        max_output_tokens=8000,
        timeout_s=300,
        extra_context={},
    )]


def _critique_workers_fn(state: RunState, profile: Profile) -> list[WorkerInvocation]:
    decisions = [state.workspace_path / s / "decision.md" for s in profile.specialists]
    distilled = state.workspace_path / "meta" / "distilled" / "post-explore.md"

    cross_inv = WorkerInvocation(
        role_path=profile.source_dir.parent / "process_roles" / "cross-skeptic.md",
        workspace_path=state.workspace_path,
        output_path=state.workspace_path / "cross-critique.md",
        allowed_read_paths=[distilled, *(d for d in decisions if d.exists())],
        model="opus",
        max_output_tokens=2500,
        timeout_s=600,
        extra_context={},
    )

    kill_inv = WorkerInvocation(
        role_path=profile.source_dir.parent / "process_roles" / "kill-case-skeptic.md",
        workspace_path=state.workspace_path,
        output_path=state.workspace_path / "kill-case.md",
        allowed_read_paths=[
            state.workspace_path / "cross-critique.md",
            state.workspace_path / "assumptions.yaml",
            *(d for d in decisions if d.exists()),
        ],
        model="opus",
        max_output_tokens=2500,
        timeout_s=600,
        extra_context={},
    )

    return [cross_inv, kill_inv]


def _synthesize_workers_fn(state: RunState, profile: Profile) -> list[WorkerInvocation]:
    assumptions_path = state.workspace_path / "assumptions.yaml"
    # >50% load-bearing unconfirmed → synthesizer flags insufficient_info
    verdict_constraint = "free_choice"
    if assumptions_path.exists():
        try:
            data: Any = yaml.safe_load(assumptions_path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                items: list[Any] = cast("list[Any]", data)
                rows: list[dict[str, Any]] = [
                    a for a in items
                    if isinstance(a, dict)
                    and cast("dict[str, Any]", a).get(
                        "would_change_verdict_if_false"
                    ) in ("yes", "maybe")
                ]
                if rows:
                    unconfirmed = [a for a in rows if not a.get("confirmed")]
                    if len(unconfirmed) / len(rows) > 0.5:
                        verdict_constraint = "insufficient_info"
        except Exception:
            pass

    decisions = [state.workspace_path / s / "decision.md" for s in profile.specialists]
    return [WorkerInvocation(
        role_path=profile.source_dir.parent / "process_roles" / "synthesizer.md",
        workspace_path=state.workspace_path,
        output_path=state.workspace_path / "deliverables" / "executive-summary.md",
        allowed_read_paths=[
            state.workspace_path / "idea.md",
            state.workspace_path / "assumptions.yaml",
            state.workspace_path / "disagreements.md",
            state.workspace_path / "frame-shifter" / "draft-1.md",
            state.workspace_path / "meta" / "distilled" / "post-explore.md",
            state.workspace_path / "cross-critique.md",
            state.workspace_path / "kill-case.md",
            *(d for d in decisions if d.exists()),
        ],
        model="opus",
        max_output_tokens=8000,
        timeout_s=1200,
        extra_context={"verdict_constraint": verdict_constraint},
    )]


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
    PhaseSpec(id="0.6", name="Reframe", workers_fn=_reframe_workers_fn, parallel=False),
    PhaseSpec(id="1", name="Discover", workers_fn=_discover_workers_fn, parallel=True),
    PhaseSpec(
        id="1.5",
        name="Disagreement",
        workers_fn=_disagreement_workers_fn,
        parallel=False,
    ),
    PhaseSpec(
        id="2.1",
        name="Explore",
        workers_fn=_explore_generate_workers_fn,
        parallel=True,
        gate_fn=_explore_gate_fn,
        setup_fn=_explore_prepare,
    ),
    PhaseSpec(
        id="2.2",
        name="Explore",
        workers_fn=_explore_critique_workers_fn,
        parallel=True,
        gate_fn=_explore_gate_fn,
    ),
    PhaseSpec(
        id="2.3",
        name="Explore",
        workers_fn=_explore_prune_workers_fn,
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
