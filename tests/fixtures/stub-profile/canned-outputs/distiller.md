---
distilled_at_phase: "post-explore"
---

## Idea

A local CLI tool (`lem`) that runs a multi-agent pipeline over a markdown workspace to evaluate an app or feature idea and produce investor-grade deliverables ending in an explicit verdict (Build / Don't build / Refine / Pivot / Insufficient information). Named after Stanisław Lem.

## Decisions

All three specialists accepted the original frame: local CLI, developer-entrepreneur target user, batch evaluation model. No branching occurred; explore phase was skipped due to no substantive disagreements. The architect chose filesystem-based state with no database. The designer chose CLI-first interaction with an optional TUI watch mode. The market analyst positioned the tool against informal LLM conversations (sycophantic) and structured frameworks (manual). The genuine differentiator is the opinionated pipeline with an explicit verdict. No specialist shifted the frame. The synthesizer has a clean, aligned workspace to work from.

## Open questions

1. Is the cost-per-run acceptable to the target user? ($10–15 per run estimated.)
2. Does the target user trust an automated verdict, or does it function primarily as a structured thinking aid?
3. What is the right default for max_cost and max_wall_clock?

## Assumptions in play

- Users have a Claude Max subscription or API key. (Unconfirmed: may limit adoption.)
- The `claude` CLI binary is installed and authenticated. (Unconfirmed: installation friction unknown.)
- Target users are developer-entrepreneurs comfortable with terminal tools. (Confirmed by framing.)
