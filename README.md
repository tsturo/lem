# lem

A multi-agent CLI framework that refines a one-line app or feature idea into investor-grade markdown deliverables, ending in an explicit verdict.

Named after Stanisław Lem.

**Status: design phase complete, implementation not yet started.**

## What's in this repo

- [Design spec](docs/superpowers/specs/2026-05-06-lem-framework-design.md) — architecture, roles, pipeline, verdict format, failure semantics
- [Implementation plan](docs/superpowers/plans/2026-05-06-lem-framework.md) — 41 tasks across 11 phases, code-free, designed for subagent-driven execution
- [Agent prompt](docs/superpowers/agent-prompt.md) — drop into a fresh Claude session to start implementation

## High-level design

A small Python orchestrator spawns headless `claude -p` workers running specialist roles (architect, designer, market researcher, frame-shifter, multiple distinct skeptics) over a shared markdown workspace. Pipeline phases: Intake → JTBD → Discover → Disagreement check → Reframe → Explore (opt-in branching) → Distill → Cross-Critique → Synthesize. Output: 3 markdown deliverables ending in a steel-manned verdict.

Workspace is Obsidian-friendly (markdown + frontmatter + wikilinks + `.obsidian/` config shipped). CLI is background-default with a `textual`-based TUI for live monitoring. Auth piggybacks on Claude Max subscription via the `claude` CLI — no API key required.

The design goal is "find the best, not the first": opt-in branching at decision points where genuine alternatives exist, contrastive reframing post-commitment, schema-validated structured outputs, and an assumptions register that surfaces what the user confirmed vs. what the system inferred.

## Implementation

See the [agent prompt](docs/superpowers/agent-prompt.md) for the self-contained briefing to start a subagent-driven implementation session.
