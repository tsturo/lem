# Configuration

Full reference for `lem refine` flags, environment variables, and config files.

## `lem refine` flags

| Flag | Default | Description |
|---|---|---|
| `--max-cost` | `25.0` | Hard cost ceiling in USD. Run aborts if projected spend exceeds this. |
| `--max-wall-clock` | `14400` | Wall-clock timeout in seconds (4 hours). |
| `--max-concurrent` | `4` | Maximum parallel worker invocations within a phase. |
| `--attach` | `false` | Run in foreground instead of background. |
| `--workspace` | auto | Use a specific workspace directory instead of the default run directory. |
| `--profile` | `app-idea` | Named profile to use. Profiles live in `profiles/` in the repo. |
| `--with-pitch` | `false` | Generate `investor-onepager.md` in addition to default deliverables. |
| `--with-roadmap` | `false` | Generate `roadmap.md`. |
| `--with-techstack` | `false` | Generate `tech-stack.md`. |

## Environment variables

| Variable | Description |
|---|---|
| `LEM_CLAUDE_BIN` | Path to the `claude` binary. Default: PATH lookup. |
| `LEM_RATES_FILE` | Path to a JSON file overriding default token cost rates. Format: `{"haiku": [input_rate, output_rate], "sonnet": [...], "opus": [...]}`. Rates are per-token in USD. |
| `LEM_NOTIFY` | Set to `0` to disable OS notifications on run completion. |
| `LEM_STUB_MODE` | Set to `1` to skip claude invocations entirely (writes placeholder output). Useful for orchestrator development and CI. |
| `LEM_STUB_MODE_DIR` | Path to a directory of `<role>.md` canned output files used by stub mode. |
| `LEM_LIVE_TEST` | Set to `1` to enable live API smoke tests (consumes real tokens). |

## Config file

lem reads `~/.config/lem/config.toml` on startup. All keys are optional.

```toml
[defaults]
max_cost = 25.0
max_wall_clock = 14400
max_concurrent = 4
profile = "app-idea"

[notify]
enabled = true

[hooks]
on_complete = ""   # shell command to run on successful completion
on_error = ""      # shell command to run on failure
```

## Workspace config (lem.toml)

A `lem.toml` in the workspace directory overrides global config for that run:

```toml
[hooks]
on_complete = "open deliverables/executive-summary.md"
on_error = "say 'lem pipeline failed'"
```

Hooks receive the run state as environment variables:
- `LEM_RUN_ID` — run identifier
- `LEM_STATUS` — final status
- `LEM_COST` — total cost in USD
- `LEM_WORKSPACE` — workspace directory path

## Default token rates

Built-in rates (per-token USD). Override with `LEM_RATES_FILE`.

| Model | Input | Output |
|---|---|---|
| haiku | $0.0000010 | $0.0000050 |
| sonnet | $0.0000030 | $0.0000150 |
| opus | $0.0000150 | $0.0000750 |
