# pyright: strict
"""Live API smoke tests — gated by LEM_LIVE_TEST=1.

These tests consume real claude tokens and require:
  - claude CLI installed and authenticated
  - A Claude Max subscription or API key configured

Run with:
  LEM_LIVE_TEST=1 pytest tests/e2e/test_live_smoke.py -v
"""

from __future__ import annotations

import os

import pytest

from lem.orchestrator import OrchestratorConfig, run_orchestrator
from lem.profile import load_profile

_LIVE = os.environ.get("LEM_LIVE_TEST")
_SKIP = pytest.mark.skipif(
    not _LIVE,
    reason="set LEM_LIVE_TEST=1 to run (consumes real claude tokens)",
)


@_SKIP
def test_live_pipeline_completes_within_budget(tmp_path: pytest.TempPathFactory) -> None:
    """Smoke test against real claude CLI. Costs real tokens. Manual verification only."""
    from pathlib import Path

    workspace = Path(str(tmp_path)) / "workspace"
    workspace.mkdir()

    profile = load_profile("app-idea")
    state = run_orchestrator(
        workspace,
        profile,
        OrchestratorConfig(max_cost=5.0, max_wall_clock_s=600, max_concurrent=2),
    )

    assert state.status in ("completed", "cost-aborted", "wall-clock-aborted")
    if state.status == "completed":
        assert (workspace / "deliverables" / "executive-summary.md").exists()
        assert state.cost_so_far <= 5.0


@_SKIP
def test_live_cli_refine_command(tmp_path: pytest.TempPathFactory) -> None:
    """Smoke test for the lem refine CLI command end-to-end.

    Exercises the full CLI path including intake prompt handling.
    Costs real tokens.
    """
    import subprocess
    from pathlib import Path

    workspace = Path(str(tmp_path)) / "workspace"
    workspace.mkdir()

    result = subprocess.run(
        [
            "lem", "refine",
            "--workspace", str(workspace),
            "--max-cost", "5",
            "--attach",
            "an app that helps freelancers track billable hours",
        ],
        capture_output=True,
        text=True,
        timeout=600,
    )

    assert result.returncode in (0, 1), (
        f"lem refine exited {result.returncode}\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )
    summary = workspace / "deliverables" / "executive-summary.md"
    if result.returncode == 0:
        assert summary.exists(), "executive-summary.md not written on successful exit"
