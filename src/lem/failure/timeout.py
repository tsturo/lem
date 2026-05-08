# pyright: strict
"""SIGTERM-then-SIGKILL with grace."""

from __future__ import annotations

import os
import signal
import subprocess
import threading
from collections.abc import Mapping
from pathlib import Path


def run_with_escalation(
    cmd: list[str],
    *,
    timeout_s: int,
    grace_s: int = 10,
    input: str | None = None,
    cwd: Path | None = None,
    env: Mapping[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run cmd; on timeout send SIGTERM, then SIGKILL after grace_s.

    Returns CompletedProcess with stdout/stderr/returncode.
    On SIGTERM-terminated process: returncode == -signal.SIGTERM
    On SIGKILL-terminated process: returncode == -signal.SIGKILL
    Callers detect timeout via negative returncode.
    """
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=cwd,
        env=dict(env) if env is not None else None,
        start_new_session=True,
    )

    timed_out = threading.Event()

    def _escalate() -> None:
        timed_out.set()
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        except ProcessLookupError:
            return
        try:
            proc.wait(timeout=grace_s)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except ProcessLookupError:
                pass

    timer = threading.Timer(timeout_s, _escalate)
    timer.start()
    try:
        stdout, stderr = proc.communicate(
            input=input,
            timeout=timeout_s + grace_s + 5,
        )
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except ProcessLookupError:
            pass
        stdout, stderr = proc.communicate()
    finally:
        timer.cancel()

    return subprocess.CompletedProcess(
        args=cmd,
        returncode=proc.returncode,
        stdout=stdout,
        stderr=stderr,
    )
