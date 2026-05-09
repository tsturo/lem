"""`lem refine`."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Annotated, Optional

import typer

from lem.daemon import daemonize
from lem.install_agents import install_agents
from lem.intake import run_intake
from lem.orchestrator import OrchestratorConfig, ProgressEvent, run_orchestrator
from lem.paths import make_run_id, resolve_workspace
from lem.profile import load_profile
from lem.types import Profile

app = typer.Typer()


@app.command()
def refine(
    idea: Annotated[
        Optional[str],
        typer.Argument(help="One-line description of the idea (omit if --from-file)"),
    ] = None,
    from_file: Optional[Path] = typer.Option(
        None,
        "--from-file",
        "-f",
        help="Read the idea from a file instead of the positional argument.",
        exists=True,
        dir_okay=False,
        readable=True,
    ),
    profile: str = typer.Option("app-idea", "--profile"),
    depth: str = typer.Option("normal", "--depth", help="quick|normal|deep"),
    model_tier: str = typer.Option("opus-heavy", "--model-tier"),
    max_cost: Optional[float] = typer.Option(
        None,
        "--max-cost",
        help=(
            "Dollar ceiling for the run. For users on metered Anthropic API "
            "billing. Claude Max users should ignore this — dollar costs are "
            "notional. Default: no ceiling."
        ),
    ),
    max_wall_clock: int = typer.Option(4 * 3600, "--max-wall-clock"),
    max_concurrent: int = typer.Option(4, "--max-concurrent"),
    workspace: Optional[Path] = typer.Option(None, "--workspace"),
    no_verdict: bool = typer.Option(False, "--no-verdict"),
    with_pitch: bool = typer.Option(False, "--with-pitch"),
    with_roadmap: bool = typer.Option(False, "--with-roadmap"),
    with_techstack: bool = typer.Option(False, "--with-techstack"),
    skip_intake: bool = typer.Option(False, "--skip-intake"),
    webhook: Optional[str] = typer.Option(None, "--webhook"),
    name: Optional[str] = typer.Option(None, "--name"),
    show_cost: bool = typer.Option(False, "--show-cost"),
    attach: bool = typer.Option(False, "--attach"),
    verbose: bool = typer.Option(
        False, "--verbose", help="Operator-style logs (timestamps, phase IDs, costs)."
    ),
    json_events: bool = typer.Option(
        False,
        "--json-events",
        help="Write one JSON line per ProgressEvent to stdout. Implies --attach.",
    ),
    dry_run: bool = typer.Option(False, "--dry-run"),
    open_in: Optional[str] = typer.Option(None, "--open"),
) -> None:
    """Refine an idea into investor-grade markdown deliverables."""
    idea = _resolve_idea(idea, from_file)
    profile_obj = load_profile(profile)
    run_id = make_run_id(name=name, idea=idea)
    workspace_path = resolve_workspace(
        name=name, workspace_arg=workspace, run_id=run_id
    )
    workspace_path.mkdir(parents=True, exist_ok=True)

    if json_events:
        attach = True

    if dry_run:
        _print_dry_run_estimate(profile_obj, depth)
        return

    _maybe_install_agents(profile_obj.source_dir)

    run_intake(
        workspace_path=workspace_path,
        profile=profile_obj,
        one_liner=idea,
        skip=skip_intake,
    )

    requested_flags: set[str] = set()
    if with_pitch:
        requested_flags.add("--with-pitch")
    if with_roadmap:
        requested_flags.add("--with-roadmap")
    if with_techstack:
        requested_flags.add("--with-techstack")

    printer = _make_printer(
        attach=attach,
        verbose=verbose,
        json_events=json_events,
        idea=idea,
        ws=workspace_path,
    )
    config = OrchestratorConfig(
        max_concurrent=max_concurrent,
        max_cost=max_cost,
        max_wall_clock_s=max_wall_clock,
        webhook_url=webhook,
        requested_flags=frozenset(requested_flags),
        progress_cb=printer.on_event if printer is not None else None,
    )

    if attach:
        if printer is not None:
            printer.on_run_start()
        state = run_orchestrator(workspace_path, profile_obj, config)
        if printer is not None:
            printer.on_run_end(state)
        else:
            typer.echo(f"Run complete: {workspace_path.name} (status={state.status})")
        if state.status == "auth_expired":
            raise typer.Exit(code=69)
    else:
        actual_run_id = daemonize(
            workspace_path,
            lambda: run_orchestrator(workspace_path, profile_obj, config),
        )
        typer.echo(actual_run_id)


_USER_PHASE_LABELS: dict[str, str] = {
    "0": "Reading your idea",
    "0.5": "Identifying the underlying job-to-be-done",
    "0.6": "Exploring alternative framings",
    "1": "Three specialists weighing in (architect, designer, market)",
    "1.5": "Finding disagreements across the specialists",
    "2.1": "Generating alternative branches where opinions diverge",
    "2.2": "Stress-testing each branch",
    "2.3": "Picking the strongest survivor of each branch",
    "2.5": "Distilling the workspace",
    "3": "Cross-domain critique and kill-case",
    "4": "Writing your final brief",
}

_PHASE_FAILURE_BLURBS: dict[str, str] = {
    "0.5": (
        "Lem couldn't extract a clear job-to-be-done from your idea.\n"
        "  This usually means the input is too abstract — try a more\n"
        "  concrete one-liner that names a real situation and outcome."
    ),
    "0.6": (
        "Lem couldn't produce a valid alternative framing of your idea.\n"
        "  This step is a known rough edge — output sometimes fails\n"
        "  the schema check on long, abstract ideas. Re-running often works."
    ),
    "1": (
        "One or more specialists couldn't analyze your idea.\n"
        "  Could be a transient model error or an idea framing the\n"
        "  specialists couldn't engage with."
    ),
    "1.5": (
        "Lem couldn't analyze the specialists' viewpoints for divergence.\n"
        "  Re-running usually works — model output varies between attempts."
    ),
    "2.1": "Lem couldn't generate alternative branches.",
    "2.2": "Lem couldn't stress-test the branches.",
    "2.3": "Lem couldn't pick a survivor among the branches.",
    "2.5": "Lem couldn't distill the workspace.",
    "3": "Lem couldn't run the cross-domain critique.",
    "4": (
        "Lem couldn't synthesize the final brief.\n"
        "  This is rare — usually a model timeout or schema mismatch.\n"
        "  The earlier phases' output is preserved in the workspace."
    ),
}


def _make_printer(
    *, attach: bool, verbose: bool, json_events: bool, idea: str, ws: Path
) -> "_Printer | None":
    if not attach:
        return None
    if json_events:
        return _JsonEventPrinter()
    if verbose:
        return _VerbosePrinter()
    return _UserPrinter(idea=idea, ws=ws)


class _Printer:
    def on_run_start(self) -> None: ...
    def on_event(self, event: ProgressEvent) -> None: ...
    def on_run_end(self, state: object) -> None: ...


class _VerbosePrinter(_Printer):
    def on_event(self, event: ProgressEvent) -> None:
        import time as _time

        ts = _time.strftime("%H:%M:%S")
        roles = ", ".join(event.roles) if event.roles else "—"
        if event.kind == "phase_start":
            typer.echo(f"[{ts}] phase {event.phase_id} → {roles} ...")
        elif event.kind == "phase_done":
            marker = "ok" if event.success else "FAIL"
            typer.echo(
                f"[{ts}] phase {event.phase_id} {marker} "
                f"{event.duration_s:.1f}s ${event.cost_usd:.4f}"
            )
        elif event.kind == "phase_skipped":
            typer.echo(f"[{ts}] phase {event.phase_id} skipped")

    def on_run_end(self, state: object) -> None:
        typer.echo(
            f"Run complete: {getattr(state, 'run_id', '?')} "
            f"(status={getattr(state, 'status', '?')})"
        )


class _JsonEventPrinter(_Printer):
    """Writes one JSON line per ProgressEvent to stdout for structured IPC."""

    def on_event(self, event: ProgressEvent) -> None:
        record = {
            "kind": event.kind,
            "phase_id": event.phase_id,
            "roles": list(event.roles),
            "duration_s": event.duration_s,
            "cost_usd": event.cost_usd,
            "success": event.success,
            "timestamp": time.time(),
        }
        sys.stdout.write(json.dumps(record) + "\n")
        sys.stdout.flush()


class _UserPrinter(_Printer):
    def __init__(self, *, idea: str, ws: Path) -> None:
        self._idea = idea
        self._ws = ws
        self._failed_phase_id: Optional[str] = None
        self._total_cost: float = 0.0

    def on_run_start(self) -> None:
        snippet = self._idea.strip().splitlines()[0] if self._idea else ""
        if len(snippet) > 80:
            snippet = snippet[:77] + "..."
        typer.echo(f'Refining: "{snippet}"')
        typer.echo("")

    def on_event(self, event: ProgressEvent) -> None:
        label = _USER_PHASE_LABELS.get(event.phase_id, f"Phase {event.phase_id}")
        if event.kind == "phase_start":
            typer.echo(f"  · {label}...")
        elif event.kind == "phase_done":
            self._total_cost += event.cost_usd
            duration = _format_duration(event.duration_s)
            if event.success:
                typer.echo(f"  ✓ {label}  ({duration})")
            else:
                self._failed_phase_id = event.phase_id
                typer.echo(f"  ✗ {label}  ({duration})")
        # phase_skipped: silent in user mode

    def on_run_end(self, state: object) -> None:
        status = getattr(state, "status", "")
        cost = getattr(state, "cost_so_far", self._total_cost)
        run_id = getattr(state, "run_id", self._ws.name)

        typer.echo("")
        if status == "completed":
            typer.echo(f"Done. Cost: ${cost:.2f} (notional).")
            typer.echo(f"View the brief:  lem show {run_id}")
            return

        typer.echo(f"Run did not finish — status: {status}")
        typer.echo("")
        typer.echo("What happened:")
        blurb = self._failure_blurb(state)
        for line in blurb.splitlines():
            typer.echo(f"  {line}")
        typer.echo("")
        typer.echo("What to do:")
        for line in self._recovery_steps(state):
            typer.echo(f"  {line}")
        typer.echo("")
        typer.echo(f"Cost so far: ${cost:.2f} (notional).")
        typer.echo(f"Workspace:   {self._ws}")

    def _failure_blurb(self, state: object) -> str:
        status = getattr(state, "status", "")
        error = getattr(state, "error", None) or ""
        if status == "wall-clock-aborted":
            return "The run hit the wall-clock limit before finishing."
        if status == "cost-aborted":
            return "The run hit the configured cost ceiling."
        if status == "cancelled":
            return "The run was cancelled."
        if "orchestrator crashed" in error:
            return (
                "Lem itself ran into an unexpected error.\n"
                "This is a bug — the underlying message is:\n"
                f"  {error}"
            )
        if self._failed_phase_id and self._failed_phase_id in _PHASE_FAILURE_BLURBS:
            return _PHASE_FAILURE_BLURBS[self._failed_phase_id]
        return error or "Unknown failure."

    def _recovery_steps(self, state: object) -> list[str]:
        status = getattr(state, "status", "")
        run_id = getattr(state, "run_id", self._ws.name)
        steps: list[str] = []
        if status not in {"cost-aborted", "cancelled"}:
            steps.append("1. Run again — model output varies between attempts.")
        if status == "cost-aborted":
            steps.append("1. Re-run with a higher --max-cost (or omit it on Max).")
        if status == "wall-clock-aborted":
            steps.append("1. Re-run with --max-wall-clock <seconds> for more time.")
        steps.append(f"2. Read the partial output: {self._ws}")
        steps.append(f"3. Resume / forensics:    lem watch {run_id} --once")
        return steps


def _format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.0f}s"
    minutes = int(seconds // 60)
    rem = int(seconds % 60)
    return f"{minutes}m{rem:02d}s"


def _resolve_idea(idea: Optional[str], from_file: Optional[Path]) -> str:
    if idea is not None and from_file is not None:
        raise typer.BadParameter(
            "Pass either an IDEA argument or --from-file, not both."
        )
    if from_file is not None:
        text = from_file.read_text().strip()
        if not text:
            raise typer.BadParameter(f"--from-file {from_file} is empty.")
        return text
    if idea is None:
        raise typer.BadParameter("Provide an IDEA argument or --from-file.")
    return idea


def _maybe_install_agents(profile_dir: Path) -> None:
    target = Path(".claude/agents")
    if target.is_dir() and any(target.iterdir()):
        return
    try:
        install_agents(profile_dir, target)
    except Exception:
        pass


def _print_dry_run_estimate(profile_obj: Profile, depth: str) -> None:
    depth_multipliers = {"quick": 0.5, "normal": 1.0, "deep": 2.0}
    multiplier = depth_multipliers.get(depth, 1.0)

    role_count = len(profile_obj.roles) + len(profile_obj.process_roles)
    notional_tokens_in = int(4000 * role_count * multiplier)
    notional_tokens_out = int(2000 * role_count * multiplier)

    from lem.state.cost import RATES
    sonnet_in, sonnet_out = RATES.get("sonnet", (0.000003, 0.000015))
    estimate_usd = notional_tokens_in * sonnet_in + notional_tokens_out * sonnet_out

    typer.echo(f"Dry-run estimate (depth={depth}, profile={profile_obj.name}):")
    typer.echo(f"  Roles: {role_count}")
    typer.echo(f"  Notional tokens in:  {notional_tokens_in:,}")
    typer.echo(f"  Notional tokens out: {notional_tokens_out:,}")
    typer.echo(f"  Estimated cost: ${estimate_usd:.4f} USD")
