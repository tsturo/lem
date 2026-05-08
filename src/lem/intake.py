# pyright: strict
"""Phase 0 interactive flow.

Two-phase design (Option 1 from spec):
- Phase A: pass one-liner + intake-prompt to claude → generate ≤3 clarifying questions.
- Phase B: pass one-liner + Q&A → synthesize idea.md + assumptions.yaml.

Both phases use dispatch_worker via a transient WorkerInvocation targeting a temp file.
"""

from __future__ import annotations

import dataclasses
import sys
import tempfile
from pathlib import Path
from typing import Any, TextIO, cast

import yaml

from lem.types import Profile, WorkerInvocation, WorkerResult
from lem.workers.dispatch import dispatch_worker

_QUESTIONS_SYSTEM_PROMPT = """\
You are an intake assistant for a product/idea evaluation framework.

Given a user's one-liner idea and a profile-specific intake prompt, generate
at most 3 clarifying questions. Each question should target a distinct missing
dimension (e.g. audience, mechanism, geography, success metric, constraints).

Output ONLY the questions, one per line, each prefixed with "Q: ".
Do not include any preamble, explanation, or closing remarks.
Example format:
Q: Who is the primary user of this product?
Q: What is the core mechanism for achieving the goal?
Q: What does success look like in 12 months?
"""

_SYNTHESIS_SYSTEM_PROMPT = """\
You are an intake assistant for a product/idea evaluation framework.
Given a user's one-liner, clarifying questions, and their answers, produce:

1. A file `idea.md` with this exact structure:
# Idea

<one-line summary>

## Brief

<clarified description, 1-3 paragraphs>

## Audience

<who this is for>

## Goal

<what the user wants to achieve>

## Constraints

- <constraint 1>

2. A file `assumptions.yaml` with a YAML list. Each entry must have exactly these keys:
   - name: short id (no spaces)
   - description: one-line description
   - confirmed: true if the user stated it, false if inferred
   - would_change_verdict_if_false: "yes", "no", or "maybe"

Write BOTH files to the paths given in the task instructions.
Write idea.md first, then assumptions.yaml.
Each file must be written separately. Do not combine them.
"""


@dataclasses.dataclass(frozen=True)
class IntakeResult:
    idea_md_path: Path
    assumptions_yaml_path: Path
    questions_asked: list[str]
    answers: list[str]


def run_intake(
    *,
    workspace_path: Path,
    profile: Profile,
    one_liner: str,
    skip: bool = False,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
) -> IntakeResult:
    """Run the interactive intake flow.

    If skip=True, writes idea.md = one_liner verbatim and an empty assumptions.yaml,
    then returns. (--skip-intake path used by the slash-command flow.)

    Otherwise:
    1. Generate ≤3 clarifying questions via claude -p
    2. Print them to stdout, read answers from stdin (one per line, blank to skip)
    3. Synthesize idea.md + assumptions.yaml via a second claude -p call
    4. Validate assumptions.yaml has expected schema before returning
    """
    _stdin = stdin if stdin is not None else sys.stdin
    _stdout = stdout if stdout is not None else sys.stdout

    idea_path = workspace_path / "idea.md"
    assumptions_path = workspace_path / "assumptions.yaml"

    if skip:
        _write_skip_outputs(idea_path, assumptions_path, one_liner)
        return IntakeResult(
            idea_md_path=idea_path,
            assumptions_yaml_path=assumptions_path,
            questions_asked=[],
            answers=[],
        )

    questions = _generate_questions(workspace_path, profile, one_liner)
    answers = _ask_questions(questions, _stdin, _stdout)
    _synthesize(workspace_path, profile, one_liner, questions, answers)
    _validate_assumptions(assumptions_path)

    return IntakeResult(
        idea_md_path=idea_path,
        assumptions_yaml_path=assumptions_path,
        questions_asked=questions,
        answers=answers,
    )


def _write_skip_outputs(
    idea_path: Path,
    assumptions_path: Path,
    one_liner: str,
) -> None:
    idea_path.write_text(f"# Idea\n\n{one_liner}\n", encoding="utf-8")
    assumptions_path.write_text("[]\n", encoding="utf-8")


def _generate_questions(
    workspace_path: Path,
    profile: Profile,
    one_liner: str,
) -> list[str]:
    with tempfile.NamedTemporaryFile(
        dir=workspace_path, suffix=".txt", delete=False
    ) as f:
        output_path = Path(f.name)

    inv = _make_invocation(
        workspace_path=workspace_path,
        output_path=output_path,
        extra_context={
            "intake_prompt": profile.intake_prompt,
            "one_liner": one_liner,
        },
    )
    result = dispatch_worker(inv, _QUESTIONS_SYSTEM_PROMPT, [])
    return _parse_questions(result)


def _parse_questions(result: WorkerResult) -> list[str]:
    if not result.output_path.exists():
        return []
    text = result.output_path.read_text(encoding="utf-8")
    questions: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("Q:"):
            questions.append(line[2:].strip())
        elif line and not questions:
            questions.append(line)
        if len(questions) >= 3:
            break
    return questions


def _ask_questions(
    questions: list[str],
    stdin: TextIO,
    stdout: TextIO,
) -> list[str]:
    answers: list[str] = []
    for q in questions:
        stdout.write(f"\n{q}\n> ")
        stdout.flush()
        line = stdin.readline()
        answers.append(line.rstrip("\n"))
    return answers


def _synthesize(
    workspace_path: Path,
    profile: Profile,
    one_liner: str,
    questions: list[str],
    answers: list[str],
) -> None:
    qa_lines = [
        f"Q: {q}\nA: {a}" for q, a in zip(questions, answers)
    ]
    qa_text = "\n\n".join(qa_lines)

    idea_path = workspace_path / "idea.md"
    assumptions_path = workspace_path / "assumptions.yaml"

    with tempfile.NamedTemporaryFile(
        dir=workspace_path, suffix=".txt", delete=False
    ) as f:
        synthesis_output_path = Path(f.name)

    inv = _make_invocation(
        workspace_path=workspace_path,
        output_path=synthesis_output_path,
        extra_context={
            "intake_prompt": profile.intake_prompt,
            "one_liner": one_liner,
            "qa_transcript": qa_text,
            "idea_md_path": str(idea_path),
            "assumptions_yaml_path": str(assumptions_path),
        },
    )
    dispatch_worker(inv, _SYNTHESIS_SYSTEM_PROMPT, [])


def _validate_assumptions(assumptions_path: Path) -> None:
    if not assumptions_path.exists():
        raise ValueError("assumptions.yaml was not written by synthesis worker")
    raw = assumptions_path.read_text(encoding="utf-8")
    data = yaml.safe_load(raw)
    _check_assumptions_schema(data)


def _check_assumptions_schema(data: Any) -> None:
    if not isinstance(data, list):
        raise ValueError(
            f"assumptions.yaml must be a list, got {type(data).__name__}"
        )
    entries = cast(list[Any], data)
    for i, entry in enumerate(entries):
        _check_assumption_entry(i, entry)


def _check_assumption_entry(i: int, entry: Any) -> None:
    if not isinstance(entry, dict):
        raise ValueError(
            f"assumptions.yaml entry {i} must be a dict, "
            f"got {type(entry).__name__}"
        )
    row = cast(dict[str, Any], entry)
    _required = {"name", "description", "confirmed",
                 "would_change_verdict_if_false"}
    missing = _required - row.keys()
    if missing:
        raise ValueError(
            f"assumptions.yaml entry {i} missing keys: {sorted(missing)}"
        )
    if not isinstance(row["confirmed"], bool):
        raise ValueError(
            f"assumptions.yaml entry {i}: 'confirmed' must be bool, "
            f"got {type(row['confirmed']).__name__}"
        )
    valid_verdicts = {"yes", "no", "maybe"}
    if row["would_change_verdict_if_false"] not in valid_verdicts:
        raise ValueError(
            f"assumptions.yaml entry {i}: 'would_change_verdict_if_false' "
            f"must be one of {valid_verdicts}, "
            f"got {row['would_change_verdict_if_false']!r}"
        )
    if not isinstance(row["name"], str) or not row["name"]:
        raise ValueError(
            f"assumptions.yaml entry {i}: 'name' must be non-empty str"
        )
    if not isinstance(row["description"], str) or not row["description"]:
        raise ValueError(
            f"assumptions.yaml entry {i}: 'description' must be non-empty str"
        )


def _make_invocation(
    *,
    workspace_path: Path,
    output_path: Path,
    extra_context: dict[str, str],
) -> WorkerInvocation:
    return WorkerInvocation(
        role_path=workspace_path / "intake-role.md",
        workspace_path=workspace_path,
        output_path=output_path,
        allowed_read_paths=[],
        model="sonnet",
        max_output_tokens=2048,
        timeout_s=120,
        extra_context=extra_context,
    )
