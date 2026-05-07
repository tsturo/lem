---
data_entities:
  - "User: authenticated person with an idea"
  - "Idea: the one-liner submitted for analysis"
  - "Run: a pipeline execution tied to an Idea"
  - "Deliverable: a markdown output file produced by a Run"
external_dependencies:
  - "claude CLI for worker invocation"
  - "Python 3.11 standard library"
state_locus: "server-side filesystem (local or remote)"
---

## Frame engagement

The original frame treats this as a simple CLI tool. Three alternatives considered:

1. Web service with persistent runs — rejected: adds deployment complexity without value for solo use.
2. Library rather than CLI — rejected: the target user wants a command, not an import.
3. Notebook/interactive environment — rejected: the JTBD is batch evaluation, not exploration.

Keeping original frame: local CLI with filesystem workspace.

## Architecture overview

The system is a Python 3.11 CLI using `subprocess` to invoke headless `claude -p` workers. Each worker writes to a markdown workspace directory on the local filesystem. The orchestrator coordinates phases sequentially, with parallel dispatch within phases using `asyncio`. State is persisted as JSON to `meta/state.json`. Cost events are appended to `meta/cost.jsonl`. The pipeline has nine phases driven by a declarative `PHASES` list. No database required; all state is in the filesystem workspace. The runtime is a simple `pip install` with no external services beyond the claude CLI.

## Build complexity

A two-person team could ship the core path in three weeks. The complexity hotspots are: (1) reliable subprocess management with timeout escalation — more fiddly than it looks due to SIGTERM/SIGKILL sequencing; (2) schema validation with meaningful error messages for retry loops; (3) the TUI using Textual, which has a steep learning curve for reactive patterns. The branching logic in Explore phase is the most stateful component.

## Tractability

Fully tractable for a small team. No novel infrastructure required. The hardest part is prompt engineering for reliable schema-valid outputs, which is a tuning problem not an engineering problem. The subprocess model is intentionally simple to avoid SDK complexity.
