# pyright: strict
"""POSIX double-fork detach."""

from __future__ import annotations

import os
import sys
from collections.abc import Callable
from pathlib import Path


def daemonize(workspace_path: Path, run_fn: Callable[[], object]) -> str:
    """Fork the calling process into a detached daemon.

    The parent (original caller) prints the run-id to stdout and returns.
    The detached grandchild runs run_fn() and exits.

    Returns the run-id string.
    Raises NotImplementedError on non-POSIX (Windows).

    WHY double-fork?
    Fork 1 lets us call setsid() in the child to create a new session with no
    controlling terminal.  But a session leader *can* re-acquire a controlling
    terminal, so fork 2 produces a grandchild that is not a session leader and
    therefore can never acquire one.  The intermediate child exits immediately,
    which also means the original parent can waitpid() on it and avoid zombies.
    """
    if os.name != "posix":
        raise NotImplementedError("daemonize requires POSIX")

    run_id = workspace_path.name

    child_pid = os.fork()
    if child_pid > 0:
        # Original parent: wait for the intermediate child to exit (no zombie),
        # then return to the caller with the run-id.
        os.waitpid(child_pid, 0)
        return run_id

    # --- intermediate child ---
    os.setsid()  # new session, no controlling terminal

    grandchild_pid = os.fork()
    if grandchild_pid > 0:
        # Intermediate child exits so the grandchild is re-parented to init.
        os._exit(0)

    # --- grandchild (the actual daemon) ---
    os.umask(0)
    _redirect_stdio(workspace_path)

    result = run_fn()
    exit_code = int(result) if isinstance(result, int) else 0
    os._exit(exit_code)


def _redirect_stdio(workspace_path: Path) -> None:
    null_fd = os.open("/dev/null", os.O_RDONLY)
    os.dup2(null_fd, sys.stdin.fileno())
    os.close(null_fd)

    log_path = workspace_path / "meta" / "log.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_fd = os.open(str(log_path), os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
    os.dup2(log_fd, sys.stdout.fileno())
    os.dup2(log_fd, sys.stderr.fileno())
    os.close(log_fd)
