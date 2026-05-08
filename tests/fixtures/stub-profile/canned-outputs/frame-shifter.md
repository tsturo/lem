---
alternative_shapes:
  - "managed service (hosted API, no local install)"
  - "library rather than CLI (import lem; run())"
  - "notebook plugin (Jupyter / Marimo integration)"
heretical_takes:
  - "the verdict format is the product; the pipeline is just the means to get there"
  - "users don't want to be told Don't build — they want permission to build; design for that tension"
---

## Original frame

A local CLI tool that runs a multi-agent pipeline to evaluate an app idea and produce markdown deliverables. The user installs it locally, provides their Claude credentials, and runs it on their machine.

## Alternative shapes

- **Managed service**: deploy the orchestrator as an API; user submits an idea, gets a webhook when done. Eliminates the local install requirement and makes the tool accessible to non-developers. Rejected for v1: adds significant operational complexity and billing surface.
- **Library rather than CLI**: expose `lem` as a Python library so developers can integrate it into notebooks, CI, or custom tooling. Simpler distribution story. Rejected for v1: the primary user is not building automation; they want a turnkey tool.
- **Notebook plugin**: run lem inside a Jupyter or Marimo notebook, with inline rendering. Better for exploration and customization. Rejected for v1: the JTBD is one-shot evaluation, not iterative exploration.

## Heretical takes

- The verdict format is the product. Users will remember "Build" or "Don't build" — they will not remember the supporting analysis. Everything else is scaffolding for the verdict's credibility.
- Users resist "Don't build" verdicts even when correct. The tool should make the kill case explicit and well-argued, not buried. A weak kill case produces a false "Build" verdict.
