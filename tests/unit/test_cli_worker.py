"""Tests for src/lem/workers/cli_worker.py."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from lem.types import WorkerInvocation, WorkerResult
from lem.workers import cli_worker

STUBS = Path(__file__).parent.parent / "fixtures" / "claude_stubs"


def make_invocation(
    tmp_path: Path,
    *,
    model: str = "sonnet",
    output_path: Path | None = None,
    allowed_read_paths: list[Path] | None = None,
    extra_context: dict[str, str] | None = None,
    max_output_tokens: int = 1024,
    timeout_s: int = 30,
) -> WorkerInvocation:
    return WorkerInvocation(
        role_path=tmp_path / "role.md",
        workspace_path=tmp_path,
        output_path=output_path or tmp_path / "output.json",
        allowed_read_paths=allowed_read_paths or [],
        model=model,  # type: ignore[arg-type]
        max_output_tokens=max_output_tokens,
        timeout_s=timeout_s,
        extra_context=extra_context or {},
    )


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_happy_path_returns_populated_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LEM_CLAUDE_BIN", str(STUBS / "claude_success"))
    inv = make_invocation(tmp_path)
    result = cli_worker.invoke(inv, system_prompt="You are a test assistant.", allowed_tools=[])

    assert isinstance(result, WorkerResult)
    assert result.stop_reason == "end_turn"
    assert result.exit_code == 0
    assert result.tokens_in == 10
    assert result.tokens_out == 5
    assert result.cost_usd == pytest.approx(0.001)
    assert result.duration_s == pytest.approx(0.5)
    assert result.schema_valid is False
    assert result.schema_errors == []


def test_happy_path_output_file_written(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LEM_CLAUDE_BIN", str(STUBS / "claude_success"))
    inv = make_invocation(tmp_path)
    cli_worker.invoke(inv, system_prompt="You are a test assistant.", allowed_tools=[])

    assert inv.output_path.exists()
    assert inv.output_path.read_text(encoding="utf-8") == "Hello from stub"


def test_atomic_write_no_tmp_file_left(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LEM_CLAUDE_BIN", str(STUBS / "claude_success"))
    inv = make_invocation(tmp_path)
    cli_worker.invoke(inv, system_prompt="system", allowed_tools=[])

    tmp_file = inv.output_path.with_suffix(inv.output_path.suffix + ".tmp")
    assert not tmp_file.exists()
    assert inv.output_path.exists()


# ---------------------------------------------------------------------------
# stop_reason variants
# ---------------------------------------------------------------------------


def test_max_tokens_stop_reason(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LEM_CLAUDE_BIN", str(STUBS / "claude_max_tokens"))
    inv = make_invocation(tmp_path)
    result = cli_worker.invoke(inv, system_prompt="system", allowed_tools=[])

    assert result.stop_reason == "max_tokens"
    assert result.exit_code == 0
    assert result.tokens_out == 100


def test_error_stop_reason_on_nonzero_exit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LEM_CLAUDE_BIN", str(STUBS / "claude_error"))
    inv = make_invocation(tmp_path)
    result = cli_worker.invoke(inv, system_prompt="system", allowed_tools=[])

    assert result.stop_reason == "error"
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Auth error (exit 69)
# ---------------------------------------------------------------------------


def test_auth_error_exit_69(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LEM_CLAUDE_BIN", str(STUBS / "claude_auth_fail"))
    inv = make_invocation(tmp_path)
    result = cli_worker.invoke(inv, system_prompt="system", allowed_tools=[])

    assert result.stop_reason == "error"
    assert result.exit_code == 69
    assert "claude auth error" in result.schema_errors
    assert result.tokens_in == 0
    assert result.tokens_out == 0


# ---------------------------------------------------------------------------
# Malformed JSON
# ---------------------------------------------------------------------------


def test_malformed_json_does_not_crash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LEM_CLAUDE_BIN", str(STUBS / "claude_malformed"))
    inv = make_invocation(tmp_path)
    result = cli_worker.invoke(inv, system_prompt="system", allowed_tools=[])

    assert result.stop_reason == "error"
    assert result.tokens_in == 0
    assert result.tokens_out == 0
    assert any("malformed" in e.lower() for e in result.schema_errors)


# ---------------------------------------------------------------------------
# Command-line construction
# ---------------------------------------------------------------------------


def test_cmd_output_format_json_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LEM_CLAUDE_BIN", str(STUBS / "claude_echo_args"))
    inv = make_invocation(tmp_path)
    result = cli_worker.invoke(inv, system_prompt="sys", allowed_tools=[])
    args = json.loads(result.output_path.read_text())["args"]

    assert "--print" in args
    assert "--output-format" in args
    assert args[args.index("--output-format") + 1] == "json"


def test_timeout_returns_timeout_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import signal as _signal
    import subprocess as _subprocess

    def fake_escalation(
        cmd: object, *, timeout_s: int, **_kwargs: object
    ) -> _subprocess.CompletedProcess[str]:
        return _subprocess.CompletedProcess(
            args=cmd,
            returncode=-_signal.SIGTERM,
            stdout="",
            stderr="",
        )

    monkeypatch.setattr("lem.workers.cli_worker.run_with_escalation", fake_escalation)
    inv = make_invocation(tmp_path, timeout_s=30)
    result = cli_worker.invoke(inv, system_prompt="sys", allowed_tools=[])

    assert result.stop_reason == "timeout"
    assert result.duration_s == pytest.approx(30.0)
    assert result.exit_code == -1
    assert result.tokens_in == 0
    assert result.tokens_out == 0


def test_write_atomic_creates_missing_parent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LEM_CLAUDE_BIN", str(STUBS / "claude_success"))
    nested = tmp_path / "deeply" / "nested" / "out.md"
    inv = make_invocation(tmp_path, output_path=nested)
    result = cli_worker.invoke(inv, system_prompt="sys", allowed_tools=[])

    assert result.exit_code == 0
    assert nested.exists()


def test_cmd_model_flag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LEM_CLAUDE_BIN", str(STUBS / "claude_echo_args"))
    inv = make_invocation(tmp_path, model="haiku")
    cli_worker.invoke(inv, system_prompt="sys", allowed_tools=[])

    args = json.loads(inv.output_path.read_text())["args"]
    assert "--model" in args
    assert args[args.index("--model") + 1] == "haiku"


@pytest.mark.parametrize("model", ["haiku", "sonnet", "opus"])
def test_cmd_model_flag_parametrized(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, model: str
) -> None:
    monkeypatch.setenv("LEM_CLAUDE_BIN", str(STUBS / "claude_echo_args"))
    inv = make_invocation(tmp_path, model=model)
    cli_worker.invoke(inv, system_prompt="sys", allowed_tools=[])

    args = json.loads(inv.output_path.read_text())["args"]
    assert args[args.index("--model") + 1] == model


def test_cmd_system_prompt_passed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LEM_CLAUDE_BIN", str(STUBS / "claude_echo_args"))
    inv = make_invocation(tmp_path)
    cli_worker.invoke(inv, system_prompt="Be concise.", allowed_tools=[])

    args = json.loads(inv.output_path.read_text())["args"]
    assert "--system-prompt" in args
    assert args[args.index("--system-prompt") + 1] == "Be concise."


def test_cmd_allowed_tools_included(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LEM_CLAUDE_BIN", str(STUBS / "claude_echo_args"))
    inv = make_invocation(tmp_path)
    cli_worker.invoke(inv, system_prompt="sys", allowed_tools=["Bash", "Edit"])

    args = json.loads(inv.output_path.read_text())["args"]
    assert "Bash" in args
    assert "Edit" in args


def test_cmd_no_allowed_tools_flag_when_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LEM_CLAUDE_BIN", str(STUBS / "claude_echo_args"))
    inv = make_invocation(tmp_path)
    cli_worker.invoke(inv, system_prompt="sys", allowed_tools=[])

    args = json.loads(inv.output_path.read_text())["args"]
    assert "--allowedTools" not in args


# ---------------------------------------------------------------------------
# LEM_CLAUDE_BIN override
# ---------------------------------------------------------------------------


def test_lem_claude_bin_override_respected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LEM_CLAUDE_BIN", str(STUBS / "claude_success"))
    inv = make_invocation(tmp_path)
    result = cli_worker.invoke(inv, system_prompt="sys", allowed_tools=[])
    assert result.stop_reason == "end_turn"


def test_no_claude_in_path_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("LEM_CLAUDE_BIN", raising=False)
    monkeypatch.setenv("PATH", "")
    with pytest.raises(RuntimeError, match="claude CLI not found"):
        cli_worker._find_claude_binary()


# ---------------------------------------------------------------------------
# allowed_read_paths prompt assembly
# ---------------------------------------------------------------------------


def test_allowed_read_paths_content_in_prompt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LEM_CLAUDE_BIN", str(STUBS / "claude_echo_args"))

    context_file = tmp_path / "idea.md"
    context_file.write_text("This is the idea.", encoding="utf-8")

    inv = make_invocation(tmp_path, allowed_read_paths=[context_file])
    cli_worker.invoke(inv, system_prompt="sys", allowed_tools=[])

    echo = json.loads(inv.output_path.read_text())
    stdin = echo["stdin"]
    assert "This is the idea." in stdin
    assert "READ-ONLY" in stdin
    assert str(context_file) in stdin


def test_missing_read_path_raises_before_invoke(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LEM_CLAUDE_BIN", str(STUBS / "claude_success"))

    missing = tmp_path / "does_not_exist.md"
    inv = make_invocation(tmp_path, allowed_read_paths=[missing])

    with pytest.raises(FileNotFoundError, match="allowed_read_path does not exist"):
        cli_worker.invoke(inv, system_prompt="sys", allowed_tools=[])


def test_extra_context_appears_in_prompt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LEM_CLAUDE_BIN", str(STUBS / "claude_echo_args"))
    inv = make_invocation(tmp_path, extra_context={"branch": "feat/v1", "run_id": "abc123"})
    cli_worker.invoke(inv, system_prompt="sys", allowed_tools=[])

    stdin = json.loads(inv.output_path.read_text())["stdin"]
    assert "extra_context.branch" in stdin
    assert "feat/v1" in stdin
    assert "extra_context.run_id" in stdin
    assert "abc123" in stdin


# ---------------------------------------------------------------------------
# cwd is set to workspace_path
# ---------------------------------------------------------------------------


def test_strip_outer_code_fence_removes_markdown_wrapper() -> None:
    """Regression: pruner-style output wrapped in ```markdown fence breaks parser."""
    fenced = (
        "```markdown\n"
        "---\n"
        "domain: architect\n"
        "survivor: a\n"
        "---\n\n"
        "## Decision\n"
        "Option A.\n"
        "```\n"
    )
    out = cli_worker._strip_outer_code_fence(fenced)
    assert out.startswith("---\n")
    assert "domain: architect" in out
    assert "```" not in out


def test_strip_outer_code_fence_handles_plain_fence() -> None:
    fenced = "```\nhello\nworld\n```\n"
    out = cli_worker._strip_outer_code_fence(fenced)
    assert out == "hello\nworld\n"


def test_strip_outer_code_fence_leaves_unfenced_text_alone() -> None:
    plain = "---\ndomain: x\n---\n## Body\nfoo\n"
    assert cli_worker._strip_outer_code_fence(plain) == plain


def test_strip_outer_code_fence_leaves_inline_fences_alone() -> None:
    """A fence in the middle of content (not wrapping the whole response) must not strip."""
    text = "Some prose.\n```python\ninline = 1\n```\nMore prose.\n"
    assert cli_worker._strip_outer_code_fence(text) == text


def test_fenced_response_written_unfenced_to_output_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """End-to-end: a stub claude that returns fenced markdown should produce
    an unfenced output file that the schema parser can read."""
    fenced_stub = tmp_path / "claude_fenced"
    fenced_stub.write_text(
        '#!/usr/bin/env bash\n'
        'cat <<\'EOF\'\n'
        '{"type":"result","subtype":"success","is_error":false,'
        '"result":"```markdown\\n---\\ndomain: architect\\n---\\n## Decision\\nA.\\n```\\n",'
        '"stop_reason":"end_turn","session_id":"x","total_cost_usd":0.0,'
        '"duration_ms":1,"duration_api_ms":1,'
        '"usage":{"input_tokens":0,"output_tokens":0,'
        '"cache_creation_input_tokens":0,"cache_read_input_tokens":0},'
        '"permission_denials":[],"terminal_reason":"completed"}\n'
        'EOF\n',
        encoding="utf-8",
    )
    fenced_stub.chmod(0o755)
    monkeypatch.setenv("LEM_CLAUDE_BIN", str(fenced_stub))

    inv = make_invocation(tmp_path, output_path=tmp_path / "decision.md")
    cli_worker.invoke(inv, system_prompt="sys", allowed_tools=[])

    written = inv.output_path.read_text(encoding="utf-8")
    assert written.startswith("---\n")
    assert "```" not in written


def test_user_prompt_forbids_write_tool_and_omits_output_path(
    tmp_path: Path,
) -> None:
    """Regression: the user prompt must not instruct the model to 'write to <path>'.

    Earlier phrasing — "Write your output to /abs/path/to/file" — caused models with
    `tools: []` to apologize and return their content wrapped in a fenced code block
    prefixed by a meta-message ('I cannot write to that file...'), breaking the
    schema validator. The prompt must (a) tell the model to return the output as
    its response text, (b) explicitly forbid file-writing tools, and (c) not leak
    the absolute output path into the prompt.
    """
    inv = make_invocation(tmp_path, max_output_tokens=512)
    prompt = cli_worker._build_user_prompt(inv)

    assert str(inv.output_path) not in prompt
    assert "Write your output to" not in prompt
    lower = prompt.lower()
    assert "no write" in lower or "do not use" in lower or "do not call" in lower
    assert "write" in lower
    assert "code fence" in lower or "no fence" in lower
    assert "512" in prompt


def test_cwd_set_to_workspace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify the subprocess cwd is workspace_path by using a pwd-printing stub."""
    pwd_stub = tmp_path / "claude_pwd"
    pwd_stub.write_text(
        '#!/usr/bin/env bash\n'
        'python3 -c "\nimport json,os\n'
        'envelope={\'type\':\'result\',\'subtype\':\'success\',\'is_error\':False,'
        '\'result\':os.getcwd(),\'stop_reason\':\'end_turn\','
        '\'session_id\':\'x\',\'total_cost_usd\':0.0,\'duration_ms\':1,'
        '\'duration_api_ms\':1,\'usage\':{\'input_tokens\':0,\'output_tokens\':0,'
        '\'cache_creation_input_tokens\':0,\'cache_read_input_tokens\':0},'
        '\'permission_denials\':[],\'terminal_reason\':\'completed\'}\n'
        'print(json.dumps(envelope))\n"',
        encoding="utf-8",
    )
    pwd_stub.chmod(0o755)
    monkeypatch.setenv("LEM_CLAUDE_BIN", str(pwd_stub))

    workspace = tmp_path / "workspace"
    workspace.mkdir()

    inv = WorkerInvocation(
        role_path=tmp_path / "role.md",
        workspace_path=workspace,
        output_path=workspace / "output.json",
        allowed_read_paths=[],
        model="sonnet",
        max_output_tokens=512,
        timeout_s=10,
        extra_context={},
    )
    cli_worker.invoke(inv, system_prompt="sys", allowed_tools=[])

    reported_cwd = (workspace / "output.json").read_text(encoding="utf-8")
    assert Path(reported_cwd).resolve() == workspace.resolve()
