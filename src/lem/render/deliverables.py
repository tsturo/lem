# pyright: strict
"""Render synthesis frontmatter into deliverable .md files via Jinja2 templates.

Contract:
    The synthesizer writes meta/synthesis.md whose YAML frontmatter is a flat
    dict of all template variables (the union of fields across every template
    referenced by profile.default_deliverables and profile.flag_gated_deliverables).

    render_deliverables() reads that frontmatter, iterates the requested
    deliverables, and renders each .md.j2 template into deliverables/<name>.md.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import (
    ChainableUndefined,
    Environment,
    FileSystemLoader,
    TemplateNotFound,
)

from lem.schema.parser import parse_file
from lem.types import Profile

REQUIRED_SYNTHESIS_KEYS_BY_DELIVERABLE: dict[str, list[str]] = {
    "executive-summary": [
        "idea_one_liner",
        "assumptions_confirmed",
        "assumptions_unconfirmed",
        "summary_body",
        "recommendation",
        "confidence",
        "confidence_rationale",
        "market",
        "strongest_build",
        "strongest_abandon",
        "falsifiable_signals",
    ],
    "mvp-plan": [
        "target_user",
        "jtbd",
        "mvp_in_scope",
        "mvp_out_of_scope",
        "architecture_sketch",
        "primary_flow_steps",
        "phase_1",
        "phase_2",
        "phase_3",
    ],
    "risks-and-rejected-paths": [
        "top_risks",
        "rejected_paths",
        "reframings",
    ],
    "investor-onepager": [
        "product_name",
        "idea_one_liner",
        "target_user",
        "problem_statement",
        "solution_statement",
        "why_now",
        "market",
        "team_needs",
        "ask",
    ],
    "roadmap": ["now", "next", "later", "not_on_roadmap", "decision_points"],
    "tech-stack": [
        "frontend",
        "backend",
        "database",
        "hosting",
        "state_locus",
        "data_entities",
        "auth",
        "external_dependencies",
        "rationale",
        "rejected_alternatives",
        "mvp_user_estimate",
        "cost_estimate",
        "stack_risks",
    ],
}


def synthesis_path(workspace_path: Path) -> Path:
    return workspace_path / "meta" / "synthesis.md"


class SynthesisIntegrityError(Exception):
    """Synthesis output is missing or unparseable — deliverables cannot render."""


def load_synthesis_frontmatter(workspace_path: Path) -> dict[str, Any]:
    path = synthesis_path(workspace_path)
    if not path.exists():
        return {}
    try:
        doc = parse_file(path)
    except Exception:
        return {}
    return dict(doc.frontmatter)


def _assert_synthesis_loadable(workspace_path: Path) -> None:
    """Raise SynthesisIntegrityError with a useful message if synthesis is broken.

    A silent empty-frontmatter outcome causes deliverables to render as empty
    Jinja templates and the run to claim 'completed' — actively misleading.
    Surface the failure so the orchestrator can mark the run as failed instead.
    """
    path = synthesis_path(workspace_path)
    if not path.exists():
        raise SynthesisIntegrityError(
            f"synthesizer produced no output at {path}"
        )
    try:
        doc = parse_file(path)
    except Exception as exc:
        raise SynthesisIntegrityError(
            f"synthesis.md is malformed and cannot be parsed: {exc}. "
            f"This usually means the synthesizer forgot to close the "
            f"frontmatter with a `---` fence before the body."
        ) from exc
    if not doc.frontmatter:
        raise SynthesisIntegrityError(
            f"synthesis.md parsed with empty frontmatter at {path}. "
            f"Render layer cannot produce any deliverable content."
        )


def required_keys_for_deliverables(deliverables: list[str]) -> set[str]:
    keys: set[str] = set()
    for d in deliverables:
        keys.update(REQUIRED_SYNTHESIS_KEYS_BY_DELIVERABLE.get(d, []))
    return keys


def validate_synthesis_frontmatter(
    frontmatter: dict[str, Any], deliverables: list[str]
) -> list[str]:
    """Return a list of missing-key error strings; empty list = valid."""
    needed = required_keys_for_deliverables(deliverables)
    missing = [k for k in sorted(needed) if k not in frontmatter]
    return [f"missing required synthesis key '{k}'" for k in missing]


def _render_one(
    env: Environment,
    template_name: str,
    *,
    context: dict[str, Any],
    output_path: Path,
) -> None:
    template = env.get_template(template_name)
    rendered = template.render(**context)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered, encoding="utf-8")


def _flag_gated_requested(
    flag_gated: dict[str, str], requested_flags: set[str]
) -> list[str]:
    """Return deliverable names whose flag is in requested_flags."""
    return [name for flag, name in flag_gated.items() if flag in requested_flags]


def render_deliverables(
    workspace_path: Path,
    profile: Profile,
    *,
    requested_flags: set[str] | None = None,
) -> list[Path]:
    """Render all default + requested-flag-gated deliverables.

    Returns the list of written file paths. Skips templates that are not
    present in the profile's deliverables directory.
    """
    if requested_flags is None:
        requested_flags = set()

    _assert_synthesis_loadable(workspace_path)
    context = load_synthesis_frontmatter(workspace_path)
    deliverable_names = list(profile.default_deliverables) + _flag_gated_requested(
        profile.flag_gated_deliverables, requested_flags
    )

    deliverables_dir = profile.source_dir / "deliverables"
    if not deliverables_dir.exists():
        return []

    env = Environment(
        loader=FileSystemLoader(str(deliverables_dir)),
        undefined=ChainableUndefined,
        autoescape=False,
        keep_trailing_newline=True,
    )

    out_dir = workspace_path / "deliverables"
    written: list[Path] = []
    for name in deliverable_names:
        template_name = f"{name}.md.j2"
        try:
            output_path = out_dir / f"{name}.md"
            _render_one(
                env, template_name, context=context, output_path=output_path
            )
            written.append(output_path)
        except TemplateNotFound:
            continue
    return written
