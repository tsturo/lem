---
description: Refine an idea into investor-grade markdown deliverables via lem
allowed-tools: ["Bash", "Read", "Write", "Edit"]
---

# /lem-refine "<one-liner>"

You are the intake-side agent for `lem`. The user has invoked `/lem-refine "<one-liner>"`. Do the following:

1. **Intake conversation**: ask the user up to 3 clarifying questions about audience, goal, mechanism, geography, and success metric. Ask only the genuinely missing items from the one-liner.
2. **Synthesize**: write `idea.md` (clarified brief) and `assumptions.yaml` (each load-bearing assumption flagged confirmed/unconfirmed with `would_change_verdict_if_false: yes|no|maybe`) to a fresh workspace at `$XDG_DATA_HOME/lem/runs/<YYYY-MM-DD-HHMM>-<slug>-<6hex>/`.
3. **Hand off**: shell `lem refine "<one-liner>" --skip-intake --workspace=<workspace_path>` to start the orchestrator.
4. **Report**: print the run-id and the workspace path to the user.

Use the Bash tool to invoke `lem`. The `lem` CLI is on the user's PATH after `pipx install lem`.
