---
name: designer
description: Stub designer role for e2e testing
model: sonnet
worker: cli
phase: discover
output_cap: 2000
timeout_s: 600
branchable: conditional
output_schema:
  required_frontmatter:
    primary_flow_steps: list
    core_interaction_pattern: str
    failure_states: list
  required_sections:
    - Frame engagement
    - Primary user flow
    - Interaction patterns
    - Failure states
  exit_criteria:
    Primary user flow:
      min_words: 50
    Interaction patterns:
      min_words: 50
tools: []
---

Stub designer system prompt.
