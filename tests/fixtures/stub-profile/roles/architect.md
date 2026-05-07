---
name: architect
description: Stub architect role for e2e testing
model: sonnet
worker: cli
phase: discover
output_cap: 2000
timeout_s: 600
branchable: yes
output_schema:
  required_frontmatter:
    data_entities: list
    external_dependencies: list
    state_locus: str
  required_sections:
    - Frame engagement
    - Architecture overview
    - Build complexity
    - Tractability
  exit_criteria:
    Architecture overview:
      min_words: 50
    Build complexity:
      min_words: 30
tools: []
---

Stub architect system prompt.
