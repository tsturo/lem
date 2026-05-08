# Prompt Engineering Review

Reviewer lens: senior prompt engineer evaluating system prompts for structural quality, constraint clarity, and resistance to common LLM failure modes.

## Cross-cutting observations

**1. The synthesizer prompt does not match the deliverable templates.** The Jinja2 templates (`executive-summary.md.j2`, `mvp-plan.md.j2`, `risks-and-rejected-paths.md.j2`) reference variables that the synthesizer prompt never names: `summary_body`, `confidence_rationale`, `top_risks` (with `severity`/`likelihood`/`trigger`/`mitigation`), `phase_1/2/3` build sequence with `effort`/`deliverable`, `mvp_in_scope`/`mvp_out_of_scope`, `architecture_sketch`, `target_user`, `jtbd`, `why_now`, `reframings` with `shift_conditions`, etc. The synthesizer is told only to write a `## Verdict` section and a vague "frontmatter declares which deliverables you wrote" — nothing about producing the data the templates need. **This is the single biggest systemic risk in the prompt set.** Either the templating layer extracts these fields from a structured synthesizer output (which the prompt must define), or the synthesizer must be told to write directly into each deliverable file with these exact sections.

**2. Frontmatter schemas are partly redundant with body instructions but partly contradictory.** The validator only checks frontmatter keys + section presence + min words. Several prompts let the body instructions drift from the schema (see specifics per file). This means schema-valid output can still be wrong, and prompts have no way to enforce content via the validator.

**3. "Frame engagement" is mandated identically in three specialist prompts but is not in the schema for two of them.** Architect, designer, and market all require `## Frame engagement` as the FIRST section. (a) it duplicates the same paragraph in three files; (b) `min_words` exit criteria are not set on it for any role, so a one-line "I kept the frame" passes validation; (c) none of the three prompts tell the specialist to *cite* a specific reframing from `frame-shifter/draft-1.md` by name, so the section can degenerate into "I considered alternatives" theater.

**4. The four skeptic roles have differentiated inputs but somewhat undifferentiated voice/method.** Branch-skeptic, cross-skeptic, and kill-case-skeptic all use phrases like "strongest objection / strongest case / hostile expert." (The Discover-phase `skeptic.md` referenced in the spec table at row 244 does not exist as a file; "four distinct skeptics" maps to three actual roles.)

**5. Several prompts use the vague verbs they ban.** The architect prompt's "Discipline" section forbids hand-waves but the body asks the worker to write "honest assessment" and "where are the surprise costs?" without enumerating signal patterns.

**6. Worker isolation: prompts read `*/draft-1.md` but worker isolation is "allowed_read_paths whitelist."** Whether the orchestrator's whitelist matches what the prompt declares is testable but not enforced by the prompt itself.

## Per-file findings

### profiles/app-idea/roles/architect.md

**Strengths**: Clear role identity opener + out-of-lane disclaimer. Frontmatter fields are concretely typed with example values inline. "No kitsch comparisons" + "Don't write 'like Notion but for X'" is precise and testable.

**Important**:
- `branchable: yes` but the prompt body never tells the architect what shape an "alternative" should take in a branched dispatch. The branch axis presumably arrives via `extra_context`, but the prompt does not acknowledge this context key or tell the worker to commit to one side of the axis.
- `## Tractability` overlaps heavily with `## Build complexity`. The schema only requires `Build complexity` min_words: 30; tractability has no minimum, inviting one-liner skip.
- "Frame engagement" has no exit criteria. A worker can write "I kept the frame because the original is fine" and pass schema. This defeats the cross-skeptic's `Frame engagement mismatch` heuristic.

**Concrete edits**:
- Add to frontmatter `exit_criteria`:
  ```yaml
  Frame engagement:
    min_words: 60
    must_reference: ["frame-shifter/draft-1.md alternative_shapes"]
  Tractability:
    min_words: 40
  ```
- Before the Frame engagement instructions, prepend: "If the orchestrator passed `branch_option` and `branch_axis` in your context, your output is for that side of the axis only. State at the top of `## Architecture overview`: 'This option commits to <axis-side>'. Do not hedge across the axis."
- Replace the Frame engagement instructions with: "Read `frame-shifter/draft-1.md`. Pick at least 2 entries from its `alternative_shapes` list and name them by their exact label. For each: one paragraph stating whether you adopted it, hybridized, or rejected — and what specific architectural commitment changes (or does not) as a result."
- Disambiguate Build complexity vs Tractability: rename `## Build complexity` → `## Where it gets expensive` and `## Tractability` → `## Research-project flags`.

### profiles/app-idea/roles/designer.md

**Strengths**: Concrete example flow (User opens cold → Today screen → 3 cards). `core_interaction_pattern` as a *named* string ("swipe-card review queue") is excellent — argueable, not vibes. "If you cannot pick, that's a real signal — surface it as a branching axis" — productively connects to disagreement-detector.

**Important**:
- `branchable: conditional` but no condition is named in the prompt or in the role file. Either spell it out ("branch only if a UX axis was named in `disagreements.md`") or remove from the role file.
- Failure-states section: "For each entry in `failure_states`, write 2–3 sentences." But schema does not require Failure states section to have a min_words.
- The example failure states ("offline edit then sync conflict") presume an app frame. If frame-shifter shifted to a content product or service, these are nonsensical.

**Concrete edits**:
- Add to exit_criteria: `Failure states: { min_words: 80 }`, `Frame engagement: { min_words: 60 }`.
- Replace failure-states first sentence with: "For each entry in `failure_states`, write 3–4 sentences naming: (a) what triggers this state, (b) what the user sees on the screen — name the visible elements, (c) the recovery action and how the user discovers it."
- Resolve `branchable: conditional`: either delete the key from the role file (let policy live in profile.yaml) or change the prompt's pre-amble to: "If your context includes `branch_option=a|b`, the orchestrator detected a UX axis and you are writing for one side."

### profiles/app-idea/roles/market.md

**Strengths**: The single best discipline section in the corpus: "No vibes-based TAM," "Hostile-witness mode," "AI-powered is not a differentiator in 2026," "URLs when possible." `customer_development_signal` enum-like list captures real epistemics. Explicit instruction to use WebFetch/WebSearch with "A market analysis without named, currently-existing competitors is worthless."

**Critical**:
- The `customer_development_signal` field is one short string but the prompt offers four exemplar values. There is no enum constraint. **The kill-case-skeptic's `kill_strength: decisive` calculation depends on knowing whether customer development is "speculation."** This field should be an enum.

**Important**:
- `target_user_acuteness` has the same problem.
- `direct_competitors` minimum is "3 (or say what you searched for)" — but a worker who searches and finds 1 will pass schema with 1 + a bullet about searches.
- WebFetch/WebSearch budget unspecified. A worker can run 50 fetches and blow rate limits.

**Concrete edits**:
- Convert `customer_development_signal` and `target_user_acuteness` to enums in frontmatter:
  ```yaml
  enums:
    customer_development_signal: [paying-waitlist, interviewed-target-users, founder-in-segment, speculation]
    target_user_acuteness: [high-daily-blocker, medium-annoyance, low-nice-to-have, unknown]
    saturation: [low, medium, high, very-high]
  ```
- Add to body: "Tool budget: at most 8 WebFetch + 4 WebSearch calls. Prioritize: (1) named-competitor pricing pages, (2) recent reviews from G2/Capterra/Reddit, (3) category analyst reports."

### process_roles/jtbd-extractor.md

**Strengths**: Tightest, cleanest role in the corpus. One line of output, canonical Christensen form, three accept and three reject examples. Output cap of 300 tokens enforces brevity. **This role is essentially fine.**

**Minor**: The required section is `## JTBD` but `jtbd:` is also in frontmatter. Two sources of truth for the same string. Add: "The frontmatter `jtbd:` value and the first line of `## JTBD` must be identical strings."

### process_roles/frame-shifter.md

**Strengths**: Strong opening. The 5-point structure for each alternative shape is excellent. Prompt-fragment substitution mechanism is clean.

**Critical**:
- The frontmatter says this role is `phase: reframe` but the spec puts frame-shifter at **Phase 0.5, *before* Discover**. The prompt body says "you have read-only access to … the three specialist drafts (`architect/draft-1.md`, `designer/draft-1.md`, `market/draft-1.md`). Read them." But at Phase 0.5 those drafts do not exist yet. **The prompt is contradicting the architecture.**

**Concrete edits**:
- Resolve the input contradiction. Replace specialist-drafts read instruction with: "If the orchestrator scheduled this role *after* Discover (rare), specialist drafts will exist. In the default v1 pipeline, this role runs *before* Discover and only `idea.md`, `assumptions.yaml`, `frame-shifter/jtbd.md` are available."
- For heretical takes: "Each take must name the specific entity that makes it bite. 'Should be a feature in $tool' must name $tool. 'Users want to talk about wanting this' must name where (Twitter, /r/X, founders' Slack)."

### process_roles/disagreement-detector.md

**Strengths**: The `axes_by_domain` dict structure is exactly right — clean machine-readable contract. "An axis is binary or near-binary." "Don't manufacture disagreement."

**Important**:
- The spec line 337 says: "If <2 substantive cross-specialist divergences are found, a devil's-advocate prompt fires." But this role does not contain devil's-advocate logic and no separate role file exists. **The "sycophantic convergence" failure mode is partially addressed but the devil's-advocate fallback is unimplemented.**
- `axes_by_domain` keys are not enum-constrained. Add explicit key enum: `architect, designer, market` only.

**Concrete edits**:
- Add a `## Devil's advocate` section, conditional: "If `substantive_disagreements` is empty or has fewer than 2 entries, this section is REQUIRED. Pick the strongest consensus claim across the three specialists and argue against it for one paragraph, attributing the contrarian position to no specialist."

### process_roles/branch-skeptic.md

**Strengths**: "The single objection a hostile expert would actually raise." Two contrasting examples (bad: "this might not scale"; good: "per-user Postgres schemas at 3000 users"). `fatal: bool` with "be parsimonious."

**Important**: The prompt assumes the worker sees `extra_context.option_label` but doesn't standardize how `extra_context` is exposed. Add: "Your context will include `option_label: 'a'` or `option_label: 'b'`. The single file you read is named `option-a.md` or `option-b.md` accordingly."

### process_roles/pruner.md

**Strengths**: `survivor: enum [a, b, neither]` with `neither` reserved for "both options dominated." "Pick. 'Both have merit' is not a decision."

**Critical**:
- The pruner reads four files and writes a `decision.md`. But the prompt does NOT instruct the pruner to copy frontmatter fields from the surviving option (e.g., `data_entities`, `state_locus`). The cross-skeptic and synthesizer read `<domain>/decision.md` for verdict-bound fields. **If the pruner produces a decision.md without those fields, the cross-skeptic gets nothing to cite.**

**Concrete edits**:
- Add to frontmatter section: "Copy ALL frontmatter fields from the surviving option's `option-<a|b>.md` into your `decision.md` frontmatter, *plus* add `domain`, `survivor`, `rationale_oneline`. Cross-skeptic and synthesizer read these fields directly."

### process_roles/distiller.md

**Strengths**: "Compress, don't summarize." "Cite, don't paraphrase" with the IndexedDB example.

**Important**:
- The prompt says "lean primarily on per-domain decision.md files" but doesn't tell the distiller to **copy the frontmatter values verbatim into the Decisions section**.
- `would_change_verdict_if_false: yes|no|maybe` introduces a `maybe` value that does not appear in `assumptions.yaml`'s schema (the spec specifies `yes | no` only). Schema drift.

**Concrete edits**:
- Add to Decisions section: "For each domain, the first bullet must enumerate the decision.md frontmatter values verbatim: `architect: data_entities=[…], external_dependencies=[…], state_locus=…`."
- Remove `maybe` unless the assumptions schema is updated.

### process_roles/cross-skeptic.md

**Strengths**: Five named "classic patterns to hunt for" — strongest few-shot in the corpus. Stable conflict IDs (C1, C2). Severity tagging (structural | tradeoff | cosmetic). "Zero conflicts is a valid output. Do not invent conflicts."

**Important**: Pattern 5 ("Frame engagement mismatch") asks the cross-skeptic to read each specialist's frame engagement section. But cross-skeptic only has access to `decision.md` files, where these may not survive pruning. Add `<role>/draft-1.md` to allowed_read_paths or have the pruner copy the surviving Frame engagement section into decision.md.

### process_roles/kill-case-skeptic.md

**Strengths**: `assumptions_leveraged` and `conflicts_leveraged` as **non-empty** lists with the rule "if you cannot cite at least one, you have not done the work." `kill_strength` enum with explicit calibration rules. "Be willing to say 'weak.'"

**Important**:
- The role is supposed to NOT rehash Discover-phase concerns (per spec). The prompt body does not say this explicitly.
- The `kill_strength: decisive` calibration: requires "load-bearing unconfirmed assumption" but the prompt does not require those IDs to have `would_change_verdict_if_false: yes`.

**Concrete edits**:
- Add: "**Do not rehash Discover-phase concerns.** If your kill case repeats the market-saturation argument that the market specialist already made in Discover, you have done the wrong work."
- Tighten: "decisive requires at least one *structural* cross-conflict from `cross-critique.md` (severity=structural) AND at least one assumption from `assumptions_leveraged` whose `would_change_verdict_if_false` is `yes`."

### process_roles/synthesizer.md

**Strengths**: "No advice-mode without object" with concrete before/after example. "Frontmatter `recommendation` MUST match the wording of the Verdict section's first sentence." `verdict_constraint = insufficient_info` override mechanism.

**Critical**: **The synthesizer prompt does not match the deliverable templates.** The Jinja2 templates need many specific named variables that the prompt does not require. *(Resolved in commit `bc9005e` via render-pass refactor.)*

**Important**:
- Synthesizer is told to read `frame-shifter/draft-1.md` but `risks-and-rejected-paths.md.j2` requires `reframings[].shape`, `reframings[].why_rejected`, `reframings[].shift_conditions`. The prompt does not tell the synthesizer to extract them in this shape.
- "If `verdict_constraint == insufficient_info`" — the prompt does not explain HOW the orchestrator passes `verdict_constraint`. *(Resolved in commit `0dc9b2b` via jinja extra_context substitution.)*
- Confidence calibration: "high requires confirmed customer development + zero structural cross-conflicts + non-empty differentiator" — three logical conditions with no enforced conjunction.

### profiles/app-idea/prompt-fragments/frame-shifter.md

**Strengths**: Seven canonical alternative shapes well-chosen. "Reject the ones that don't fit." Heretical takes named specifically.

**Minor**: "Pick at least two" but the role spec says minimum 3. Reconcile.

### profiles/app-idea/intake-prompt.md

**Strengths**: Triple-locked "AT MOST 3" constraint. Five dimensions in priority order with concrete examples. "After asking, listen. Do not pre-answer or hedge."

**Important**: The prompt does not specify the `assumptions.yaml` schema (each entry needs `id`, `description`, `confirmed: bool`, `would_change_verdict_if_false: yes|no`). A Sonnet worker may produce variant YAML.

**Concrete edits**: Add explicit schema with example showing all four required keys.

## Failure-mode coverage assessment

**Sycophantic convergence**: disagreement-detector addresses it; **devil's-advocate fallback is unimplemented** (gap).

**Critic theater**: three of four claimed skeptic roles exist (branch / cross / kill-case); the fourth (Discover-phase skeptic) is missing. Differentiation by inputs is load-bearing; could push harder on differentiated method.

**Manufactured alternatives**: addressed at prompt level by disagreement-detector; orchestrator wiring is correct.

**Fake-positive verdict**: assumptions register addressed via intake; kill-case is mandatory; "Insufficient information" is first-class; auto-downgrade rule is now enforced (commit `ac0b639`).

**Generic / advice-mode slop**: synthesizer has the cleanest version. *Gap*: rule is not restated in pruner/distiller/cross-skeptic/kill-case-skeptic; slop can leak in upstream.

**Distillation losing critical info**: synthesizer reads BOTH distilled and raw decision.md. Distiller does not preserve frontmatter values verbatim by default.

## Top-3 priority fixes (at time of review)

1. **Fix the synthesizer ↔ deliverable template contract.** [Resolved in `bc9005e`]
2. **Fix the pruner → cross-skeptic frontmatter pipeline.** [Partially resolved in `07ada68` — archive frontmatter is written; copying surviving option's frontmatter into decision.md is still pending if the pruner doesn't do it]
3. **Resolve the frame-shifter input contradiction.** [Resolved in `9a566e2` — Reframe now runs before Discover so specialist drafts don't exist when frame-shifter runs]
