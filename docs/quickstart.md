# Quickstart

Get from zero to your first idea brief in 5 minutes.

## 1. Install

```
pipx install lem
```

Or from source:

```
git clone https://github.com/tsturo/lem
cd lem
pip install -e ".[dev]"
```

Requires Python 3.11+ and the `claude` CLI with an active Max subscription or API key:

```
claude auth
```

## 2. Run your first idea

```
lem refine "an app that helps freelancers send invoices on time"
```

lem asks up to three clarifying questions, then starts the pipeline in the background:

```
? Who sends the invoices — freelancers themselves, or someone on their behalf? [freelancers themselves]
? What's the main friction today — forgetting, awkward conversations, or something else? [forgetting]

Run started: abc123
Watch: lem watch abc123
```

## 3. Watch progress

```
lem watch abc123
```

Opens a live TUI showing phases, worker statuses, and running cost. Press `q` to detach (the run continues). Press `c` to cancel.

## 4. Read the results

When the pipeline completes:

```
lem show abc123
```

This opens the executive summary in your `$PAGER`. The summary ends with an explicit verdict:

```
Verdict: Build
Confidence: medium
```

## 5. List all runs

```
lem list
```

Shows run ID, status, idea snippet, verdict, and cost.

## 6. Generate an HTML report

```
lem render abc123
```

Produces a self-contained `report.html` in the run directory. Open it in any browser or share it directly.

## Next steps

- See [docs/configuration.md](configuration.md) for all CLI flags and environment variables.
- See [docs/profiles.md](profiles.md) to customize the pipeline for different idea types.
- See [docs/development.md](development.md) to run tests or use stub mode for development.
