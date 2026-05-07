# pyright: strict
"""Terminal bell + osascript/notify-send OS notifications."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys

from lem.types import RunState


def notify(state: RunState, *, force: bool = False) -> None:
    """Fire OS notification + terminal bell on run completion/error.

    Only fires when LEM_NOTIFY=1 or force=True.
    """
    if not force and os.environ.get("LEM_NOTIFY") != "1":
        return
    title, message = _make_message(state)
    _send_notification(title, message)


def _make_message(state: RunState) -> tuple[str, str]:
    if state.status == "completed":
        title = "lem run completed"
    else:
        title = "lem run failed"
    message = f"{state.run_id} — {state.status}"
    return title, message


def _send_notification(title: str, message: str) -> None:
    if sys.platform == "darwin" and shutil.which("osascript"):
        _osascript(title, message)
    elif sys.platform.startswith("linux") and shutil.which("notify-send"):
        _notify_send(title, message)
    else:
        _bell()


def _osascript(title: str, message: str) -> None:
    script = f'display notification "{message}" with title "{title}"'
    try:
        subprocess.run(["osascript", "-e", script], check=False, capture_output=True)
    except Exception:
        _bell()


def _notify_send(title: str, message: str) -> None:
    try:
        subprocess.run(
            ["notify-send", title, message], check=False, capture_output=True
        )
    except Exception:
        _bell()


def _bell() -> None:
    if sys.stderr.isatty():
        sys.stderr.write("\a")
        sys.stderr.flush()
