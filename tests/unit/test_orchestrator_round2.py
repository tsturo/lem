# pyright: strict
"""Tests for round-2+ orchestrator behavior (parent_run_id set)."""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Any

import pytest

from lem.orchestrator import (
    OrchestratorConfig,
    OrchestratorError,
    run_orchestrator,
)
from lem.phases import PHASES
from lem.types import Profile, Role

_SYNTHESIZER_FM = """\
---
recommendation: Build
confidence: high
---

## Verdict

Build.
"""

_PROCESS_ROLE_NAMES = [
    "jtbd-extractor",
    "disagreement-detector",
    "frame-shifter",
    "branch-skeptic",
    "pruner",
    "distiller",
    "cross-skeptic",
    "kill-case-skeptic",
    "synthesizer",
]


def _make_role(name: str = "stub-role") -> Role:
    return Role(
        name=name,
        description="stub",
        model="haiku",
        worker="cli",
        phase=None,
        output_cap=1024,
        timeout_s=30,
        branchable="no",
        output_schema={},
        tools=[],
        system_prompt="",
        source_path=Path("/stub"),
    )


@pytest.fixture
def stub_profile() -> Profile:
    role = _make_role("stub-role")
    process_roles = {name: _make_role(name) for name in _PROCESS_ROLE_NAMES}
    return Profile(
        name="stub",
        description="stub profile",
        specialists=["stub-role"],
        verdict_options=[],
        default_deliverables=[],
        flag_gated_deliverables={},
        roles={"stub-role": role},
        process_roles=process_roles,
        intake_prompt="",
        source_dir=Path("/stub"),
    )


def _patch_all_phases_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    def _empty(s: Any, p: Any) -> list[Any]:
        return []

    patched = [dataclasses.replace(p, workers_fn=_empty) for p in PHASES]
    monkeypatch.setattr("lem.orchestrator.PHASES", patched)


def _make_parent_dir(tmp_path: Path, *, round_depth: int | None = None) -> Path:
    parent = tmp_path / "parent-run"
    parent.mkdir()
    (parent / "meta").mkdir()
    (parent / "idea.md").write_text("# Idea\n\nParent idea.", encoding="utf-8")
    (parent / "meta" / "synthesis.md").write_text(_SYNTHESIZER_FM, encoding="utf-8")
    if round_depth is not None:
        (parent / "meta" / "round-depth").write_text(str(round_depth), encoding="utf-8")
    return parent


def _make_new_workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "new-run"
    ws.mkdir()
    (ws / "idea.md").write_text("# Idea\n\nNew idea.", encoding="utf-8")
    return ws


def _make_ctx_file(tmp_path: Path, text: str = "Now mobile-first.") -> Path:
    ctx = tmp_path / "context.txt"
    ctx.write_text(text, encoding="utf-8")
    return ctx


class TestRound1PathUnchanged:
    def test_no_parent_run_id_completes_normally(
        self,
        tmp_path: Path,
        stub_profile: Profile,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        ws = _make_new_workspace(tmp_path)
        _patch_all_phases_empty(monkeypatch)
        state = run_orchestrator(ws, stub_profile)
        assert state.status == "completed"
        assert not (ws / "meta" / "parent_run_id").exists()
        assert not (ws / "meta" / "round-depth").exists()

    def test_no_parent_run_id_idea_md_unmodified(
        self,
        tmp_path: Path,
        stub_profile: Profile,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        ws = _make_new_workspace(tmp_path)
        original_idea = (ws / "idea.md").read_text(encoding="utf-8")
        _patch_all_phases_empty(monkeypatch)
        run_orchestrator(ws, stub_profile)
        assert (ws / "idea.md").read_text(encoding="utf-8") == original_idea


class TestRound2HappyPath:
    def test_all_four_meta_files_written(
        self,
        tmp_path: Path,
        stub_profile: Profile,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        parent = _make_parent_dir(tmp_path)
        ws = _make_new_workspace(tmp_path)
        ctx = _make_ctx_file(tmp_path)
        monkeypatch.setattr("lem.orchestrator.run_dir_by_id", lambda _: parent)
        _patch_all_phases_empty(monkeypatch)

        config = OrchestratorConfig(
            parent_run_id="parent-abc",
            branch_label="mobile-first",
            iteration_context_file=ctx,
        )
        state = run_orchestrator(ws, stub_profile, config)

        def _read(name: str) -> str:
            return (ws / "meta" / name).read_text(encoding="utf-8")

        assert state.status == "completed"
        assert _read("parent_run_id") == "parent-abc"
        assert _read("branch_label") == "mobile-first"
        assert _read("iteration-context.md") == "Now mobile-first."
        assert _read("round-depth") == "2"

    def test_iteration_context_header_injected_into_idea_md(
        self,
        tmp_path: Path,
        stub_profile: Profile,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        parent = _make_parent_dir(tmp_path)
        ws = _make_new_workspace(tmp_path)
        ctx = _make_ctx_file(tmp_path, "Mobile-first with comments.")
        monkeypatch.setattr("lem.orchestrator.run_dir_by_id", lambda _: parent)
        _patch_all_phases_empty(monkeypatch)

        config = OrchestratorConfig(
            parent_run_id="parent-abc",
            branch_label="mobile-first",
            iteration_context_file=ctx,
        )
        run_orchestrator(ws, stub_profile, config)

        idea_content = (ws / "idea.md").read_text(encoding="utf-8")
        assert "This is round 2 of refinement on this idea." in idea_content
        assert "Round 1 (parent) reached verdict: Build (high)." in idea_content
        assert "> Mobile-first with comments." in idea_content
        assert "# Idea" in idea_content

    def test_round_depth_increments_from_parent(
        self,
        tmp_path: Path,
        stub_profile: Profile,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        parent = _make_parent_dir(tmp_path, round_depth=2)
        ws = _make_new_workspace(tmp_path)
        ctx = _make_ctx_file(tmp_path)
        monkeypatch.setattr("lem.orchestrator.run_dir_by_id", lambda _: parent)
        _patch_all_phases_empty(monkeypatch)

        config = OrchestratorConfig(
            parent_run_id="parent-abc",
            branch_label="some-label",
            iteration_context_file=ctx,
        )
        run_orchestrator(ws, stub_profile, config)

        assert (ws / "meta" / "round-depth").read_text(encoding="utf-8") == "3"
        idea_content = (ws / "idea.md").read_text(encoding="utf-8")
        assert "This is round 3 of refinement on this idea." in idea_content
        assert "Round 2 (parent) reached verdict: Build (high)." in idea_content

    def test_legacy_parent_without_round_depth_defaults_to_1(
        self,
        tmp_path: Path,
        stub_profile: Profile,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        parent = _make_parent_dir(tmp_path)
        ws = _make_new_workspace(tmp_path)
        ctx = _make_ctx_file(tmp_path)
        monkeypatch.setattr("lem.orchestrator.run_dir_by_id", lambda _: parent)
        _patch_all_phases_empty(monkeypatch)

        config = OrchestratorConfig(
            parent_run_id="parent-abc",
            branch_label="label",
            iteration_context_file=ctx,
        )
        run_orchestrator(ws, stub_profile, config)

        assert (ws / "meta" / "round-depth").read_text(encoding="utf-8") == "2"


class TestRound2ErrorCases:
    def test_missing_parent_dir_raises_orchestrator_error(
        self,
        tmp_path: Path,
        stub_profile: Profile,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        missing = tmp_path / "does-not-exist"
        monkeypatch.setattr("lem.orchestrator.run_dir_by_id", lambda _: missing)
        ws = _make_new_workspace(tmp_path)
        ctx = _make_ctx_file(tmp_path)

        config = OrchestratorConfig(
            parent_run_id="ghost-id",
            branch_label="label",
            iteration_context_file=ctx,
        )
        with pytest.raises(OrchestratorError, match="parent run not found"):
            run_orchestrator(ws, stub_profile, config)

    def test_missing_iteration_context_file_raises(
        self,
        tmp_path: Path,
        stub_profile: Profile,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        parent = _make_parent_dir(tmp_path)
        monkeypatch.setattr("lem.orchestrator.run_dir_by_id", lambda _: parent)
        ws = _make_new_workspace(tmp_path)

        config = OrchestratorConfig(
            parent_run_id="parent-abc",
            branch_label="label",
            iteration_context_file=tmp_path / "no-such-file.txt",
        )
        with pytest.raises(OrchestratorError, match="iteration_context_file not found"):
            run_orchestrator(ws, stub_profile, config)

    def test_none_iteration_context_file_raises(
        self,
        tmp_path: Path,
        stub_profile: Profile,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        parent = _make_parent_dir(tmp_path)
        monkeypatch.setattr("lem.orchestrator.run_dir_by_id", lambda _: parent)
        ws = _make_new_workspace(tmp_path)

        config = OrchestratorConfig(
            parent_run_id="parent-abc",
            branch_label="label",
            iteration_context_file=None,
        )
        with pytest.raises(
            OrchestratorError, match="iteration_context_file is required"
        ):
            run_orchestrator(ws, stub_profile, config)

    def test_empty_iteration_context_raises(
        self,
        tmp_path: Path,
        stub_profile: Profile,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        parent = _make_parent_dir(tmp_path)
        monkeypatch.setattr("lem.orchestrator.run_dir_by_id", lambda _: parent)
        ws = _make_new_workspace(tmp_path)
        ctx = _make_ctx_file(tmp_path, "   \n  ")

        config = OrchestratorConfig(
            parent_run_id="parent-abc",
            branch_label="label",
            iteration_context_file=ctx,
        )
        with pytest.raises(OrchestratorError, match="empty"):
            run_orchestrator(ws, stub_profile, config)

    def test_missing_synthesis_md_raises(
        self,
        tmp_path: Path,
        stub_profile: Profile,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        parent = tmp_path / "parent-run"
        parent.mkdir()
        (parent / "meta").mkdir()
        (parent / "idea.md").write_text("# Idea\n\nParent.", encoding="utf-8")
        monkeypatch.setattr("lem.orchestrator.run_dir_by_id", lambda _: parent)
        ws = _make_new_workspace(tmp_path)
        ctx = _make_ctx_file(tmp_path)

        config = OrchestratorConfig(
            parent_run_id="parent-abc",
            branch_label="label",
            iteration_context_file=ctx,
        )
        with pytest.raises(OrchestratorError, match="synthesis.md not found"):
            run_orchestrator(ws, stub_profile, config)


class TestBranchLabelLogic:
    def test_branch_label_none_calls_extractor(
        self,
        tmp_path: Path,
        stub_profile: Profile,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        parent = _make_parent_dir(tmp_path)
        ws = _make_new_workspace(tmp_path)
        ctx = _make_ctx_file(tmp_path, "Focus on mobile.")
        monkeypatch.setattr("lem.orchestrator.run_dir_by_id", lambda _: parent)
        _patch_all_phases_empty(monkeypatch)

        extractor_calls: list[str] = []

        def mock_extractor(text: str) -> str:
            extractor_calls.append(text)
            return "mobile-first"

        monkeypatch.setattr("lem.orchestrator.extract_branch_label", mock_extractor)

        config = OrchestratorConfig(
            parent_run_id="parent-abc",
            branch_label=None,
            iteration_context_file=ctx,
        )
        run_orchestrator(ws, stub_profile, config)

        assert len(extractor_calls) == 1
        label = (ws / "meta" / "branch_label").read_text(encoding="utf-8")
        assert label == "mobile-first"

    def test_branch_label_empty_string_uses_fallback_without_extractor(
        self,
        tmp_path: Path,
        stub_profile: Profile,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        parent = _make_parent_dir(tmp_path)
        ws = _make_new_workspace(tmp_path)
        ctx = _make_ctx_file(tmp_path)
        monkeypatch.setattr("lem.orchestrator.run_dir_by_id", lambda _: parent)
        _patch_all_phases_empty(monkeypatch)

        extractor_calls: list[str] = []

        def mock_extractor(text: str) -> str:
            extractor_calls.append(text)
            return "should-not-be-called"

        monkeypatch.setattr("lem.orchestrator.extract_branch_label", mock_extractor)

        config = OrchestratorConfig(
            parent_run_id="parent-abc",
            branch_label="",
            iteration_context_file=ctx,
        )
        run_orchestrator(ws, stub_profile, config)

        assert extractor_calls == []
        assert (ws / "meta" / "branch_label").read_text(encoding="utf-8") == "round-2"

    def test_extractor_raises_falls_back_to_round_n(
        self,
        tmp_path: Path,
        stub_profile: Profile,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from lem.branch_label import BranchLabelExtractionError

        parent = _make_parent_dir(tmp_path)
        ws = _make_new_workspace(tmp_path)
        ctx = _make_ctx_file(tmp_path)
        monkeypatch.setattr("lem.orchestrator.run_dir_by_id", lambda _: parent)
        _patch_all_phases_empty(monkeypatch)

        def failing_extractor(text: str) -> str:
            raise BranchLabelExtractionError("claude failed")

        monkeypatch.setattr("lem.orchestrator.extract_branch_label", failing_extractor)

        config = OrchestratorConfig(
            parent_run_id="parent-abc",
            branch_label=None,
            iteration_context_file=ctx,
        )
        state = run_orchestrator(ws, stub_profile, config)

        assert state.status == "completed"
        assert (ws / "meta" / "branch_label").read_text(encoding="utf-8") == "round-2"

    def test_explicit_branch_label_used_verbatim(
        self,
        tmp_path: Path,
        stub_profile: Profile,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        parent = _make_parent_dir(tmp_path)
        ws = _make_new_workspace(tmp_path)
        ctx = _make_ctx_file(tmp_path)
        monkeypatch.setattr("lem.orchestrator.run_dir_by_id", lambda _: parent)
        _patch_all_phases_empty(monkeypatch)

        extractor_calls: list[str] = []

        def mock_extractor(text: str) -> str:
            extractor_calls.append(text)
            return "should-not-be-called"

        monkeypatch.setattr("lem.orchestrator.extract_branch_label", mock_extractor)

        config = OrchestratorConfig(
            parent_run_id="parent-abc",
            branch_label="b2b-focus",
            iteration_context_file=ctx,
        )
        run_orchestrator(ws, stub_profile, config)

        assert extractor_calls == []
        assert (ws / "meta" / "branch_label").read_text(encoding="utf-8") == "b2b-focus"


class TestAtomicWriteSemantics:
    def test_meta_files_not_partial_if_idea_md_missing(
        self,
        tmp_path: Path,
        stub_profile: Profile,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        parent = _make_parent_dir(tmp_path)
        ws = tmp_path / "new-run-no-idea"
        ws.mkdir()
        ctx = _make_ctx_file(tmp_path)
        monkeypatch.setattr("lem.orchestrator.run_dir_by_id", lambda _: parent)
        _patch_all_phases_empty(monkeypatch)

        config = OrchestratorConfig(
            parent_run_id="parent-abc",
            branch_label="x",
            iteration_context_file=ctx,
        )
        run_orchestrator(ws, stub_profile, config)

        idea = (ws / "idea.md").read_text(encoding="utf-8")
        assert "This is round 2 of refinement on this idea." in idea
        assert (ws / "meta" / "parent_run_id").exists()
