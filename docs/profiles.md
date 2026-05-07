# Profiles

A profile defines the specialists, verdict options, and deliverables for a pipeline run. Profiles are the main customization point.

## What a profile contains

```
profiles/
  app-idea/
    profile.yaml        — metadata, specialists list, deliverables
    intake-prompt.md    — clarifying questions shown during intake
    roles/
      architect.md      — specialist role definition + output schema
      designer.md
      market.md
    deliverables/       — deliverable templates (optional)
    prompt-fragments/   — injected snippets for process roles (optional)
```

## profile.yaml structure

```yaml
name: app-idea
description: Refines an app or feature idea into an investor-grade brief
specialists: [architect, designer, market]
verdict_options:
  - Build
  - Refine before building
  - Pivot the angle
  - Don't build
  - Insufficient information
default_deliverables:
  - executive-summary
  - mvp-plan
  - risks-and-rejected-paths
flag_gated_deliverables:
  --with-pitch: investor-onepager
  --with-roadmap: roadmap
  --with-techstack: tech-stack
```

`specialists` controls which domain experts run in the Discover phase and downstream phases. The names must match role files in `roles/`.

## Role file structure

Each role file is a markdown document with YAML frontmatter:

```markdown
---
name: architect
description: System shape, data model, and tractability for a small team
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
tools: []
---

You are the Architect for lem's app-idea pipeline...
```

The body below the frontmatter is the system prompt sent to claude.

### output_schema fields

| Field | Type | Description |
|---|---|---|
| `required_frontmatter` | dict or list | Frontmatter keys that must be present. Dict form allows type checking (`str`, `int`, `list`, `bool`, `enum`). |
| `required_sections` | list | H2 section names that must be present and non-empty. |
| `exit_criteria` | dict | Per-section quality gates. Supported: `min_words`, `min_bullets`. |
| `enums` | dict | Allowed values for `enum`-typed frontmatter keys. |

If a role's output fails schema validation, the dispatch layer retries once with the error list injected into the prompt.

## Writing a custom profile

1. Copy `profiles/app-idea/` to `profiles/<your-profile>/`.
2. Edit `profile.yaml`: update `name`, `description`, `specialists`, and `verdict_options`.
3. Edit or replace the role files in `roles/`. Each specialist name in `specialists` must have a matching `<name>.md`.
4. Update `intake-prompt.md` with questions relevant to your domain.
5. Run: `lem refine --profile <your-profile> "your idea"`.

The built-in process roles (jtbd-extractor, frame-shifter, synthesizer, etc.) are shared across all profiles. They live in `process_roles/` and can be overridden by placing a same-named file in your profile's roles directory — though this is rarely needed.
