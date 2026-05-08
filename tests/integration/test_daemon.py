# pyright: basic
"""Integration tests for POSIX double-fork daemonize()."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest


def _make_driver(workspace: Path, grandchild_body: str) -> Path:
    """Write a small driver script that calls daemonize() with custom grandchild work."""
    driver = workspace / "driver.py"
    driver.write_text(
        f"""
import sys, os
from pathlib import Path
sys.path.insert(0, {repr(str(Path(__file__).parent.parent.parent / "src"))})
from lem.daemon import daemonize

def grandchild_work():
{grandchild_body}

run_id = daemonize(Path({repr(str(workspace))}), grandchild_work)
print(run_id, flush=True)
"""
    )
    return driver


# ---------------------------------------------------------------------------
# 1. run-id printed to stdout, parent exits 0
# ---------------------------------------------------------------------------


def test_run_id_printed_and_parent_exits_zero(tmp_path: Path) -> None:
    workspace = tmp_path / "2026-05-06-1200-myidea-abc123"
    workspace.mkdir()

    driver = _make_driver(workspace, "    pass\n")
    result = subprocess.run(
        [sys.executable, str(driver)],
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 0
    assert result.stdout.strip() == workspace.name


# ---------------------------------------------------------------------------
# 2. Grandchild survives parent exit
# ---------------------------------------------------------------------------


def test_grandchild_survives_parent_exit(tmp_path: Path) -> None:
    workspace = tmp_path / "run-survives"
    workspace.mkdir()
    status_file = workspace / "status.txt"

    grandchild_body = f"""
    import time
    Path({repr(str(status_file))}).write_text("RUNNING")
    time.sleep(2)
    Path({repr(str(status_file))}).write_text("DONE")
"""
    driver = _make_driver(workspace, grandchild_body)

    proc = subprocess.Popen(
        [sys.executable, str(driver)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    # Driver (parent) should exit quickly — well before grandchild finishes
    proc.wait(timeout=5)
    assert proc.returncode == 0

    # Poll until grandchild writes "DONE" (max ~4s)
    deadline = time.monotonic() + 4.0
    while time.monotonic() < deadline:
        if status_file.exists() and status_file.read_text() == "DONE":
            break
        time.sleep(0.1)

    assert status_file.exists(), "grandchild never wrote status file"
    assert status_file.read_text() == "DONE", "grandchild did not finish after parent exited"


# ---------------------------------------------------------------------------
# 3. stdout/stderr redirected to meta/log.jsonl
# ---------------------------------------------------------------------------


def test_stdio_redirected_to_log(tmp_path: Path) -> None:
    workspace = tmp_path / "run-log"
    workspace.mkdir()
    log_path = workspace / "meta" / "log.jsonl"
    done_marker = workspace / "done.txt"

    grandchild_body = f"""
    import sys, time
    print("HELLO_STDOUT", flush=True)
    print("HELLO_STDERR", file=sys.stderr, flush=True)
    time.sleep(0.1)
    from pathlib import Path
    Path({repr(str(done_marker))}).write_text("done")
"""
    driver = _make_driver(workspace, grandchild_body)

    proc = subprocess.run(
        [sys.executable, str(driver)],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert proc.returncode == 0

    # Wait for grandchild to finish writing
    deadline = time.monotonic() + 4.0
    while time.monotonic() < deadline:
        if done_marker.exists():
            break
        time.sleep(0.1)

    assert log_path.exists(), "log.jsonl not created"
    log_content = log_path.read_text()
    assert "HELLO_STDOUT" in log_content
    assert "HELLO_STDERR" in log_content


# ---------------------------------------------------------------------------
# 4. stdin redirected to /dev/null
# ---------------------------------------------------------------------------


def test_stdin_redirected_to_devnull(tmp_path: Path) -> None:
    workspace = tmp_path / "run-stdin"
    workspace.mkdir()
    result_file = workspace / "stdin_content.txt"

    grandchild_body = f"""
    import sys
    from pathlib import Path
    data = sys.stdin.read()
    Path({repr(str(result_file))}).write_text(repr(data))
"""
    driver = _make_driver(workspace, grandchild_body)

    proc = subprocess.run(
        [sys.executable, str(driver)],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert proc.returncode == 0

    deadline = time.monotonic() + 4.0
    while time.monotonic() < deadline:
        if result_file.exists():
            break
        time.sleep(0.1)

    assert result_file.exists(), "grandchild never wrote stdin_content.txt"
    # stdin.read() on /dev/null returns empty string
    assert result_file.read_text() == repr(""), f"unexpected stdin content: {result_file.read_text()}"


# ---------------------------------------------------------------------------
# 5. Non-POSIX raises NotImplementedError
# ---------------------------------------------------------------------------


def test_non_posix_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr("os.name", "nt")

    from lem.daemon import daemonize

    with pytest.raises(NotImplementedError, match="POSIX"):
        daemonize(tmp_path / "run-nt", lambda: None)
