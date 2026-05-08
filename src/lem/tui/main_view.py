# pyright: strict
"""Pipeline + active workers + recent + issues."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import ScrollableContainer, Vertical
from textual.widget import Widget
from textual.widgets import DataTable, Label, Static

from lem.failure.stalled import compute_role_medians, is_stalled
from lem.phases import PHASES
from lem.state.cost import read_cost, run_total
from lem.state.log import read_log
from lem.state.run_state import read_state
from lem.state.timeline import read_timeline
from lem.types import CostEvent, LogEvent, RunState


def _phase_pill(name: str, status: str) -> str:
    if status == "done":
        return f"[green]✓ {name}[/green]"
    if status == "current":
        return f"[bold cyan]{name}[/bold cyan]"
    if status == "skipped":
        return f"[dim]— {name}[/dim]"
    return f"[dim]{name}[/dim]"


def _fmt_elapsed(seconds: float) -> str:
    m = int(seconds) // 60
    s = int(seconds) % 60
    return f"{m}m{s:02d}s" if m else f"{s}s"


def _build_pipeline_text(current_phase: str, completed_phases: set[str]) -> str:
    parts: list[str] = []
    found_current = False
    seen: set[str] = set()
    # Dedupe by name so the user sees one pill per logical phase even when the
    # pipeline has multiple sub-phases with the same display name (e.g. Explore
    # 2.1 / 2.2 / 2.3).
    for spec in PHASES:
        if spec.name in seen:
            continue
        seen.add(spec.name)
        if spec.name in completed_phases:
            parts.append(_phase_pill(spec.name, "done"))
        elif spec.name == current_phase and not found_current:
            found_current = True
            parts.append(_phase_pill(spec.name, "current"))
        else:
            parts.append(_phase_pill(spec.name, "pending"))
    return " → ".join(parts)


def _count_issues(events: list[LogEvent]) -> tuple[int, int, int]:
    retries = sum(1 for e in events if e.event == "worker_retry")
    timeouts = sum(1 for e in events if e.event == "worker_timeout")
    trips = sum(1 for e in events if e.event == "breaker_tripped")
    return retries, timeouts, trips


def _aggregate_workers(
    events: list[CostEvent],
) -> dict[str, dict[str, Any]]:
    """Build per-role aggregated token/cost info from cost events."""
    workers: dict[str, dict[str, Any]] = {}
    for e in events:
        key = f"{e.phase}/{e.role}"
        if key not in workers:
            workers[key] = {
                "role": e.role,
                "model": e.model,
                "tokens_in": 0,
                "tokens_out": 0,
                "cost_usd": 0.0,
                "last_ts": e.timestamp,
            }
        workers[key]["tokens_in"] += e.tokens_in
        workers[key]["tokens_out"] += e.tokens_out
        workers[key]["cost_usd"] += e.cost_usd
        if e.timestamp > workers[key]["last_ts"]:
            workers[key]["last_ts"] = e.timestamp
    return workers


class PipelineBar(Static):
    """Single-line pipeline phase display."""

    def __init__(self, workspace_path: Path) -> None:
        super().__init__("")
        self._workspace_path = workspace_path

    def refresh_data(self, state: RunState, completed_phases: set[str]) -> None:
        text = _build_pipeline_text(state.phase, completed_phases)
        self.update(text)


class WorkersTable(Widget):
    """Active workers grid."""

    DEFAULT_CSS = """
    WorkersTable {
        height: auto;
        max-height: 12;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._table: DataTable[str] | None = None  # pyright: ignore[reportPrivateUsage]

    def compose(self) -> ComposeResult:
        table: DataTable[str] = DataTable(show_cursor=False, zebra_stripes=True)  # pyright: ignore[reportUnknownVariableType]
        table.add_column("Role", width=20)
        table.add_column("Model", width=8)
        table.add_column("Elapsed", width=9)
        table.add_column("Tok in", width=8)
        table.add_column("Tok out", width=8)
        table.add_column("Activity", width=30)
        self._table = table
        yield table

    def refresh_data(
        self,
        active: list[dict[str, Any]],
        medians: dict[str, float],
        now: float,
    ) -> None:
        if self._table is None:
            return
        self._table.clear()
        for w in active:
            role: str = w.get("role", "")
            model: str = w.get("model", "")
            started: float = float(w.get("started_at", now))
            elapsed = now - started
            tokens_in: int = int(w.get("tokens_in", 0))
            tokens_out: int = int(w.get("tokens_out", 0))
            activity: str = w.get("activity", "")
            check = is_stalled(role=role, elapsed_s=elapsed, medians=medians)
            role_text = Text(role)
            if check.stalled:
                role_text.stylize("bold yellow")
            self._table.add_row(
                role_text,  # pyright: ignore[reportArgumentType] # rich Text accepted at runtime
                model,
                _fmt_elapsed(elapsed),
                str(tokens_in),
                str(tokens_out),
                activity[:30],
            )


class RecentList(ScrollableContainer):
    """Last 10 completed workers."""

    def __init__(self) -> None:
        super().__init__()
        self._label = Static("")
        self._items: list[str] = []

    def compose(self) -> ComposeResult:
        yield Label("[bold]Recent completions[/bold]")
        yield self._label

    def refresh_data(self, completed: list[dict[str, Any]]) -> None:
        recent = completed[-10:]
        lines = [
            f"  {w.get('role', '?')} ({w.get('phase', '?')}) "
            f"— {_fmt_elapsed(float(w.get('duration_s', 0.0)))}"
            for w in recent
        ]
        self._label.update("\n".join(lines) if lines else "[dim]none[/dim]")


class IssuesLine(Static):
    """Single-line issues summary."""

    def refresh_data(self, retries: int, timeouts: int, trips: int) -> None:
        self.update(
            f"retries: {retries} | timeouts: {timeouts} | breaker_trips: {trips}"
        )


class TokensLine(Static):
    """Token and optional cost display."""

    def __init__(self, show_cost: bool) -> None:
        super().__init__("")
        self._show_cost = show_cost

    def refresh_data(self, tokens_in: int, tokens_out: int, cost: float) -> None:
        parts = [f"tokens in: {tokens_in:,} | tokens out: {tokens_out:,}"]
        if self._show_cost:
            parts.append(f"cost: ${cost:.4f}")
        self.update(" | ".join(parts))


class MainView(Vertical):
    """Composite view: pipeline + workers + completions + issues + tokens."""

    def __init__(self, workspace_path: Path, *, show_cost: bool = False) -> None:
        super().__init__()
        self._workspace_path = workspace_path
        self._show_cost = show_cost
        self._pipeline_bar = PipelineBar(workspace_path)
        self._workers_table = WorkersTable()
        self._recent_list = RecentList()
        self._issues_line = IssuesLine("")
        self._tokens_line = TokensLine(show_cost)

    def compose(self) -> ComposeResult:
        yield Label("[bold]Pipeline[/bold]")
        yield self._pipeline_bar
        yield Label("[bold]Active Workers[/bold]")
        yield self._workers_table
        yield self._recent_list
        yield Label("[bold]Issues[/bold]")
        yield self._issues_line
        yield Label("[bold]Tokens[/bold]")
        yield self._tokens_line

    def on_mount(self) -> None:
        self.refresh_data()

    def refresh_data(self) -> None:
        try:
            state = read_state(self._workspace_path)
        except FileNotFoundError:
            return

        now = time.time()
        log_events = list(read_log(self._workspace_path))
        cost_events = list(read_cost(self._workspace_path))
        timeline_events = list(read_timeline(self._workspace_path))

        completed_phases = {e.phase for e in timeline_events}
        # Workers active = in cost events but not yet in timeline
        workers_by_role = _aggregate_workers(cost_events)

        # Determine active vs completed from timeline
        finished_keys = {f"{e.phase}/{e.role}" for e in timeline_events}
        active_workers: list[dict[str, Any]] = []
        completed_workers: list[dict[str, Any]] = []

        for key, w in workers_by_role.items():
            if key in finished_keys:
                matched = next(
                    (e for e in timeline_events if f"{e.phase}/{e.role}" == key), None
                )
                completed_workers.append({
                    **w,
                    "duration_s": matched.duration_s if matched else 0.0,
                    "phase": key.split("/")[0],
                })
            else:
                active_workers.append({
                    **w,
                    "started_at": w.get("last_ts", now),
                    "activity": state.phase,
                })

        medians: dict[str, float] = compute_role_medians(
            self._workspace_path.parent
        )

        retries, timeouts, trips = _count_issues(log_events)
        total_in = sum(e.tokens_in for e in cost_events)
        total_out = sum(e.tokens_out for e in cost_events)
        total_cost = run_total(self._workspace_path)

        self._pipeline_bar.refresh_data(state, completed_phases)
        self._workers_table.refresh_data(active_workers, medians, now)
        self._recent_list.refresh_data(completed_workers)
        self._issues_line.refresh_data(retries, timeouts, trips)
        self._tokens_line.refresh_data(total_in, total_out, total_cost)
