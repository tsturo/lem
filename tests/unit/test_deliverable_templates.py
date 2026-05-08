"""Tests for deliverable Jinja2 templates (Task 7.4)."""

from pathlib import Path
from typing import Any

import pytest
from jinja2 import Environment, FileSystemLoader, StrictUndefined

DELIVERABLES_DIR = (
    Path(__file__).parent.parent.parent / "profiles" / "app-idea" / "deliverables"
)


@pytest.fixture
def env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(DELIVERABLES_DIR)),
        undefined=StrictUndefined,
        autoescape=False,
    )


@pytest.fixture
def market_ctx() -> dict[str, Any]:
    return {
        "saturation": "medium",
        "direct_competitors": ["Notion", "Obsidian", "Roam"],
        "closest_analogue": "Notion",
        "genuine_differentiator": "PDF-native annotation as the primary input",
        "business_model": "freemium SaaS, $12/mo individual",
        "customer_development_signal": "interviewed 8 target users",
        "target_user_acuteness": "high — daily blocker",
    }


@pytest.fixture
def exec_summary_ctx(market_ctx: dict[str, Any]) -> dict[str, Any]:
    return {
        "idea_one_liner": "A PDF-native note-taking tool for academic researchers.",
        "assumptions_confirmed": [
            {"description": "User interviews 8 PhD students weekly."},
        ],
        "assumptions_unconfirmed": [
            {
                "description": "Target users will pay $12/mo.",
                "would_change_verdict_if_false": "yes",
            }
        ],
        "summary_body": "The idea has a clear differentiator and a real audience.",
        "recommendation": "Build",
        "confidence": "medium",
        "confidence_rationale": "structural fit but customer development is light.",
        "open_questions": ["Will users pay $12/mo?"],
        "market": market_ctx,
        "strongest_build": "Differentiator is real and the team is in-segment.",
        "strongest_abandon": "Notion may add PDF-native annotation in 12 months.",
        "falsifiable_signals": [
            "5 paying customers within 60 days of MVP launch.",
        ],
    }


@pytest.fixture
def mvp_plan_ctx() -> dict[str, Any]:
    return {
        "target_user": "PhD students in STEM fields who read 5+ papers/week",
        "jtbd": "When I'm reviewing papers, I want to capture annotations inline.",
        "why_now": "PDF tooling has stagnated; AI summaries make annotation more useful.",
        "mvp_in_scope": ["PDF upload", "Inline annotation", "Cross-paper search"],
        "mvp_out_of_scope": ["Mobile app", "Real-time collaboration"],
        "architecture_sketch": "Next.js app + Postgres + S3 for PDFs.",
        "data_entities": ["User", "Paper", "Annotation"],
        "external_dependencies": ["Stripe Billing", "S3"],
        "state_locus": "server-side Postgres",
        "core_interaction_pattern": "split-pane PDF + sidebar annotations",
        "primary_flow_steps": [
            "User uploads PDF",
            "User highlights text to annotate",
            "User searches across papers",
        ],
        "phase_1": {
            "name": "Single-user MVP",
            "goal": "validate annotation flow",
            "effort": "4 weeks",
            "deliverable": "private beta with 5 users",
        },
        "phase_2": {
            "name": "Cross-paper search",
            "goal": "deliver the differentiator",
            "effort": "3 weeks",
            "deliverable": "search across uploaded library",
        },
        "phase_3": {
            "name": "Billing + public launch",
            "goal": "convert users to paying",
            "effort": "2 weeks",
            "deliverable": "Stripe billing + ProductHunt launch",
        },
        "open_questions": ["Should mobile be sooner?"],
    }


@pytest.fixture
def risks_ctx() -> dict[str, Any]:
    return {
        "top_risks": [
            {
                "title": "Notion adds PDF-native annotation",
                "severity": "high",
                "likelihood": "medium",
                "trigger": "Notion roadmap announcement",
                "description": "If Notion ships native PDFs, the differentiator collapses.",
                "mitigation": "Lead with academic-specific features Notion will not prioritize.",
            }
        ],
        "rejected_paths": [
            {
                "name": "Browser extension",
                "description": "Annotate PDFs in browser without standalone app.",
                "reason": "Cannot do cross-paper search in extension scope.",
                "upside": "Lower friction first-use.",
            }
        ],
        "reframings": [
            {
                "shape": "Content product",
                "description": "Newsletter teaching paper-reading techniques.",
                "why_rejected": "User wants software, not pedagogy.",
                "shift_conditions": "If user research finds the real job is learning, not annotating.",
            }
        ],
    }


@pytest.fixture
def investor_ctx(market_ctx: dict[str, Any]) -> dict[str, Any]:
    return {
        "product_name": "Marginalia",
        "idea_one_liner": "PDF-native notes for academic researchers.",
        "target_user": "PhD students in STEM",
        "problem_statement": "Existing note tools treat PDFs as second-class citizens.",
        "solution_statement": "Annotation-first workflow with cross-paper search.",
        "why_now": "PDF tooling has stagnated; AI summaries are the unlock.",
        "market": market_ctx,
        "team_needs": "1 senior FE eng, 1 designer, founder doing growth.",
        "ask": "$500k pre-seed for 12 months runway.",
    }


@pytest.fixture
def roadmap_ctx() -> dict[str, Any]:
    return {
        "now": {
            "timeframe": "weeks 1-4",
            "goal": "Validate annotation flow",
            "deliverable": "private beta",
            "items": ["upload PDF", "inline annotation"],
        },
        "next": {
            "timeframe": "weeks 5-8",
            "goal": "Ship differentiator",
            "deliverable": "cross-paper search",
            "items": ["embeddings index", "search UI"],
        },
        "later": {
            "timeframe": "weeks 9+",
            "goal": "Monetize",
            "items": ["billing", "team plan"],
        },
        "not_on_roadmap": ["mobile app for v1", "real-time collab"],
        "decision_points": [
            {
                "trigger": "10 paying customers",
                "what_to_reconsider": "whether to expand to humanities researchers",
            }
        ],
    }


@pytest.fixture
def tech_stack_ctx() -> dict[str, Any]:
    return {
        "frontend": "Next.js 15 + React",
        "backend": "Next.js API routes + tRPC",
        "database": "Postgres on Neon",
        "hosting": "Vercel",
        "state_locus": "server-side Postgres",
        "data_entities": ["User", "Paper", "Annotation"],
        "auth": "Clerk",
        "external_dependencies": [
            {
                "name": "Stripe Billing",
                "purpose": "subscriptions",
                "cost_anchor": "$0 + 2.9% of revenue",
            }
        ],
        "rationale": "Next.js gives the team velocity; Neon handles DB scaling.",
        "rejected_alternatives": [
            {"name": "Rails", "reason": "team has no Ruby experience"}
        ],
        "mvp_user_estimate": "500",
        "cost_estimate": "$80/month all-in",
        "stack_risks": ["Vercel function cold starts on PDF upload"],
    }


def test_executive_summary_renders(env: Environment, exec_summary_ctx: dict[str, Any]) -> None:
    template = env.get_template("executive-summary.md.j2")
    output = template.render(**exec_summary_ctx)
    assert "## Assumptions" in output
    assert "## Verdict" in output
    assert "Build" in output


def test_executive_summary_assumptions_before_verdict(
    env: Environment, exec_summary_ctx: dict[str, Any]
) -> None:
    template = env.get_template("executive-summary.md.j2")
    output = template.render(**exec_summary_ctx)
    assert output.index("## Assumptions") < output.index("## Verdict")


def test_executive_summary_omits_open_questions_when_not_insufficient(
    env: Environment, exec_summary_ctx: dict[str, Any]
) -> None:
    template = env.get_template("executive-summary.md.j2")
    output = template.render(**exec_summary_ctx)
    assert "Open questions to answer" not in output


def test_executive_summary_includes_open_questions_when_insufficient(
    env: Environment, exec_summary_ctx: dict[str, Any]
) -> None:
    exec_summary_ctx["recommendation"] = "Insufficient information"
    template = env.get_template("executive-summary.md.j2")
    output = template.render(**exec_summary_ctx)
    assert "Open questions to answer" in output


def test_mvp_plan_renders(env: Environment, mvp_plan_ctx: dict[str, Any]) -> None:
    template = env.get_template("mvp-plan.md.j2")
    output = template.render(**mvp_plan_ctx)
    for section in (
        "## Problem and user",
        "## MVP scope",
        "## Architecture sketch",
        "## UX flow",
        "## 3-phase build sequence",
        "## Open questions",
    ):
        assert section in output


def test_mvp_plan_includes_phase_names(
    env: Environment, mvp_plan_ctx: dict[str, Any]
) -> None:
    template = env.get_template("mvp-plan.md.j2")
    output = template.render(**mvp_plan_ctx)
    assert "Single-user MVP" in output
    assert "Cross-paper search" in output


def test_risks_renders(env: Environment, risks_ctx: dict[str, Any]) -> None:
    template = env.get_template("risks-and-rejected-paths.md.j2")
    output = template.render(**risks_ctx)
    for section in (
        "## Top 5 risks",
        "## Paths considered and rejected",
        "## Reframings considered",
    ):
        assert section in output


def test_risks_includes_top_risk_title(
    env: Environment, risks_ctx: dict[str, Any]
) -> None:
    template = env.get_template("risks-and-rejected-paths.md.j2")
    output = template.render(**risks_ctx)
    assert "Notion adds PDF-native annotation" in output


def test_investor_onepager_renders(
    env: Environment, investor_ctx: dict[str, Any]
) -> None:
    template = env.get_template("investor-onepager.md.j2")
    output = template.render(**investor_ctx)
    assert "Marginalia" in output
    assert "Target customer" in output
    assert "Ask" in output


def test_roadmap_renders(env: Environment, roadmap_ctx: dict[str, Any]) -> None:
    template = env.get_template("roadmap.md.j2")
    output = template.render(**roadmap_ctx)
    assert "## Now" in output
    assert "## Next" in output
    assert "## Later" in output
    assert "Decision points" in output


def test_tech_stack_renders(env: Environment, tech_stack_ctx: dict[str, Any]) -> None:
    template = env.get_template("tech-stack.md.j2")
    output = template.render(**tech_stack_ctx)
    assert "Next.js 15" in output
    assert "## External dependencies" in output
    assert "## Cost anchor" in output


def test_all_templates_present() -> None:
    expected = {
        "executive-summary.md.j2",
        "mvp-plan.md.j2",
        "risks-and-rejected-paths.md.j2",
        "investor-onepager.md.j2",
        "roadmap.md.j2",
        "tech-stack.md.j2",
    }
    actual = {p.name for p in DELIVERABLES_DIR.glob("*.j2")}
    assert expected <= actual
