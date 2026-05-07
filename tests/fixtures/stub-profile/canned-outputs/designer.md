---
primary_flow_steps:
  - "User runs: lem refine 'my idea'"
  - "Terminal prompts up to 3 clarifying questions"
  - "User answers inline; lem writes idea.md"
  - "Pipeline runs in background; user gets run ID"
  - "User runs: lem watch <run-id> to follow progress"
  - "User runs: lem show <run-id> to read the executive summary"
core_interaction_pattern: "CLI-first, background execution, pull-based status"
failure_states:
  - "claude CLI not found: lem prints installation instructions and exits 1"
  - "API auth failure: lem prints auth instructions, exits 69"
  - "Cost ceiling hit: lem writes partial deliverables, marks run cost-aborted"
  - "Schema validation failure after retry: run continues, error noted in logs"
---

## Frame engagement

The original frame is a CLI tool. Alternatives considered:

1. TUI with inline editing — rejected: the JTBD is batch evaluation, not interactive authoring.
2. Web UI — rejected: adds deployment friction; the user is a developer comfortable with terminals.
3. Voice input — rejected: out of scope for v1.

Keeping original frame: terminal-first CLI with optional TUI watch mode.

## Primary user flow

The primary user flow starts with a single command: `lem refine "my idea"`. The terminal immediately prompts clarifying questions — at most three, printed one at a time. Each question has a default answer shown in brackets; pressing Enter accepts the default. After the intake, lem writes `idea.md` and `assumptions.yaml` to the workspace, prints a run ID, and exits. The pipeline runs in the background. The user can type `lem watch <run-id>` at any time to open a live TUI showing phase progress, worker statuses, and a running cost counter. When synthesis completes, lem prints a one-line summary and the path to the executive summary.

## Interaction patterns

The intake interaction pattern is conversational but constrained: questions appear sequentially, not as a form. The default-answer pattern reduces friction for users who want to accept the defaults and let the pipeline run. The watch TUI uses a split-pane layout: phases on the left, worker detail on the right, cost and elapsed time in the footer. Log lines scroll in real time. The user can press `p` to pause, `r` to resume, `c` to cancel. The `lem show` command pipes the executive summary through `$PAGER` with markdown rendering if `glow` is installed.

## Failure states

The system has several failure modes handled gracefully. If the claude binary is missing, the error message includes installation instructions. Auth failures produce a clear message with the `claude auth` command. Cost ceiling breaches produce partial but complete deliverables for the phases that ran, with a banner explaining the abort. Schema validation failures are surfaced in the TUI as warnings, not crashes — the pipeline continues with the best available output.
