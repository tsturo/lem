# Three-reviewer audit — synthesis

Date: 2026-05-07
Reviewers (parallel, independent): prompt engineer, multi-agent architect, AI production engineer.
Subject: lem v1 (post-43-task-implementation, pre-release).

## TL;DR

The prompts are mostly fine; the wiring between them was not. Three reviewers converged on three categories of issue: orchestration bugs that fail real runs, spec promises that the implementation never honored, and production-safety items needed before publishing.

## Resolution status

### ✅ Resolved (Round 1+2 fix commits, see `git log --grep '^fix'`)

| Finding | Reviewer(s) | Fix commit |
|---|---|---|
| Phase 2 race condition (generators/skeptics/pruner in one asyncio.gather) | architect | `a1aa5bb` |
| Reframe runs after Discover instead of before | prompt + architect | `9a566e2` |
| `draft-1.md → decision.md` rename hidden inside `_explore_workers_fn` | architect | `00ca58e` |
| Distiller's `allowed_read_paths` missing `idea.md` / `assumptions.yaml` / `frame-shifter/draft-1.md` | architect | `0bd1ba7` |
| Verdict auto-downgrade unenforced (synthesizer prompt was decorative) | all three | `ac0b639` |
| Pruner does not write `_archive/<loser>.md` rejection frontmatter | prompt + architect | `07ada68` |
| Synthesizer ↔ deliverable template contract broken (templates were dead code) | prompt + architect | `bc9005e` |
| Dollar cost ceiling — irrelevant for Max users | (user decision) | `1438a19` |

### 🟠 Pending (Round 3 — production safety)

These are the AI production engineer's "must fix before declaring v1 production ready" items. Bounded scope each; no attempted fix in this session.

1. **Prompt-injection fencing**. User one-liner is concatenated verbatim with a soft fence. Random-delimiter fences + content-directive stripping. See `ai-production.md` C1.
2. **Citation grounding verifier**. Schema validates shape, not truthfulness. Synthesizer can cite `C7` when only `C1`–`C3` exist. Add post-synthesis regex verifier for IDs and quoted strings. See `ai-production.md` C2.
3. **Persist rendered prompts + raw outputs**. `meta/prompts/<phase>-<role>-<attempt>.json` + `meta/raw/<phase>-<role>-<attempt>.txt`. Without this, prompt-regression debugging is impossible. See `ai-production.md` C5.
4. **Reference eval set + LLM-as-judge regression test**. 20-idea reference dataset + Sonnet judge with 4-criterion rubric. Run on every PR touching role prompts. See `ai-production.md` recommendations §1-§4. Estimated 2 days work; eval data needs author judgment.

### 🟡 Smaller backlog (deferred, not blocking v1)

- Devil's-advocate fallback when <2 disagreements found (spec promised, never implemented). See `prompt-engineer.md` cross-cutting #4.
- Discover-phase `skeptic.md` referenced in spec table but the role file does not exist. Either add the file or update the spec. See `prompt-engineer.md` cross-cutting #4.
- `customer_development_signal` and `target_user_acuteness` should be enums in `market.md` frontmatter. See `prompt-engineer.md` market.md findings.
- `saturation` enum is uncalibrated (`very-high` not gated on competitor count). See `ai-production.md` I3.
- `confidence` field is asserted, not computed. See `ai-production.md` I4.
- No regulated-domain / illegal-activity classifier. See `ai-production.md` I5.
- `--depth=deep` K=3 not implemented (currently always K=2). See `architect.md` branching logic.
- Webhook payload missing `recommendation`, `confidence`, `kill_strength`, etc. See `ai-production.md` I8.
- Per-attempt cost tracking absent. See `ai-production.md` I7.
- `parse_retry_after` exists but is dead code in CLI mode (acknowledged in retry.py). See `ai-production.md` M4.
- Maybe-load-bearing assumptions silently treated as not-load-bearing for verdict downgrade. See `ai-production.md` M5.

### Convergent confidence

These findings appeared in ≥2 reviews and have high evidence:

- Reframe ordering inversion (prompt + architect agreed; high confidence; resolved)
- Pruner archive missing (prompt + architect agreed; resolved)
- Verdict auto-downgrade decorative not enforced (all three agreed; resolved)
- Synthesizer↔template contract (prompt + architect agreed; resolved)

## Decisions taken

- **Cost ceiling: dropped.** User runs on Claude Max; dollar amounts are notional. `--max-cost` defaults to None; cost-tracking machinery preserved for benchmarking.
- **Synthesizer↔template: render pass.** Synthesizer produces structured frontmatter at `meta/synthesis.md`; pure-Python jinja2 renderer fills the 6 templates and writes deliverables. Templates remain the structural contract; synthesizer focuses on prose.
- **Model assignments: kept current.** Spec said Opus-only-for-synthesizer; impl has 4 Opus roles. Quality-vs-cost tradeoff doesn't apply for Max users. Decision: keep until eval data shows downgrade is safe.

## Pointers

- Full reviews: `prompt-engineer.md`, `architect.md`, `ai-production.md`
- Round 1+2 fix commits: `git log feat/v1-bootstrap --grep '^fix[0-9]:'`
- Open work: see "Pending" and "Smaller backlog" above
- Eval set scaffolding: not yet present; recommended path documented in `ai-production.md` §Evaluation
