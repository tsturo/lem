# pyright: strict
"""Tests for src/lem/render/deliverables.py."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from lem.render.deliverables import (
    REQUIRED_SYNTHESIS_KEYS_BY_DELIVERABLE,
    render_deliverables,
    required_keys_for_deliverables,
    validate_synthesis_frontmatter,
)
from lem.types import Profile, Role


def _make_profile(
    *,
    source_dir: Path,
    default: list[str],
    flag_gated: dict[str, str],
) -> Profile:
    role = Role(
        name="stub", description="", model="haiku", worker="cli",
        phase=None, output_cap=1024, timeout_s=30, branchable="no",
        output_schema={}, tools=[], system_prompt="", source_path=source_dir,
    )
    return Profile(
        name="stub", description="", specialists=[], verdict_options=[],
        default_deliverables=default, flag_gated_deliverables=flag_gated,
        roles={"stub": role}, process_roles={}, intake_prompt="",
        source_dir=source_dir,
    )


def _write_synthesis(workspace: Path, frontmatter: dict[str, object]) -> None:
    out = workspace / "meta" / "synthesis.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    fm_yaml = yaml.safe_dump(frontmatter, sort_keys=False)
    out.write_text(f"---\n{fm_yaml}---\n\n## Verdict\n\nbody.\n", encoding="utf-8")


def _write_template(profile_dir: Path, name: str, content: str) -> None:
    deliverables = profile_dir / "deliverables"
    deliverables.mkdir(parents=True, exist_ok=True)
    (deliverables / f"{name}.md.j2").write_text(content, encoding="utf-8")


def test_render_default_deliverables(tmp_path: Path) -> None:
    profile_dir = tmp_path / "profile"
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write_template(profile_dir, "executive-summary", "Hello {{ idea_one_liner }}\n")
    profile = _make_profile(
        source_dir=profile_dir, default=["executive-summary"], flag_gated={}
    )
    _write_synthesis(workspace, {"idea_one_liner": "world"})
    written = render_deliverables(workspace, profile)
    assert len(written) == 1
    out = workspace / "deliverables" / "executive-summary.md"
    assert out.exists()
    assert out.read_text(encoding="utf-8") == "Hello world\n"


def test_render_skips_missing_template(tmp_path: Path) -> None:
    profile_dir = tmp_path / "profile"
    workspace = tmp_path / "ws"
    workspace.mkdir()
    profile = _make_profile(
        source_dir=profile_dir,
        default=["executive-summary", "no-such-template"],
        flag_gated={},
    )
    _write_template(profile_dir, "executive-summary", "x={{ idea_one_liner }}\n")
    _write_synthesis(workspace, {"idea_one_liner": "y"})
    written = render_deliverables(workspace, profile)
    assert len(written) == 1


def test_render_flag_gated_only_when_requested(tmp_path: Path) -> None:
    profile_dir = tmp_path / "profile"
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write_template(profile_dir, "executive-summary", "es\n")
    _write_template(profile_dir, "investor-onepager", "pitch={{ ask }}\n")
    profile = _make_profile(
        source_dir=profile_dir,
        default=["executive-summary"],
        flag_gated={"--with-pitch": "investor-onepager"},
    )
    _write_synthesis(workspace, {"ask": "$500k", "idea_one_liner": "x"})

    written = render_deliverables(workspace, profile)
    assert len(written) == 1  # default only

    written_with_flag = render_deliverables(
        workspace, profile, requested_flags={"--with-pitch"}
    )
    assert len(written_with_flag) == 2
    pitch = workspace / "deliverables" / "investor-onepager.md"
    assert pitch.exists()
    assert "$500k" in pitch.read_text(encoding="utf-8")


def test_undefined_keys_render_as_empty(tmp_path: Path) -> None:
    """ChainableUndefined: a missing-but-known key renders as empty string,
    not raise — so a partial synthesis still produces *something*."""
    profile_dir = tmp_path / "profile"
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write_template(profile_dir, "executive-summary", "before-{{ missing }}-after\n")
    profile = _make_profile(
        source_dir=profile_dir, default=["executive-summary"], flag_gated={}
    )
    # Non-empty frontmatter (real synthesizer output), but the template uses
    # a key the synthesizer didn't include. Should render as empty, not crash.
    _write_synthesis(workspace, {"recommendation": "Build"})
    written = render_deliverables(workspace, profile)
    assert len(written) == 1
    text = written[0].read_text(encoding="utf-8")
    assert "before--after" in text


def test_render_raises_on_empty_synthesis_frontmatter(tmp_path: Path) -> None:
    """Regression for 2026-05-08 silent-empty-deliverables bug:
    if synthesis frontmatter is empty (= parse failure surrogate), render
    must raise SynthesisIntegrityError, not produce blank deliverables."""
    from lem.render.deliverables import SynthesisIntegrityError
    profile_dir = tmp_path / "profile"
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write_template(profile_dir, "executive-summary", "x")
    profile = _make_profile(
        source_dir=profile_dir, default=["executive-summary"], flag_gated={}
    )
    _write_synthesis(workspace, {})
    with pytest.raises(SynthesisIntegrityError, match="empty frontmatter"):
        render_deliverables(workspace, profile)


def test_render_raises_on_unparseable_synthesis(tmp_path: Path) -> None:
    """Regression: synthesizer output with opening `---` but no closing fence
    must surface as SynthesisIntegrityError, not silently render empty."""
    from lem.render.deliverables import SynthesisIntegrityError
    profile_dir = tmp_path / "profile"
    workspace = tmp_path / "ws"
    workspace.mkdir()
    (workspace / "meta").mkdir()
    (workspace / "meta" / "synthesis.md").write_text(
        "---\nrecommendation: Build\n\n## Verdict\nbody\n", encoding="utf-8"
    )
    _write_template(profile_dir, "executive-summary", "x")
    profile = _make_profile(
        source_dir=profile_dir, default=["executive-summary"], flag_gated={}
    )
    with pytest.raises(SynthesisIntegrityError, match="malformed"):
        render_deliverables(workspace, profile)


def test_validate_synthesis_frontmatter_missing_keys(tmp_path: Path) -> None:
    errors = validate_synthesis_frontmatter({}, ["executive-summary"])
    assert errors  # non-empty
    expected_keys = REQUIRED_SYNTHESIS_KEYS_BY_DELIVERABLE["executive-summary"]
    for k in expected_keys:
        assert any(k in e for e in errors), f"missing error for {k}"


def test_validate_synthesis_frontmatter_complete(tmp_path: Path) -> None:
    needed = required_keys_for_deliverables(["executive-summary"])
    fm: dict[str, object] = dict.fromkeys(needed, "x")
    errors = validate_synthesis_frontmatter(fm, ["executive-summary"])
    assert errors == []


def test_render_no_deliverables_dir_returns_empty(tmp_path: Path) -> None:
    profile_dir = tmp_path / "profile"
    profile_dir.mkdir()
    workspace = tmp_path / "ws"
    workspace.mkdir()
    profile = _make_profile(
        source_dir=profile_dir, default=["executive-summary"], flag_gated={}
    )
    _write_synthesis(workspace, {"idea_one_liner": "x"})
    written = render_deliverables(workspace, profile)
    assert written == []


def test_render_app_idea_real_templates(tmp_path: Path) -> None:
    """Render against the real app-idea profile templates with full frontmatter."""
    workspace = tmp_path / "ws"
    workspace.mkdir()

    # Build complete frontmatter covering all default deliverables for app-idea.
    fm: dict[str, object] = {
        "idea_one_liner": "PDF-native notes for academic researchers.",
        "assumptions_confirmed": [{"description": "users have internet"}],
        "assumptions_unconfirmed": [
            {"description": "users will pay $12/mo", "would_change_verdict_if_false": "yes"}
        ],
        "summary_body": "The idea has a clear differentiator.",
        "recommendation": "Build",
        "confidence": "medium",
        "confidence_rationale": "real gap, light validation",
        "open_questions": ["will users pay $12/mo?"],
        "market": {
            "saturation": "medium",
            "direct_competitors": ["Notion", "Obsidian"],
            "closest_analogue": "Notion",
            "genuine_differentiator": "PDF-native annotation",
        },
        "strongest_build": "real gap.",
        "strongest_abandon": "Notion may add PDFs.",
        "falsifiable_signals": ["5 paying customers in 60d"],
        "target_user": "PhD students",
        "jtbd": "annotate while reading",
        "why_now": "PDF tooling stagnated",
        "mvp_in_scope": ["upload PDF", "inline annotation"],
        "mvp_out_of_scope": ["mobile app"],
        "architecture_sketch": "Next.js + Postgres + S3.",
        "data_entities": ["User", "Paper"],
        "external_dependencies": ["Stripe", "S3"],
        "state_locus": "server-side Postgres",
        "core_interaction_pattern": "split-pane",
        "primary_flow_steps": ["upload", "annotate"],
        "phase_1": {"name": "MVP", "goal": "validate", "effort": "4w", "deliverable": "beta"},
        "phase_2": {"name": "search", "goal": "differentiate", "effort": "3w", "deliverable": "search"},
        "phase_3": {"name": "billing", "goal": "convert", "effort": "2w", "deliverable": "Stripe"},
        "top_risks": [
            {"title": "Notion adds PDFs", "severity": "high", "likelihood": "medium",
             "trigger": "Notion roadmap", "description": "...", "mitigation": "lead with academic features"}
        ],
        "rejected_paths": [
            {"name": "extension", "description": "browser ext", "reason": "no cross-paper search",
             "upside": "lower friction"}
        ],
        "reframings": [
            {"shape": "Content", "description": "newsletter", "why_rejected": "user wants software",
             "shift_conditions": "if research finds learning is the job"}
        ],
    }
    _write_synthesis(workspace, fm)

    profile_dir = (
        Path(__file__).parent.parent.parent / "profiles" / "app-idea"
    )
    profile = _make_profile(
        source_dir=profile_dir,
        default=["executive-summary", "mvp-plan", "risks-and-rejected-paths"],
        flag_gated={},
    )
    written = render_deliverables(workspace, profile)
    assert len(written) == 3
    for p in written:
        assert p.exists()
        content = p.read_text(encoding="utf-8")
        assert "{{" not in content  # no unfilled jinja vars
