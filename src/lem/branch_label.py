"""Extracts a 2-4 word branch label from context text via claude -p."""
from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path

from lem.types import WorkerInvocation
from lem.workers import cli_worker


class BranchLabelExtractionError(Exception):
    pass


_SYSTEM_PROMPT = (
    "Output ONLY a 2-4 word label that captures the core focus of the context.\n"
    "Format: lowercase words joined by hyphens. No quotes, no punctuation, no explanation.\n"
    "Good examples: mobile-first, b2b-managers, free-tier-only, offline-support.\n"
    "Output the label and nothing else."
)

_TIMEOUT_S = 30
_MAX_OUTPUT_TOKENS = 20


def extract_branch_label(context_text: str) -> str:
    """Use claude -p to summarize the round-2 context as a 2-4 word label.

    Returns the cleaned label string, or raises BranchLabelExtractionError on failure.
    """
    if not context_text.strip():
        raise BranchLabelExtractionError("context_text is empty")

    if os.environ.get("LEM_STUB_MODE"):
        return "stub-label"

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        output_path = tmp / "branch_label.txt"

        inv = WorkerInvocation(
            role_path=Path(__file__),
            workspace_path=tmp,
            output_path=output_path,
            allowed_read_paths=[],
            model="haiku",
            max_output_tokens=_MAX_OUTPUT_TOKENS,
            timeout_s=_TIMEOUT_S,
            extra_context={"context": context_text},
        )

        result = cli_worker.invoke(inv, _SYSTEM_PROMPT, [])

        if result.stop_reason in ("timeout", "error") or result.exit_code != 0:
            raise BranchLabelExtractionError(
                f"claude subprocess failed: exit_code={result.exit_code}, "
                f"stop_reason={result.stop_reason}"
            )

        if not output_path.exists():
            raise BranchLabelExtractionError("claude produced no output")

        raw = output_path.read_text(encoding="utf-8")
        label = _clean_label(raw)
        if not label:
            raise BranchLabelExtractionError("claude output cleaned to empty label")
        return label


def _clean_label(raw: str) -> str:
    text = raw.strip().lower()
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"[^a-z0-9-]", "", text)
    text = re.sub(r"-+", "-", text).strip("-")
    words = [w for w in text.split("-") if w]
    return "-".join(words[:4])
