"""Tests for profiles/app-idea/profile.yaml + intake-prompt.md (Task 7.1)."""

from pathlib import Path

import yaml

PROFILE_DIR = Path(__file__).parent.parent.parent / "profiles" / "app-idea"


def _load_profile() -> dict[str, object]:
    text = (PROFILE_DIR / "profile.yaml").read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    assert isinstance(data, dict)
    return data


def test_profile_yaml_loads() -> None:
    data = _load_profile()
    assert data["name"] == "app-idea"


def test_profile_has_description() -> None:
    data = _load_profile()
    desc = data.get("description")
    assert isinstance(desc, str)
    assert len(desc) > 10


def test_profile_specialists() -> None:
    data = _load_profile()
    assert data["specialists"] == ["architect", "designer", "market"]


def test_profile_verdict_options() -> None:
    data = _load_profile()
    options = data["verdict_options"]
    assert isinstance(options, list)
    assert "Build" in options
    assert "Don't build" in options
    assert "Insufficient information" in options
    assert len(options) == 5


def test_profile_default_deliverables() -> None:
    data = _load_profile()
    assert data["default_deliverables"] == [
        "executive-summary",
        "mvp-plan",
        "risks-and-rejected-paths",
    ]


def test_profile_flag_gated_deliverables() -> None:
    data = _load_profile()
    flags = data["flag_gated_deliverables"]
    assert isinstance(flags, dict)
    assert flags["--with-pitch"] == "investor-onepager"
    assert flags["--with-roadmap"] == "roadmap"
    assert flags["--with-techstack"] == "tech-stack"


def test_profile_branching_policy() -> None:
    data = _load_profile()
    policy = data["branching_policy"]
    assert isinstance(policy, dict)
    assert set(policy.keys()) == {"architect", "designer", "market"}


def test_intake_prompt_exists_and_nonempty() -> None:
    text = (PROFILE_DIR / "intake-prompt.md").read_text(encoding="utf-8")
    assert text.strip()
    assert len(text.split()) > 100


def test_intake_prompt_mentions_three_questions() -> None:
    text = (PROFILE_DIR / "intake-prompt.md").read_text(encoding="utf-8").lower()
    assert "3 question" in text or "three question" in text or "at most 3" in text
