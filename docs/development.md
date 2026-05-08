# Development

## Running tests

Standard tests (no API calls):

```
pytest -q
```

Live API smoke test (consumes real claude tokens):

```
LEM_LIVE_TEST=1 pytest tests/e2e/test_live_smoke.py -v
```

This requires:
- `claude` CLI installed and authenticated
- A Claude Max subscription or API key configured

Expected cost: ~$5–10 per run. The test enforces `max_cost=5.0`; the orchestrator
aborts if exceeded.

## Stub mode

Run the full pipeline locally with no API calls:

```
LEM_STUB_MODE=1 lem refine "test idea" --workspace /tmp/lem-stub-test
```

Or point to a custom canned-outputs directory:

```
LEM_STUB_MODE=1 LEM_STUB_MODE_DIR=/path/to/canned lem refine "test idea"
```

Skips claude entirely; useful for orchestrator development and CI.

## Environment variables

| Variable | Purpose |
|---|---|
| `LEM_STUB_MODE` | Set to `1` to skip claude invocations entirely |
| `LEM_STUB_MODE_DIR` | Path to directory of `<role>.md` canned output files |
| `LEM_LIVE_TEST` | Set to `1` to enable live API smoke tests |
| `LEM_CLAUDE_BIN` | Path to claude binary (default: PATH lookup) |
| `LEM_RATES_FILE` | JSON file overriding default token cost rates |

## Project layout

```
src/lem/               — main package
  orchestrator.py      — run loop, phase iteration
  phases.py            — declarative PHASES list
  profile.py           — profile + role loader
  workers/
    cli_worker.py      — claude subprocess wrapper (LEM_STUB_MODE here)
    dispatch.py        — retry, schema validation seam
  schema/
    parser.py          — frontmatter + section parser
    validator.py       — output_schema validation
  failure/
    ceiling.py         — cost + wall-clock projection
    breaker.py         — phase circuit breaker
    retry.py           — retry policy
  state/
    run_state.py       — state.json read/write
    cost.py            — cost.jsonl + aggregate
    events.py          — meta/events/*.json writer
process_roles/         — built-in pipeline roles (jtbd-extractor, synthesizer, …)
profiles/              — named profiles (app-idea)
tests/
  unit/                — isolated unit tests
  integration/         — orchestrator + component integration tests
  e2e/                 — end-to-end tests (stub + live)
  fixtures/
    stub-profile/      — deterministic stub profile for e2e tests
```
