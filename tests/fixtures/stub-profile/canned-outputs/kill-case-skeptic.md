---
assumptions_leveraged:
  - "users have Claude Max subscription or API key"
  - "claude CLI binary is installed and authenticated"
kill_strength: moderate
conflicts_leveraged: []
---

## The kill case

The strongest case for not building lem rests on a distribution problem, not a technical problem. The tool requires three preconditions to run: Python 3.11+, the claude CLI installed and authenticated, and a Claude Max subscription or API key. Each precondition eliminates a fraction of the target user. The intersection of "has Python," "has claude CLI authenticated," and "has Claude Max" is smaller than the intersection of "has a startup idea" and "would benefit from structured analysis." The tool solves a real problem for a narrower audience than the problem statement implies.

Additionally, the $10–15 per-run cost is not negligible for someone who is still evaluating whether to build something. The user might run the tool once, get a "Refine before building" verdict, and never return — because the follow-on action (refine and re-run) costs another $15. The tool optimizes for the one-time evaluation case, not the iteration case, which may limit its value as a decision-making aid.

Finally, informal LLM conversations are fast and free. The target user has already developed a workflow of chatting with Claude or GPT about their ideas. Displacing that workflow requires lem to produce meaningfully better output, consistently. Prompt engineering quality is the single highest-risk assumption in this build — if the pipeline produces generic, hedged output, users will revert to informal conversations within two runs.

## What this depends on

This kill case depends primarily on the distribution constraint (Claude Max penetration among the target user), the per-run cost tolerance, and the quality of the pipeline output. If lem can be run with a free API tier at acceptable cost, the first objection dissolves. If the output is consistently sharper than informal LLM conversations, the third objection dissolves.

## What would refute this

Evidence that would refute this kill case: (1) a user survey showing >50% of developer-entrepreneurs already have Claude Max; (2) a cost reduction to under $3 per run through Haiku-heavy routing; (3) a head-to-head evaluation showing lem verdicts are more accurate than informal LLM conversations on a held-out set of ideas.
