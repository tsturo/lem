"""Verify that every lem module is importable as a stub placeholder."""

import importlib

import pytest

MODULES = [
    "lem",
    "lem.cli",
    "lem.types",
    "lem.paths",
    "lem.auth",
    "lem.intake",
    "lem.orchestrator",
    "lem.daemon",
    "lem.phases",
    "lem.profile",
    "lem.control",
    "lem.hooks",
    "lem.notify",
    "lem.workers",
    "lem.workers.cli_worker",
    "lem.workers.dispatch",
    "lem.schema",
    "lem.schema.parser",
    "lem.schema.validator",
    "lem.state",
    "lem.state.run_state",
    "lem.state.events",
    "lem.state.cost",
    "lem.state.timeline",
    "lem.state.log",
    "lem.failure",
    "lem.failure.timeout",
    "lem.failure.retry",
    "lem.failure.breaker",
    "lem.failure.ceiling",
    "lem.failure.stalled",
    "lem.render",
    "lem.render.report",
    "lem.tui",
    "lem.tui.app",
    "lem.tui.main_view",
    "lem.tui.worker_view",
    "lem.tui.phase_view",
    "lem.tui.artifact_view",
    "lem.tui.logs_view",
    "lem.tui.tree_view",
    "lem.tui.controls",
    "lem.commands",
    "lem.commands.refine",
    "lem.commands.watch",
    "lem.commands.list",
    "lem.commands.show",
    "lem.commands.logs",
    "lem.commands.rerun",
    "lem.commands.cancel",
    "lem.commands.render",
]


@pytest.mark.parametrize("module", MODULES)
def test_module_importable(module: str) -> None:
    importlib.import_module(module)
