# pyright: strict
"""on_complete, on_error shell hooks and webhook posting."""

from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from lem.types import RunState


@dataclass(frozen=True)
class HookConfig:
    on_complete: str | None = None
    on_error: str | None = None


def load_hook_config(
    workspace_path: Path | None = None,
    *,
    user_config_path: Path | None = None,
) -> HookConfig:
    """Read project lem.toml then user config. Project keys override user keys."""
    user_cfg = _read_toml_hooks(_resolve_user_config_path(user_config_path))
    project_cfg = _read_toml_hooks(_resolve_project_config_path(workspace_path))
    return HookConfig(
        on_complete=project_cfg.get("on_complete") or user_cfg.get("on_complete"),
        on_error=project_cfg.get("on_error") or user_cfg.get("on_error"),
    )


def run_hook(
    command: str,
    *,
    env_overrides: dict[str, str],
    timeout_s: int = 30,
) -> subprocess.CompletedProcess[str]:
    """Run a hook shell command with env overrides. Logs failures but does not raise."""
    import os
    env = {**os.environ, **env_overrides}
    try:
        return subprocess.run(
            command,
            shell=True,
            env=env,
            timeout=timeout_s,
            text=True,
            capture_output=True,
        )
    except Exception as exc:
        print(f"hook failed: {exc}", file=sys.stderr)
        return subprocess.CompletedProcess(
            command, returncode=1, stdout="", stderr=str(exc)
        )


def fire_on_complete(state: RunState, config: HookConfig) -> None:
    """Run on_complete hook with standard LEM_* env vars."""
    if not config.on_complete:
        return
    run_hook(config.on_complete, env_overrides=_base_env(state), timeout_s=30)


def fire_on_error(state: RunState, config: HookConfig) -> None:
    """Run on_error hook with standard LEM_* env vars plus LEM_ERROR."""
    if not config.on_error:
        return
    env = {**_base_env(state), "LEM_ERROR": state.error or ""}
    run_hook(config.on_error, env_overrides=env, timeout_s=30)


def post_webhook(
    url: str,
    state: RunState,
    *,
    timeout_s: int = 10,
    max_retries: int = 3,
) -> None:
    """POST run summary to webhook URL with retry on 5xx. Errors logged, not raised."""
    payload: dict[str, object] = {
        "run_id": state.run_id,
        "verdict": state.status,
        "cost": state.cost_so_far,
        "duration": state.last_event_at - state.started_at,
        "deliverables_path": str(state.workspace_path / "deliverables"),
        "status": state.status,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}
    )
    delay = 1
    for attempt in range(max_retries):
        try:
            resp = urllib.request.urlopen(req, timeout=timeout_s)
            status_code: int = getattr(resp, "status", 200)
            if status_code < 500:
                return
            print(f"webhook {status_code} on attempt {attempt + 1}", file=sys.stderr)
        except Exception as exc:
            print(f"webhook error on attempt {attempt + 1}: {exc}", file=sys.stderr)
        if attempt < max_retries - 1:
            time.sleep(delay)
            delay *= 2


def _base_env(state: RunState) -> dict[str, str]:
    return {
        "LEM_RUN_ID": state.run_id,
        "LEM_WORKSPACE": str(state.workspace_path),
        "LEM_VERDICT": state.status,
        "LEM_COST": str(state.cost_so_far),
        "LEM_DURATION": str(state.last_event_at - state.started_at),
    }


def _resolve_user_config_path(override: Path | None) -> Path:
    if override is not None:
        return override
    return Path.home() / ".config" / "lem" / "config.toml"


def _resolve_project_config_path(workspace_path: Path | None) -> Path:
    search_start = workspace_path or Path.cwd()
    for candidate in [search_start, *search_start.parents]:
        p = candidate / "lem.toml"
        if p.exists():
            return p
        if (candidate / ".lem").is_dir():
            p2 = candidate / "lem.toml"
            if p2.exists():
                return p2
    return search_start / "lem.toml"


def _read_toml_hooks(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    try:
        import tomllib  # Python 3.11+
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        hooks = data.get("hooks", {})
        return {k: str(v) for k, v in hooks.items() if isinstance(v, str)}
    except Exception as exc:
        print(f"failed to read {path}: {exc}", file=sys.stderr)
        return {}
