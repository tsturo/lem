---
name: market
description: Stub market role for e2e testing
model: sonnet
worker: cli
phase: discover
output_cap: 2500
timeout_s: 900
branchable: yes
output_schema:
  required_frontmatter:
    saturation: enum
    direct_competitors: list
    closest_analogue: str
    genuine_differentiator: str
    business_model: str
    customer_development_signal: str
    target_user_acuteness: str
  required_sections:
    - Frame engagement
    - Market context
    - Competitors
    - Differentiator
    - Customer development
  enums:
    saturation: [low, medium, high, very-high]
  exit_criteria:
    Competitors:
      min_bullets: 3
    Differentiator:
      min_words: 30
tools: []
---

Stub market system prompt.
