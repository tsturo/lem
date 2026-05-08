# Multi-Agent Architecture Review

Reviewer lens: senior architect evaluating pipeline structure, role responsibilities, information flow, and coordination mechanisms.

## System overview

`lem` is a phase-serial / role-parallel orchestrator that turns a one-liner into a verdict-bearing markdown deliverable by walking nine phases. Each phase is a function `(state, profile) -> list[WorkerInvocation]`; the orchestrator decides parallel vs. sequential, runs a cost ceiling check, dispatches via `claude -p` subprocesses, validates outputs against per-role schemas, and aggregates per-worker JSON events into `cost.jsonl` at phase boundaries. Workers write to declared output paths only, and inter-worker information flow is strictly disk-mediated through `allowed_read_paths`.

The design is fundamentally sound — clean dataclass contracts, atomic writes, schema validation with one retry, hybrid CLI/SDK plan, and a serial-aggregation cost ledger that avoids races. The chief concern is divergence between the spec and the implementation: the most important pipeline ordering decision in the spec has been inverted in code, and several "non-negotiable" enforcement mechanisms exist only in the spec.

## Pipeline coherence

**Reframe ordering inversion (likely failure, spec→implementation gap; high confidence).** The spec puts Reframe at Phase 0.5, *before* Discover. The implementation puts Reframe at id `1.6`, *after* Discover and Disagreement. Discover specialists are given `frame-shifter/jtbd.md` (the 1-line JTBD) but not `frame-shifter/draft-1.md` (the alternative-shapes document). Yet the specialist role files all *require* a `## Frame engagement` section that "lists 2–4 alternative framings you considered" — which is unenforceable when the alternative framings haven't been generated yet. **Resolved in commit `9a566e2`** — Reframe moved to phase 0.6.

**Phase numbering inconsistency**: Phase ids in the impl (`0`, `0.5`, `1`, `1.5`, `1.6`, ...) do not match the spec table. Cosmetic.

**JTBD vs Reframe redundancy.** The impl splits one frame-shifter role into a separate `jtbd-extractor.md` and `frame-shifter.md`. Reasonable refactor, but the JTBD extractor's output goes into `frame-shifter/jtbd.md` (under the frame-shifter directory), which is confusing.

**Specialist count mismatch.** Spec lists 4 specialists (architect, designer, market, skeptic). Impl has 3 (skeptic dropped). The spec also touts "four distinct skeptic role files"; impl has 3.

## Role boundaries

Boundaries are clean. Architect, designer, market declare disjoint frontmatter fields and explicitly tell each role to "stay out of the other's lane."

The skeptic chain is well-differentiated by reading inputs:
- branch-skeptic: reads ONE option file
- cross-skeptic: reads decisions across domains + distilled
- kill-case-skeptic: reads cross-critique + assumptions + decisions

One concern: `cross-skeptic` and `kill-case-skeptic` both run on Opus. The spec promises "Opus is used for one role only: synthesizer." The impl has 4 Opus roles: cross-skeptic, kill-case-skeptic, frame-shifter, synthesizer. *(For Max users this is moot; for API users it triples the spec's "$10–12 typical" claim.)*

## Information flow

**Synthesizer load (manageable).** Synthesizer reads ~10 files, roughly 21K input tokens — well within Opus's window.

**Distillation may lose load-bearing info — partially mitigated.** `_synthesize_workers_fn` reads BOTH `meta/distilled/post-explore.md` AND each raw `decision.md`, which honors the spec's "verdict-bound from raw, prose from distilled" distinction.

**Distiller does not read everything it should.** `_distill_workers_fn` allows reads only on `decision.md` per specialist. The distiller role file explicitly says "you have read-only access to ... `idea.md`, `assumptions.yaml`, `frame-shifter/draft-1.md`." That promise was broken. **Resolved in commit `0bd1ba7`.**

**Branching gate logic**: `_explore_gate_fn` reads `disagreements.md` frontmatter for `axes_by_domain` (a dict) and skips the phase if every value is empty. Gate semantics match the disagreement-detector's role file. **Wired correctly.**

## Failure modes and recovery

**Disagreement-detector returning garbage frontmatter.** `_explore_gate_fn` wraps `parse_file` in a bare try/except that returns `False` on any parse error. Result: if the detector flakes, Explore is skipped silently and the rename `draft-1.md → decision.md` (formerly inside `_explore_workers_fn`) never happens. Distill, critique, and synthesize crash on missing reads. **Resolved in commit `00ca58e`** — rename moved to a setup_fn that runs unconditionally before the gate.

**Specialist schema-validation exhaustion.** Spec says "On second failure, the phase is marked failed, workspace is preserved, run aborts." Impl uses a 50% breaker. With 3 specialists, one schema-fail = 33% < 50% threshold → phase passes but a `draft-1.md` may be malformed. Phase 1.5 then reads it. Spec→implementation gap.

**Worker timeout cascade.** If the architect times out, `<role>/draft-1.md` is never written. Phase 1.5's invocation `allowed_read_paths` lists the missing file. `_build_user_prompt` raises `FileNotFoundError`. **Whole run dies.** Consider filtering `allowed_read_paths` to only existing files (the impl already does this for distill/critique/synthesize: `*(d for d in decisions if d.exists())`, but NOT for disagreement-detector or reframe).

**kill-case-skeptic depends on cross-critique.md.** If cross-skeptic fails, kill-case-skeptic still gets dispatched, and `_build_user_prompt` raises FileNotFoundError on missing `cross-critique.md`. Whole run dies.

## Branching logic

**K=2 is hard-coded.** `_explore_workers_fn` iterates `enumerate(("a", "b"))`. Spec promises `--depth=deep` raises K=3. Not implemented.

**`_archive/` rename is missing entirely.** Spec mandates "Loser → `<domain>/_archive/option-X.md` with structured rejection frontmatter" containing five required keys. Impl: pruner writes `decision.md`; option files left in place. Synthesizer's `risks-and-rejected-paths.md` has nothing real to read. **Resolved in commit `07ada68`** — orchestrator post-processes pruner output and writes `_archive/option-<loser>.md` with rejection frontmatter.

**Non-branching draft-1 → decision.md rename.** Originally fired only when `_explore_workers_fn` ran at all, which required the gate to pass. **Resolved in commit `00ca58e`** — moved to a pre-phase setup hook.

**Pruner cannot reliably determine loser.** Pruner writes `decision.md` with `survivor: a | b | neither` in frontmatter, but the orchestrator never reads that field to act on it. **Resolved in commit `07ada68`** — orchestrator now reads `survivor` and acts on it.

## Concurrency

**Discover phase: 3 parallel under Semaphore(4).** Safe.

**Explore phase semantics were dangerous.** Generators, branch-skeptics, and pruner were all flat in one parallel dispatch. Pruner could try to read `option-a.md` before the alternative-generator finished writing it. **This was the single most serious bug in the system.** **Resolved in commit `a1aa5bb`** — Phase 2 split into 2.1 (generate) → 2.2 (critique) → 2.3 (prune).

**Critique phase declared parallel=False.** Sequential within phase; cross-skeptic completes before kill-case-skeptic dispatches. Correct.

**No two workers write the same file.** Confirmed.

## State machine

**Statuses defined**: `running`, `completed`, `failed`, `cost-aborted`, `wall-clock-aborted`, `cancelled`. Missing: a `paused` status. `_wait_for_resume` blocks but never updates `state.status`, so `lem status` reports `running` while the run is paused.

**Resume-from-crash data preservation.** What is preserved well enough to resume: `state.json` has `phase` (last completed) and `cost_so_far`; all phase outputs are atomic writes. What is missing for resume: no "in-flight workers" record; `state.phase` is set AFTER dispatch completes, so a mid-phase crash records the *previous* phase. Not a v1 issue (no resume) but worth flagging for v1.1.

## Determinism / reproducibility

**Sources of unbounded variance:**
1. Asyncio race ordering in Phase 2 *(resolved)*.
2. Model temperature — claude CLI does not currently expose `--temperature`. Unavoidable.
3. Jinja extra_context propagation — `_resolve_role` renders the system prompt against `inv.extra_context`. ChainableUndefined silently renders missing vars as empty strings. Typos in role files (`{{ branchaxis }}` vs `{{ branch_axis }}`) silently render empty. Subtle source of variance.

**Cost projection accuracy.** `_estimate_input_tokens` uses `path.stat().st_size // 4`. Reasonable for English prose; understates for compact YAML. Omits system_prompt + extra_context + framing. *(Mostly moot for Max users.)*

## Verdict pipeline

**Auto-downgrade**: Spec section "Verdict format" says "if >50% of load-bearing assumptions are agent-assumed, the recommendation auto-falls to 'Insufficient information' regardless of the synthesizer's own preference. Enforced by a small post-synthesis check in the orchestrator that reads `assumptions.yaml` + the verdict and rewrites the recommendation field if needed." Originally, impl only passed `verdict_constraint` as a soft hint via extra_context. **Resolved in commit `ac0b639`** — `_post_synthesize_verdict_check` reads frontmatter, recomputes ratio, rewrites recommendation field, atomic write.

The impl's threshold counts `would_change_verdict_if_false in ("yes", "maybe")`, which differs from spec's `yes` only. Looser, triggers `insufficient_info` more readily.

**Deliverable templates were dead code**: `profiles/app-idea/deliverables/*.md.j2` (six Jinja templates) were never invoked. **Resolved in commit `bc9005e`** — render pass implemented; synthesizer produces structured frontmatter at `meta/synthesis.md`; pure-Python jinja2 step fills templates and writes deliverables.

**The synthesizer's only schema-required section was `## Verdict`.** Spec promises "must include a `## Reframings considered` section" — was unenforced. *(Resolved by render pass; synthesizer's frontmatter contract now requires structured `reframings` list.)*

## Profile abstraction

The profile loader is reasonably tolerant but has hardcoded surfaces:

- `branching_policy` in profile.yaml is loaded but never read by the impl. Branching is gated entirely by the disagreement-detector's `axes_by_domain`. So profile-level branching policy is dead config.
- `_jtbd_workers_fn` hard-codes `frame-shifter/jtbd.md` as output. JTBD is an app-idea concept, not universal.
- `_synthesize_workers_fn` hard-codes the assumption that the deliverable is `deliverables/executive-summary.md`. A different profile's verdict might live in a different file.

For v1 (single profile shipping), this is fine. For v1.1 multi-profile, the JTBD phase, the executive-summary path, and possibly the verdict-constraint logic need profile-driven extraction.

## Top-5 architectural risks (at time of review)

1. **Phase 2 race condition (concurrency).** [Resolved in `a1aa5bb`]
2. **Reframe runs after Discover, not before (pipeline coherence).** [Resolved in `9a566e2`]
3. **Disappearing decision.md when no branching axis exists (failure mode).** [Resolved in `00ca58e`]
4. **Verdict auto-downgrade is unenforced; deliverable templates are unused (spec→impl gap).** [Resolved in `ac0b639` and `bc9005e`]
5. **`_archive/` rejection frontmatter is missing entirely (branching, spec→impl).** [Resolved in `07ada68`]

## What works well (don't change)

- **Worker contract.** `WorkerInvocation` / `WorkerResult` are clean, frozen dataclasses with kw-only init. The contract's seam (`dispatch_worker`) cleanly separates orchestration from invocation.
- **Disk-only inter-worker communication + atomic writes.** `tmp + rename` everywhere. Phase-boundary aggregation of `cost.jsonl` is serial → no race on the hot path.
- **Schema validator.** Frontmatter + section presence + placeholder detection + exit_criteria DSL is a small but high-leverage layer. The line-relative placeholder error coordinates ("body line N") and the in-fence skip are thoughtful.
- **Per-role timeouts with SIGTERM-then-SIGKILL escalation.** Many agent systems leak hung child processes; lem doesn't.
- **Phase-level circuit breaker.** Synthesize-exempt with a clear comment explaining why.
- **The four-skeptic-with-distinct-role-files design** (modulo the missing Discover-phase skeptic). Real architectural decision against critic theater.
- **The recommendation auto-downgrade rule** (now actually enforced). One mechanical guardrail is worth a hundred prompt directives.
- **Profile-as-directory + `process_roles/` split.** The orchestrator never special-cases either set. Right abstraction for v1.1 multi-profile.
