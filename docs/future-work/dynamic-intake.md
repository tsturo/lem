# Parked: Connect real adaptive intake to desktop

**Parked on:** 2026-05-10
**Status:** Brainstormed at high level only; full design + plan deferred until after Feature A (iterate-on-idea) ships.
**Companion feature:** `docs/superpowers/specs/<date>-iterate-on-idea-design.md` (Feature A — being designed now)

---

## Problem statement

The desktop intake currently shows the user a 3-question mock chat (`desktop/src/renderer/screens/IntakeChat.tsx`). The questions are hardcoded, the answers are not piped into the run, and the mock is what the user sees instead of any real clarifying dialogue. Once they hit confirm, a fresh `lem refine` is spawned with `--skip-intake` hardcoded at `desktop/src/main/orchestrator-bridge.ts:63`, so the run starts from the bare one-liner with no clarifying context.

The user wants this replaced with a real Claude-driven intake — adaptive questions, no fixed count, pulling from genuine information gaps.

## What already exists

- **`src/lem/intake.py`** (~296 lines) — full Phase 0 intake orchestrator. Spawns a `claude -p` worker, asks ≤3 adaptive questions across 5 dimensions (audience, goal, mechanism, geography, success metric), writes `idea.md` + `assumptions.yaml`. Already production code. Used today only when invoked via CLI without `--skip-intake`.
- **`profiles/app-idea/intake-prompt.md`** (~23 lines) — the prompt the worker runs against. Already nuanced: skips dimensions answered by the one-liner, allows one follow-up for vagueness, refuses to fabricate.
- **`superpowers:brainstorming` skill** (open-source, in `~/.claude/plugins/cache/claude-plugins-official/superpowers/`) — a more sophisticated dialogue pattern: one question at a time, multiple-choice preferred, scope-decomposition checks, visual companion. The user mentioned adapting/incorporating this.

## Design surface (the questions worth answering when this is unparked)

1. **Wire vs adapt vs replace?**
   a. *Wire* — keep `intake.py` as-is, just stream its Q&A through orchestrator-bridge into `IntakeChat.tsx`. Smallest delta. Loses nothing.
   b. *Adapt* — keep the structure of `intake.py` but rewrite `intake-prompt.md` borrowing brainstorming-skill principles (multiple-choice options, explicit scope check, longer dialogue when warranted).
   c. *Replace* — rip out the 3-question budget, let the worker run an open-ended dialogue until it declares satisfaction. Risk: cost + latency unbounded.

2. **Streaming protocol.** `lem refine` currently emits `--json-events` for phases. Phase 0 (intake) needs bidirectional streaming: worker → desktop (next question), desktop → worker (user answer). Likely need a new event type (`intake.question`, `intake.answer`) or a separate child-process channel via stdin.

3. **Are intake answers retained for Feature A's "round 2"?** This is the cross-feature question. If user says round 2 = "make it a mobile app with comments", does the round-2 intake re-ask everything, only ask deltas, or skip intake entirely? Answer this in Feature A's design — it determines whether intake outputs need a stable schema versioned alongside runs.

4. **Mock chat removal.** `IntakeChat.tsx` currently fakes everything. Either delete it and replace with a streaming-capable component, or refactor it to accept an event source.

5. **First-run UX impact.** With real intake, time-to-first-result grows by ~30s of clarifying dialogue. Decide whether to (a) make it skippable ("ship my one-liner as-is"), (b) require it always, or (c) detect when the one-liner is rich enough and skip silently.

## Why parked

Brainstorming both features at once tangles their UX (the iterate-on-idea history flow keeps colliding with the intake flow). Feature A is also the harder design (data model + UI), and its outcome may dictate intake-answer persistence (#3 above). Once A ships, B is mostly wiring guided by A's contract.

## Resume hint

When you pick this up, start brainstorming with: "Read `docs/future-work/dynamic-intake.md`. Feature A has shipped. Now design B." The brainstorming skill will take it from there.
