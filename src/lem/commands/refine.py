"""`lem refine`."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Optional

import typer

from lem.daemon import daemonize
from lem.intake import run_intake
from lem.orchestrator import OrchestratorConfig, run_orchestrator
from lem.paths import make_run_id, resolve_workspace
from lem.profile import load_profile
from lem.types import Profile

app = typer.Typer()


@app.command()
def refine(
    idea: Annotated[str, typer.Argument(help="One-line description of the idea")],
    profile: str = typer.Option("app-idea", "--profile"),
    depth: str = typer.Option("normal", "--depth", help="quick|normal|deep"),
    model_tier: str = typer.Option("opus-heavy", "--model-tier"),
    max_cost: float = typer.Option(25.0, "--max-cost"),
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
    dry_run: bool = typer.Option(False, "--dry-run"),
    open_in: Optional[str] = typer.Option(None, "--open"),
) -> None:
    """Refine an idea into investor-grade markdown deliverables."""
    profile_obj = load_profile(profile)
    run_id = make_run_id(name=name, idea=idea)
    workspace_path = resolve_workspace(
        name=name, workspace_arg=workspace, run_id=run_id
    )
    workspace_path.mkdir(parents=True, exist_ok=True)

    if dry_run:
        _print_dry_run_estimate(profile_obj, depth)
        return

    run_intake(
        workspace_path=workspace_path,
        profile=profile_obj,
        one_liner=idea,
        skip=skip_intake,
    )

    config = OrchestratorConfig(
        max_concurrent=max_concurrent,
        max_cost=max_cost,
        max_wall_clock_s=max_wall_clock,
        webhook_url=webhook,
    )

    if attach:
        state = run_orchestrator(workspace_path, profile_obj, config)
        typer.echo(f"Run complete: {workspace_path.name} (status={state.status})")
    else:
        actual_run_id = daemonize(
            workspace_path,
            lambda: run_orchestrator(workspace_path, profile_obj, config),
        )
        typer.echo(actual_run_id)


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
