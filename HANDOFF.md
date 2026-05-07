# lem v1 — Session handoff

**Last updated**: 2026-05-07
**Branch**: `feat/v1-bootstrap` (pushed to `tsturo/lem`)
**Last commit**: see `git log -1` (most recent fix or doc commit)

This file is for resuming work after `/clear`. Read first; then `git log feat/v1-bootstrap` for full history.

---

## Where we are

- **All 43 plan tasks complete.** v0.1.0 implementation done.
- **580 tests passing**, 2 skipped (live-API tests gated by `LEM_LIVE_TEST=1`).
- Three-reviewer audit complete (`docs/reviews/`); 8 fix commits applied to address must-fix findings.
- Branch is on `tsturo/lem feat/v1-bootstrap`. **Not merged to main, not tagged, not on PyPI.**

## To resume after `/clear`

1. **Read CLAUDE.md** (auto-loaded by Claude Code when working in this repo). Establishes conventions.
2. **Skim `docs/reviews/SYNTHESIS.md`** for the audit's deduped action list. Ignore individual review files unless drilling into a specific finding.
3. `git log feat/v1-bootstrap --oneline` for commit history.
4. `pytest -q` to confirm green baseline (should show 580 passed, 2 skipped).
5. `LEM_STUB_MODE=1 lem refine "test idea" --attach` to see the pipeline run end-to-end (no API calls).

## What works (v0.1.0 capabilities)

- 9-phase pipeline runs end-to-end on stub mode (deterministic, no claude calls).
- Live smoke test passes against real claude (gated; spends real tokens).
- TUI (`lem watch <id>`) shows pipeline progress, active workers, issues, control protocol.
- Atomic state.json + JSONL ledgers for cost / timeline / log.
- SIGTERM-then-SIGKILL timeout escalation; phase circuit breaker (50% threshold, synthesize exempt); cost ceiling (off by default for Max users).
- Schema-validated outputs per role; one-retry-on-schema-failure with errors fed back via continuation.
- Verdict auto-downgrade enforced by orchestrator (rewrites `meta/synthesis.md` and re-renders deliverables).
- Pruner archives losing branches with structured rejection frontmatter (`_archive/option-<loser>.md`).
- Render pass: synthesizer produces structured frontmatter; pure-Python jinja2 fills 6 templates.
- Lifecycle hooks (TOML), webhook poster (with retry), OS notifications, CC slash command (`/lem-refine`), `.claude/agents` symlinks.

## What's known to be incomplete

### Production-safety items (Round 3 — not yet implemented)

These are bounded-scope items the AI production reviewer flagged. Each is its own commit's worth of work; not blocking v1 but recommended before publishing.

1. **Prompt-injection fencing** (~½ day). User one-liner is concatenated verbatim with a soft fence. Need random-delimiter fences + content-directive stripping. See `docs/reviews/ai-production.md` C1.
2. **Citation grounding verifier** (~1 day). Schema validates shape, not truthfulness. Synthesizer can cite `C7` when only `C1`–`C3` exist. Add post-synthesis regex verifier for IDs and quoted strings. See `ai-production.md` C2.
3. **Persist rendered prompts + raw outputs** (~½ day). `meta/prompts/<phase>-<role>-<attempt>.json` + `meta/raw/<phase>-<role>-<attempt>.txt`. Without this, prompt-regression debugging is impossible. See `ai-production.md` C5.
4. **Reference eval set + LLM-as-judge regression test** (~2 days). 20-idea reference dataset under `tests/eval/reference_ideas/` + Sonnet judge with 4-criterion rubric. Run on every PR touching role prompts. See `ai-production.md` recommendations §1-§4. **Eval data needs your judgment** (correct verdicts, acceptable confidence per idea).

### Smaller backlog (deferred)

- **Devil's-advocate fallback** when <2 disagreements found. Spec promised, never implemented. See `prompt-engineer.md` cross-cutting #4.
- **Missing Discover-phase `skeptic.md`** referenced in spec table but the role file does not exist. Either add the file or update the spec.
- **Enum tightening** for `customer_development_signal`, `target_user_acuteness` in `market.md` frontmatter (currently free-form strings; downstream can't key off them).
- **Saturation enum gating** on competitor count (currently uncalibrated). See `ai-production.md` I3.
- **Confidence mechanically computed** (currently asserted by synthesizer). See `ai-production.md` I4.
- **Regulated-domain / illegal-activity classifier** (e.g., medical, financial, weapons). See `ai-production.md` I5.
- **`--depth=deep` K=3** (currently always K=2).
- **Webhook payload missing** `recommendation`, `confidence`, `kill_strength`. See `ai-production.md` I8.
- **Per-attempt cost tracking** (schema-failure retries collapsed into one event).
- **`parse_retry_after` is dead code** in CLI mode (acknowledged in retry.py).
- **`maybe` in `would_change_verdict_if_false`** silently treated as not-load-bearing for verdict downgrade (M5 in ai-production review).
- **Pruner copying surviving option's frontmatter** into `decision.md`. Important for cross-skeptic to have specifics to cite. Partially addressed by `07ada68` archiving losers; verify pruner role prompt now copies surviving frontmatter explicitly.

## Open decisions

- ~~Cost ceiling~~ → resolved: dropped (default `None`); Max users unaffected.
- ~~Synthesizer↔templates~~ → resolved: render pass; structured frontmatter contract.
- ~~Round 1+2 fixes~~ → resolved: 8 commits applied (`fix1` through `fix8`).
- **Round 3** → not started. Pick from the 4 items above.
- **Model assignments** — 4 Opus roles vs spec's 1; Max user is unaffected by cost; quality eval needed before downgrading. **Decision: keep current assignments until eval data exists.**
- **Release path** — no merge to main, no tag, no PyPI. See "Release sequence" below.

## Live smoke test (when ready to validate the full chain)

```bash
LEM_LIVE_TEST=1 pytest tests/e2e/test_live_smoke.py -v
```

Costs ~$5-10 in API tokens (or comes off Max allowance). Verifies end-to-end with real claude. Asserts only that the run completes — quality requires human review of `deliverables/*.md`.

## Release sequence (when ready)

1. Bump `pyproject.toml` version `0.0.1` → `0.1.0`
2. Optional: create `CHANGELOG.md` (doesn't exist yet)
3. Update README.md if anything user-facing changed since the last revision
4. Merge `feat/v1-bootstrap` to `main` (PR or fast-forward — your call)
5. `git tag v0.1.0 && git push --tags`
6. `gh release create v0.1.0 --generate-notes` with built wheel attached
7. Optional: `python -m build && twine upload dist/*` for PyPI

**Do not run any of these without explicit go-ahead.** Each step is irreversible (or hard to reverse).

## Suggested first activity in next session

Pick one based on appetite:

- **Validate the chain**: live smoke test, read the generated deliverables, decide if the prompts produce useful output.
- **Tighten the prompts**: read `docs/reviews/prompt-engineer.md` per-file edits and apply the ones you agree with. Each role file is independently editable; commit per file.
- **Implement Round 3 #1 (prompt-injection fencing)**: smallest production-safety win, ~½ day. Improves outputs for non-author users.
- **Implement Round 3 #4 (eval set scaffolding)**: highest-leverage long-term work, but heaviest. Set up `tests/eval/` structure first, populate reference data over time.
- **Cut v0.1.0**: if you're satisfied with current state, follow Release sequence above.

## Key file pointers

- **CLAUDE.md** — auto-loaded conventions
- **README.md** — user-facing
- **docs/reviews/SYNTHESIS.md** — start here for audit findings
- **docs/superpowers/specs/2026-05-06-lem-framework-design.md** — design spec (some claims now out of date; fix commits noted in audit)
- **docs/superpowers/plans/2026-05-06-lem-framework.md** — original 43-task plan
- **docs/superpowers/agent-prompt.md** — original kickoff brief (still useful for spawning future implementer agents)
- **profiles/app-idea/** — the only profile shipping in v1
- **process_roles/** — 9 profile-independent role prompts (the "soul of lem" per the agent prompt)

## Safety reminders

- This branch has 50+ atomic commits; per-task audit trail is preserved.
- All commits are co-authored with `Claude Opus 4.7 (1M context)`.
- Never force-push, never `git reset --hard` on shared branches without asking.
- The user is on Claude Max — dollar cost figures in code are notional.
- The role prompts under `process_roles/` and `profiles/app-idea/roles/` are the highest-leverage content. They were AI-drafted; **the original agent prompt called for human review of every prompt before merge.** That review hasn't happened yet — pick whichever you want to revise based on `docs/reviews/prompt-engineer.md` per-file findings.
