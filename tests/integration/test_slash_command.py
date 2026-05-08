# pyright: strict
"""Integration tests for Task 10.3 — slash command file and install_agents."""

from __future__ import annotations

from pathlib import Path

import pytest

from lem.install_agents import install_agents


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_COMMANDS_DIR = Path(__file__).parent.parent.parent / ".claude" / "commands"
_LEM_REFINE_MD = _COMMANDS_DIR / "lem-refine.md"
_PROFILES_DIR = Path(__file__).parent.parent.parent / "profiles" / "app-idea"


# ---------------------------------------------------------------------------
# Slash command file tests
# ---------------------------------------------------------------------------


def test_lem_refine_md_exists() -> None:
    assert _LEM_REFINE_MD.exists(), f"{_LEM_REFINE_MD} not found"


def test_lem_refine_md_has_valid_frontmatter() -> None:
    text = _LEM_REFINE_MD.read_text(encoding="utf-8")
    assert text.startswith("---\n"), "file must start with YAML frontmatter delimiter"
    parts = text.split("---\n", maxsplit=2)
    assert len(parts) >= 3, "file must have closing frontmatter delimiter"
    import yaml
    fm = yaml.safe_load(parts[1])
    assert "description" in fm, "frontmatter must have 'description'"
    assert "allowed-tools" in fm, "frontmatter must have 'allowed-tools'"


def test_lem_refine_md_body_references_lem_cli() -> None:
    text = _LEM_REFINE_MD.read_text(encoding="utf-8")
    assert "lem refine" in text, "body must reference 'lem refine'"
    assert "--skip-intake" in text, "body must reference --skip-intake flag"


# ---------------------------------------------------------------------------
# install_agents tests
# ---------------------------------------------------------------------------


def test_install_agents_creates_symlinks(tmp_path: Path) -> None:
    target = tmp_path / ".claude" / "agents"
    created = install_agents(_PROFILES_DIR, target_dir=target)
    assert len(created) > 0
    for path in created:
        assert path.exists(), f"{path} should exist"
        assert path.is_symlink(), f"{path} should be a symlink"
        assert path.suffix == ".md"


def test_install_agents_idempotent(tmp_path: Path) -> None:
    target = tmp_path / ".claude" / "agents"
    created1 = install_agents(_PROFILES_DIR, target_dir=target)
    created2 = install_agents(_PROFILES_DIR, target_dir=target)
    assert sorted(str(p) for p in created1) == sorted(str(p) for p in created2)
    for path in created2:
        assert path.is_symlink()


def test_install_agents_includes_roles_and_process_roles(tmp_path: Path) -> None:
    target = tmp_path / ".claude" / "agents"
    created = install_agents(_PROFILES_DIR, target_dir=target)
    names = {p.stem for p in created}
    assert "architect" in names
    assert "designer" in names
    assert "market" in names
    process_role_names = {"jtbd-extractor", "distiller", "synthesizer", "pruner"}
    assert process_role_names & names, "at least some process_roles must be included"


def test_install_agents_raises_on_regular_file_collision(tmp_path: Path) -> None:
    target = tmp_path / ".claude" / "agents"
    target.mkdir(parents=True)
    (target / "architect.md").write_text("collision", encoding="utf-8")
    with pytest.raises(FileExistsError):
        install_agents(_PROFILES_DIR, target_dir=target)


def test_install_agents_recreates_wrong_symlink(tmp_path: Path) -> None:
    target = tmp_path / ".claude" / "agents"
    target.mkdir(parents=True)
    wrong_target = tmp_path / "wrong.md"
    wrong_target.write_text("wrong", encoding="utf-8")
    import os
    os.symlink(wrong_target, target / "architect.md")
    created = install_agents(_PROFILES_DIR, target_dir=target)
    arch = target / "architect.md"
    assert arch.is_symlink()
    assert arch.resolve() != wrong_target.resolve()
