# pyright: strict
"""Tests for src/lem/intake.py."""

from __future__ import annotations

from io import StringIO
from pathlib import Path
from typing import Any

import pytest
import yaml

from lem.intake import IntakeResult, _check_assumptions_schema, run_intake
from lem.types import Profile, Role, WorkerInvocation, WorkerResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_role() -> Role:
    return Role(
        name="intake",
        description="intake role",
        model="sonnet",
        worker="cli",
        phase=None,
        output_cap=2048,
        timeout_s=120,
        branchable="no",
        output_schema={},
        tools=[],
        system_prompt="",
        source_path=Path("/profiles/app-idea/roles/intake.md"),
    )


def _make_profile(intake_prompt: str = "Tell me about your idea.") -> Profile:
    role = _make_role()
    return Profile(
        name="app-idea",
        description="Evaluate an app idea",
        specialists=["intake"],
        verdict_options=["invest", "pass"],
        default_deliverables=["report"],
        flag_gated_deliverables={},
        roles={"intake": role},
        process_roles={},
        intake_prompt=intake_prompt,
        source_dir=Path("/profiles/app-idea/"),
    )


def _make_worker_result(output_path: Path, *, exit_code: int = 0) -> WorkerResult:
    return WorkerResult(
        exit_code=exit_code,
        output_path=output_path,
        tokens_in=10,
        tokens_out=5,
        cost_usd=0.001,
        duration_s=0.5,
        stop_reason="end_turn",
        schema_valid=False,
        schema_errors=[],
    )


_CANNED_ASSUMPTIONS = [
    {
        "name": "mobile_first",
        "description": "App will be mobile-first",
        "confirmed": True,
        "would_change_verdict_if_false": "yes",
    },
    {
        "name": "b2c_market",
        "description": "Targeting consumer market not enterprise",
        "confirmed": False,
        "would_change_verdict_if_false": "maybe",
    },
]

_CANNED_IDEA_MD = """\
# Idea

A note-taking app for fast capture

## Brief

A mobile-first app for capturing notes quickly.

## Audience

Note-takers who need fast capture on mobile.

## Goal

Provide the fastest capture experience on mobile.

## Constraints

- Mobile-first
- Offline support
"""


def _write_synthesis_outputs(tmp_path: Path) -> None:
    (tmp_path / "idea.md").write_text(_CANNED_IDEA_MD, encoding="utf-8")
    (tmp_path / "assumptions.yaml").write_text(
        yaml.dump(_CANNED_ASSUMPTIONS), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# Test 1: skip=True writes minimal files, no claude calls
# ---------------------------------------------------------------------------


def test_skip_intake_writes_minimal_files(tmp_path: Path) -> None:
    profile = _make_profile()
    result = run_intake(
        workspace_path=tmp_path,
        profile=profile,
        one_liner="A note-taking app",
        skip=True,
    )

    idea = (tmp_path / "idea.md").read_text()
    assert "A note-taking app" in idea

    assumptions: Any = yaml.safe_load((tmp_path / "assumptions.yaml").read_text())
    assert assumptions == []

    assert result.questions_asked == []
    assert result.answers == []
    assert result.idea_md_path == tmp_path / "idea.md"
    assert result.assumptions_yaml_path == tmp_path / "assumptions.yaml"


def test_skip_intake_no_dispatch_calls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[WorkerInvocation] = []

    def fake_dispatch(
        inv: WorkerInvocation,
        sp: str,
        tools: list[str],
        *,
        output_schema: dict[str, object] | None = None,
    ) -> WorkerResult:
        calls.append(inv)
        return _make_worker_result(inv.output_path)

    monkeypatch.setattr("lem.intake.dispatch_worker", fake_dispatch)

    run_intake(
        workspace_path=tmp_path,
        profile=_make_profile(),
        one_liner="A note-taking app",
        skip=True,
    )

    assert calls == []


# ---------------------------------------------------------------------------
# Test 2: Two-phase flow dispatches exactly 2 calls
# ---------------------------------------------------------------------------


def test_intake_runs_two_phase_flow(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[WorkerInvocation] = []

    def fake_dispatch(
        inv: WorkerInvocation,
        sp: str,
        tools: list[str],
        *,
        output_schema: dict[str, object] | None = None,
    ) -> WorkerResult:
        calls.append(inv)
        if len(calls) == 1:
            inv.output_path.write_text(
                "Q: Who is the user?\nQ: What's the goal?\nQ: What's the mechanism?",
                encoding="utf-8",
            )
        else:
            _write_synthesis_outputs(tmp_path)
            inv.output_path.write_text("done", encoding="utf-8")
        return _make_worker_result(inv.output_path)

    monkeypatch.setattr("lem.intake.dispatch_worker", fake_dispatch)

    stdin = StringIO("note-takers\nfast capture\nmobile-first\n")
    stdout = StringIO()
    result = run_intake(
        workspace_path=tmp_path,
        profile=_make_profile(),
        one_liner="A note-taking app",
        stdin=stdin,
        stdout=stdout,
    )

    assert len(calls) == 2
    assert (tmp_path / "idea.md").exists()
    assert (tmp_path / "assumptions.yaml").exists()
    assert len(result.questions_asked) == 3
    assert len(result.answers) == 3


# ---------------------------------------------------------------------------
# Test 3: Questions are printed to stdout
# ---------------------------------------------------------------------------


def test_questions_printed_to_stdout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[WorkerInvocation] = []

    def fake_dispatch(
        inv: WorkerInvocation,
        sp: str,
        tools: list[str],
        *,
        output_schema: dict[str, object] | None = None,
    ) -> WorkerResult:
        calls.append(inv)
        if len(calls) == 1:
            inv.output_path.write_text("Q: Who is the user?", encoding="utf-8")
        else:
            _write_synthesis_outputs(tmp_path)
            inv.output_path.write_text("done", encoding="utf-8")
        return _make_worker_result(inv.output_path)

    monkeypatch.setattr("lem.intake.dispatch_worker", fake_dispatch)

    stdin = StringIO("devs\n")
    stdout = StringIO()
    run_intake(
        workspace_path=tmp_path,
        profile=_make_profile(),
        one_liner="A CLI tool",
        stdin=stdin,
        stdout=stdout,
    )

    assert "Who is the user?" in stdout.getvalue()


# ---------------------------------------------------------------------------
# Test 4: User answers are read from stdin
# ---------------------------------------------------------------------------


def test_answers_read_from_stdin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[WorkerInvocation] = []

    def fake_dispatch(
        inv: WorkerInvocation,
        sp: str,
        tools: list[str],
        *,
        output_schema: dict[str, object] | None = None,
    ) -> WorkerResult:
        calls.append(inv)
        if len(calls) == 1:
            inv.output_path.write_text("Q: Who is the target user?\nQ: What platform?", encoding="utf-8")
        else:
            _write_synthesis_outputs(tmp_path)
            inv.output_path.write_text("done", encoding="utf-8")
        return _make_worker_result(inv.output_path)

    monkeypatch.setattr("lem.intake.dispatch_worker", fake_dispatch)

    stdin = StringIO("mobile developers\niOS\n")
    result = run_intake(
        workspace_path=tmp_path,
        profile=_make_profile(),
        one_liner="A SDK",
        stdin=stdin,
        stdout=StringIO(),
    )

    assert result.answers == ["mobile developers", "iOS"]


# ---------------------------------------------------------------------------
# Test 5: Empty answer line is treated as empty string (not skipped entirely)
# ---------------------------------------------------------------------------


def test_empty_answer_included_as_empty_string(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[WorkerInvocation] = []

    def fake_dispatch(
        inv: WorkerInvocation,
        sp: str,
        tools: list[str],
        *,
        output_schema: dict[str, object] | None = None,
    ) -> WorkerResult:
        calls.append(inv)
        if len(calls) == 1:
            inv.output_path.write_text("Q: Who?\nQ: What?", encoding="utf-8")
        else:
            _write_synthesis_outputs(tmp_path)
            inv.output_path.write_text("done", encoding="utf-8")
        return _make_worker_result(inv.output_path)

    monkeypatch.setattr("lem.intake.dispatch_worker", fake_dispatch)

    stdin = StringIO("\nfast notes\n")
    result = run_intake(
        workspace_path=tmp_path,
        profile=_make_profile(),
        one_liner="App",
        stdin=stdin,
        stdout=StringIO(),
    )

    assert result.answers[0] == ""
    assert result.answers[1] == "fast notes"


# ---------------------------------------------------------------------------
# Test 6: idea.md has expected sections
# ---------------------------------------------------------------------------


def test_idea_md_has_expected_sections(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[WorkerInvocation] = []

    def fake_dispatch(
        inv: WorkerInvocation,
        sp: str,
        tools: list[str],
        *,
        output_schema: dict[str, object] | None = None,
    ) -> WorkerResult:
        calls.append(inv)
        if len(calls) == 1:
            inv.output_path.write_text("Q: Who is the user?", encoding="utf-8")
        else:
            _write_synthesis_outputs(tmp_path)
            inv.output_path.write_text("done", encoding="utf-8")
        return _make_worker_result(inv.output_path)

    monkeypatch.setattr("lem.intake.dispatch_worker", fake_dispatch)

    run_intake(
        workspace_path=tmp_path,
        profile=_make_profile(),
        one_liner="A note-taking app",
        stdin=StringIO("devs\n"),
        stdout=StringIO(),
    )

    idea = (tmp_path / "idea.md").read_text()
    for section in ["# Idea", "## Brief", "## Audience", "## Goal", "## Constraints"]:
        assert section in idea, f"Missing section: {section}"


# ---------------------------------------------------------------------------
# Test 7: assumptions.yaml passes schema validation
# ---------------------------------------------------------------------------


def test_assumptions_yaml_schema_valid(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[WorkerInvocation] = []

    def fake_dispatch(
        inv: WorkerInvocation,
        sp: str,
        tools: list[str],
        *,
        output_schema: dict[str, object] | None = None,
    ) -> WorkerResult:
        calls.append(inv)
        if len(calls) == 1:
            inv.output_path.write_text("Q: Who?", encoding="utf-8")
        else:
            _write_synthesis_outputs(tmp_path)
            inv.output_path.write_text("done", encoding="utf-8")
        return _make_worker_result(inv.output_path)

    monkeypatch.setattr("lem.intake.dispatch_worker", fake_dispatch)

    run_intake(
        workspace_path=tmp_path,
        profile=_make_profile(),
        one_liner="App",
        stdin=StringIO("devs\n"),
        stdout=StringIO(),
    )

    data: Any = yaml.safe_load((tmp_path / "assumptions.yaml").read_text())
    assert isinstance(data, list)
    for entry in data:
        assert "name" in entry
        assert "description" in entry
        assert isinstance(entry["confirmed"], bool)
        assert entry["would_change_verdict_if_false"] in {"yes", "no", "maybe"}


# ---------------------------------------------------------------------------
# Test 8: Schema-invalid assumptions output raises ValueError
# ---------------------------------------------------------------------------


def test_invalid_assumptions_raises_value_error(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="must be a list"):
        _check_assumptions_schema({"not": "a list"})


def test_invalid_assumptions_missing_key_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="missing keys"):
        _check_assumptions_schema([{"name": "x", "description": "y"}])


def test_invalid_confirmed_type_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="'confirmed' must be bool"):
        _check_assumptions_schema([{
            "name": "x",
            "description": "y",
            "confirmed": "true",
            "would_change_verdict_if_false": "yes",
        }])


def test_invalid_verdict_value_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="'would_change_verdict_if_false'"):
        _check_assumptions_schema([{
            "name": "x",
            "description": "y",
            "confirmed": True,
            "would_change_verdict_if_false": "dunno",
        }])


def test_empty_name_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="'name' must be non-empty"):
        _check_assumptions_schema([{
            "name": "",
            "description": "y",
            "confirmed": True,
            "would_change_verdict_if_false": "no",
        }])


# ---------------------------------------------------------------------------
# Test 9: Profile.intake_prompt is passed to the worker's extra_context
# ---------------------------------------------------------------------------


def test_profile_intake_prompt_in_worker_context(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[WorkerInvocation] = []

    def fake_dispatch(
        inv: WorkerInvocation,
        sp: str,
        tools: list[str],
        *,
        output_schema: dict[str, object] | None = None,
    ) -> WorkerResult:
        calls.append(inv)
        if len(calls) == 1:
            inv.output_path.write_text("Q: Who?", encoding="utf-8")
        else:
            _write_synthesis_outputs(tmp_path)
            inv.output_path.write_text("done", encoding="utf-8")
        return _make_worker_result(inv.output_path)

    monkeypatch.setattr("lem.intake.dispatch_worker", fake_dispatch)

    custom_prompt = "Focus on the business model above all else."
    run_intake(
        workspace_path=tmp_path,
        profile=_make_profile(intake_prompt=custom_prompt),
        one_liner="A SaaS product",
        stdin=StringIO("SMBs\n"),
        stdout=StringIO(),
    )

    assert len(calls) == 2
    assert calls[0].extra_context.get("intake_prompt") == custom_prompt
    assert calls[1].extra_context.get("intake_prompt") == custom_prompt


# ---------------------------------------------------------------------------
# Test 10: synthesis call extra_context includes the Q&A transcript
# ---------------------------------------------------------------------------


def test_synthesis_invocation_includes_qa_transcript(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[WorkerInvocation] = []

    def fake_dispatch(
        inv: WorkerInvocation,
        sp: str,
        tools: list[str],
        *,
        output_schema: dict[str, object] | None = None,
    ) -> WorkerResult:
        calls.append(inv)
        if len(calls) == 1:
            inv.output_path.write_text("Q: Who is the user?", encoding="utf-8")
        else:
            _write_synthesis_outputs(tmp_path)
            inv.output_path.write_text("done", encoding="utf-8")
        return _make_worker_result(inv.output_path)

    monkeypatch.setattr("lem.intake.dispatch_worker", fake_dispatch)

    run_intake(
        workspace_path=tmp_path,
        profile=_make_profile(),
        one_liner="A productivity app",
        stdin=StringIO("knowledge workers\n"),
        stdout=StringIO(),
    )

    synth_inv = calls[1]
    assert "qa_transcript" in synth_inv.extra_context
    assert "knowledge workers" in synth_inv.extra_context["qa_transcript"]
