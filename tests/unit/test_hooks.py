# pyright: strict
"""Tests for src/lem/hooks.py — lifecycle hooks and webhook."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from lem.hooks import (
    HookConfig,
    fire_on_complete,
    fire_on_error,
    load_hook_config,
    post_webhook,
    run_hook,
)
from lem.types import RunState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_state(
    *,
    run_id: str = "test-run",
    workspace_path: Path | None = None,
    status: str = "completed",
    cost: float = 1.23,
    error: str | None = None,
) -> RunState:
    now = time.time()
    return RunState(
        run_id=run_id,
        workspace_path=workspace_path or Path("/tmp/ws"),
        phase="4",
        status=status,  # type: ignore[arg-type]
        started_at=now - 10.0,
        last_event_at=now,
        cost_so_far=cost,
        error=error,
    )


def _write_toml(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# load_hook_config — project config
# ---------------------------------------------------------------------------


def test_load_hook_config_project_toml(tmp_path: Path) -> None:
    toml = tmp_path / "lem.toml"
    _write_toml(toml, '[hooks]\non_complete = "/project/done.sh"\n')
    cfg = load_hook_config(tmp_path, user_config_path=Path("/nonexistent/config.toml"))
    assert cfg.on_complete == "/project/done.sh"
    assert cfg.on_error is None


def test_load_hook_config_user_toml(tmp_path: Path) -> None:
    user_cfg = tmp_path / "config.toml"
    _write_toml(user_cfg, '[hooks]\non_error = "/user/error.sh"\n')
    workspace = tmp_path / "ws"
    workspace.mkdir()
    cfg = load_hook_config(workspace, user_config_path=user_cfg)
    assert cfg.on_error == "/user/error.sh"
    assert cfg.on_complete is None


def test_load_hook_config_project_overrides_user(tmp_path: Path) -> None:
    user_cfg = tmp_path / "config.toml"
    _write_toml(user_cfg, '[hooks]\non_complete = "/user/done.sh"\non_error = "/user/error.sh"\n')
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write_toml(workspace / "lem.toml", '[hooks]\non_complete = "/project/done.sh"\n')
    cfg = load_hook_config(workspace, user_config_path=user_cfg)
    assert cfg.on_complete == "/project/done.sh"
    assert cfg.on_error == "/user/error.sh"


def test_load_hook_config_no_files(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    workspace.mkdir()
    cfg = load_hook_config(workspace, user_config_path=Path("/nonexistent/config.toml"))
    assert cfg == HookConfig()


def test_load_hook_config_empty_hooks_section(tmp_path: Path) -> None:
    toml = tmp_path / "lem.toml"
    _write_toml(toml, "[hooks]\n")
    cfg = load_hook_config(tmp_path, user_config_path=Path("/nonexistent/config.toml"))
    assert cfg == HookConfig()


# ---------------------------------------------------------------------------
# fire_on_complete — env vars
# ---------------------------------------------------------------------------


def test_fire_on_complete_passes_env_vars(tmp_path: Path) -> None:
    out_file = tmp_path / "env_out.txt"
    command = f"env | grep LEM_ > {out_file}"
    state = _make_state(run_id="my-run", workspace_path=tmp_path, cost=9.99)
    fire_on_complete(state, HookConfig(on_complete=command))
    output = out_file.read_text()
    assert "LEM_RUN_ID=my-run" in output
    assert "LEM_VERDICT=completed" in output
    assert "LEM_COST=9.99" in output
    assert "LEM_WORKSPACE=" in output
    assert "LEM_DURATION=" in output


def test_fire_on_complete_noop_when_not_configured(tmp_path: Path) -> None:
    state = _make_state()
    fire_on_complete(state, HookConfig())  # must not raise


def test_fire_on_error_passes_lem_error(tmp_path: Path) -> None:
    out_file = tmp_path / "env_out.txt"
    command = f"env | grep LEM_ > {out_file}"
    state = _make_state(status="failed", error="something went wrong")
    fire_on_error(state, HookConfig(on_error=command))
    output = out_file.read_text()
    assert "LEM_ERROR=something went wrong" in output


# ---------------------------------------------------------------------------
# run_hook — failure doesn't crash
# ---------------------------------------------------------------------------


def test_run_hook_failure_does_not_raise() -> None:
    result = run_hook("exit 1", env_overrides={})
    assert result.returncode == 1


def test_run_hook_timeout_does_not_raise() -> None:
    result = run_hook("sleep 10", env_overrides={}, timeout_s=1)
    assert result.returncode != 0


# ---------------------------------------------------------------------------
# post_webhook
# ---------------------------------------------------------------------------


def test_post_webhook_sends_correct_payload() -> None:
    state = _make_state(run_id="wh-run", cost=3.14, status="completed")
    captured: list[dict[str, Any]] = []

    class FakeResponse:
        status = 200

        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, *args: object) -> None:
            pass

    def fake_urlopen(req: Any, timeout: int = 10) -> FakeResponse:
        captured.append(json.loads(req.data))
        return FakeResponse()

    with patch("urllib.request.urlopen", fake_urlopen):
        post_webhook("http://example.com/hook", state)

    assert len(captured) == 1
    p = captured[0]
    assert p["run_id"] == "wh-run"
    assert p["status"] == "completed"
    assert p["verdict"] == "completed"
    assert p["cost"] == pytest.approx(3.14)
    assert "duration" in p
    assert "deliverables_path" in p


def test_post_webhook_retries_on_5xx() -> None:
    state = _make_state()
    call_count = 0

    class FakeResponse:
        def __init__(self, status: int) -> None:
            self.status = status

        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, *args: object) -> None:
            pass

    def fake_urlopen(req: Any, timeout: int = 10) -> FakeResponse:
        nonlocal call_count
        call_count += 1
        return FakeResponse(503)

    with patch("urllib.request.urlopen", fake_urlopen), patch("time.sleep"):
        post_webhook("http://example.com/hook", state, max_retries=3)

    assert call_count == 3


def test_post_webhook_stops_retrying_on_200() -> None:
    state = _make_state()
    call_count = 0

    class FakeResponse:
        status = 200

        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, *args: object) -> None:
            pass

    def fake_urlopen(req: Any, timeout: int = 10) -> FakeResponse:
        nonlocal call_count
        call_count += 1
        return FakeResponse()

    with patch("urllib.request.urlopen", fake_urlopen):
        post_webhook("http://example.com/hook", state, max_retries=3)

    assert call_count == 1


def test_post_webhook_error_does_not_raise() -> None:
    state = _make_state()

    def fake_urlopen(req: Any, timeout: int = 10) -> None:
        raise OSError("network down")

    with patch("urllib.request.urlopen", fake_urlopen), patch("time.sleep"):
        post_webhook("http://example.com/hook", state, max_retries=2)
