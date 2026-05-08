"""claude -p subprocess wrapper.

DECISION – prompt assembly: workspace files are inlined into the user-prompt as
fenced markdown sections under a "READ-ONLY context" header. Each file appears as:

    ## File: <relative-or-absolute-path>
    ```
    <file contents>
    ```

Extra-context entries follow as:

    ## extra_context.<key>
    <value>

A separator line ("---") divides the context block from the task instruction.

DECISION – model precedence: WorkerInvocation.model is authoritative. The role's
default model is resolved before invoke() is called (orchestrator responsibility).

DECISION – max-output-tokens: claude CLI has no --max-output-tokens flag. The cap
is enforced via the role's system prompt and the dispatch layer's wall-clock timeout.
invoke() passes max_output_tokens to the user prompt as an informational note so the
model can self-limit.

DECISION – claude binary discovery: PATH lookup by default; overridable via
LEM_CLAUDE_BIN env var.

DECISION – --system-prompt flag: the full role body is passed as the system prompt
(replacing the default). --append-system-prompt appends to the default; --system-prompt
replaces it entirely, which is what we want for role isolation.
"""

from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
from pathlib import Path
from typing import Any, Literal

from lem.failure.timeout import run_with_escalation
from lem.types import WorkerInvocation, WorkerResult

_AUTH_EXIT_CODE = 69
_StopReason = Literal["end_turn", "max_tokens", "timeout", "error"]
_TIMEOUT_RETURNCODES = frozenset({-signal.SIGTERM, -signal.SIGKILL})


def invoke(
    inv: WorkerInvocation,
    system_prompt: str,
    allowed_tools: list[str],
) -> WorkerResult:
    """Run claude -p for the given invocation; write output_path atomically.

    The orchestrator is responsible for pre-extracting system_prompt and
    allowed_tools from the role file before calling this function.
    """
    if os.environ.get("LEM_STUB_MODE"):
        stub_dir_env = os.environ.get("LEM_STUB_MODE_DIR")
        return _stub_invoke(
            inv, stub_dir=Path(stub_dir_env) if stub_dir_env else None
        )

    user_prompt = _build_user_prompt(inv)
    cmd = _build_command(inv, system_prompt, allowed_tools)

    proc = run_with_escalation(
        cmd,
        timeout_s=inv.timeout_s,
        input=user_prompt,
        cwd=inv.workspace_path,
    )

    if proc.returncode in _TIMEOUT_RETURNCODES:
        return WorkerResult(
            exit_code=-1,
            output_path=inv.output_path,
            tokens_in=0,
            tokens_out=0,
            cost_usd=0.0,
            duration_s=float(inv.timeout_s),
            stop_reason="timeout",
            schema_valid=False,
            schema_errors=[],
        )

    if proc.returncode == _AUTH_EXIT_CODE:
        return WorkerResult(
            exit_code=_AUTH_EXIT_CODE,
            output_path=inv.output_path,
            tokens_in=0,
            tokens_out=0,
            cost_usd=0.0,
            duration_s=0.0,
            stop_reason="error",
            schema_valid=False,
            schema_errors=["claude auth error"],
        )

    return _parse_result(proc, inv)


def _build_command(
    inv: WorkerInvocation,
    system_prompt: str,
    allowed_tools: list[str],
) -> list[str]:
    binary = _find_claude_binary()
    cmd: list[str] = [
        binary,
        "--print",
        "--output-format", "json",
        "--model", inv.model,
        "--system-prompt", system_prompt,
        "--no-session-persistence",
    ]
    if allowed_tools:
        cmd += ["--allowedTools"] + allowed_tools
    return cmd


def _build_user_prompt(inv: WorkerInvocation) -> str:
    parts: list[str] = []

    if inv.allowed_read_paths:
        parts.append(
            "You have READ-ONLY access to the following workspace files. "
            "Treat them as context, not content to modify.\n"
        )
        for path in inv.allowed_read_paths:
            if not path.exists():
                raise FileNotFoundError(
                    f"allowed_read_path does not exist: {path}"
                )
            contents = path.read_text(encoding="utf-8")
            parts.append(f"## File: {path}\n```\n{contents}\n```\n")

    if inv.extra_context:
        for key, value in inv.extra_context.items():
            parts.append(f"## extra_context.{key}\n{value}\n")

    if parts:
        parts.append("---\n\n(end of context — your task instructions follow)\n\n")

    parts.append(
        "Respond with your final output as your message text — exactly the "
        "file contents, with no surrounding code fences (no leading ```...``` "
        "wrapper), no commentary before or after, and no Write/Edit/file-writing "
        "tools. The first line of your response must be the first line of the "
        "file. lem will save your response to disk verbatim. "
        f"Limit your response to {inv.max_output_tokens} tokens."
    )

    return "\n".join(parts)


def _parse_result(
    proc: subprocess.CompletedProcess[str], inv: WorkerInvocation
) -> WorkerResult:
    try:
        envelope: dict[str, Any] = json.loads(proc.stdout)
    except (json.JSONDecodeError, ValueError):
        return WorkerResult(
            exit_code=proc.returncode if proc.returncode != 0 else 1,
            output_path=inv.output_path,
            tokens_in=0,
            tokens_out=0,
            cost_usd=0.0,
            duration_s=0.0,
            stop_reason="error",
            schema_valid=False,
            schema_errors=["malformed JSON envelope from claude"],
        )

    usage = envelope.get("usage") or {}
    raw_stop = envelope.get("stop_reason", "error")
    stop_reason: _StopReason
    if raw_stop in ("end_turn", "max_tokens", "timeout", "error"):
        stop_reason = raw_stop
    elif proc.returncode != 0:
        stop_reason = "error"
    else:
        stop_reason = "end_turn"

    result_text: str = envelope.get("result") or ""
    result_text = _strip_outer_code_fence(result_text)

    if result_text:
        _write_atomic(inv.output_path, result_text)

    return WorkerResult(
        exit_code=proc.returncode,
        output_path=inv.output_path,
        tokens_in=int(usage.get("input_tokens", 0)),
        tokens_out=int(usage.get("output_tokens", 0)),
        cost_usd=float(envelope.get("total_cost_usd", 0.0)),
        duration_s=float(envelope.get("duration_ms", 0)) / 1000.0,
        stop_reason=stop_reason,
        schema_valid=False,
        schema_errors=[],
    )


def _stub_invoke(inv: WorkerInvocation, stub_dir: Path | None) -> WorkerResult:
    """Stub mode: read canned output by role name and write it to output_path."""
    role_name = inv.role_path.stem
    if stub_dir is None:
        # Default: canned-outputs dir relative to the profile source dir is unknown
        # here; fall back to a generic placeholder that passes any schema.
        content = f"## Stub output\n\nStub content for role: {role_name}\n"
    else:
        canned = stub_dir / f"{role_name}.md"
        if canned.exists():
            content = canned.read_text(encoding="utf-8")
        else:
            content = f"## Stub output\n\nStub content for role: {role_name}\n"
    _write_atomic(inv.output_path, content)
    return WorkerResult(
        exit_code=0,
        output_path=inv.output_path,
        tokens_in=100,
        tokens_out=200,
        cost_usd=0.01,
        duration_s=0.05,
        stop_reason="end_turn",
        schema_valid=False,
        schema_errors=[],
    )


def _strip_outer_code_fence(text: str) -> str:
    """If the whole response is wrapped in a single ```...``` fence, unwrap it.

    Models sometimes return structured markdown wrapped in a code fence
    (`` ```markdown\\n<content>\\n``` ``). When that happens line 1 is the
    fence, not the file's first real line, and the schema parser rejects the
    output. Strip the fence iff the response opens with ``` on its first
    non-empty line and the matching closing ``` appears at end of text.
    """
    stripped = text.strip()
    if not stripped.startswith("```"):
        return text

    lines = stripped.splitlines()
    if len(lines) < 2 or not lines[-1].startswith("```"):
        return text

    return "\n".join(lines[1:-1]) + "\n"


def _write_atomic(output_path: Path, text: str) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = output_path.with_suffix(output_path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, output_path)


def _find_claude_binary() -> str:
    override = os.environ.get("LEM_CLAUDE_BIN")
    if override:
        return override
    binary = shutil.which("claude")
    if binary is None:
        raise RuntimeError("claude CLI not found in PATH; set LEM_CLAUDE_BIN")
    return binary
