# pyright: strict
"""Worker invocation with timeout, retry, schema validation.

dispatch_worker is the public seam between the orchestrator and cli_worker.
Task 3.3 will add retry-on-schema-fail and exponential backoff here.

Logging: timeout events SHOULD be written to log.jsonl once state/log.py
(Task 4.1) exists. For now, WorkerResult.stop_reason == "timeout" is the
only signal.
"""

from __future__ import annotations

from lem.types import WorkerInvocation, WorkerResult
from lem.workers import cli_worker


def dispatch_worker(
    inv: WorkerInvocation,
    system_prompt: str,
    allowed_tools: list[str],
) -> WorkerResult:
    """Invoke the CLI worker and return its result unchanged.

    Timeout enforcement and SIGTERM/SIGKILL escalation are handled inside
    cli_worker.invoke via failure.timeout.run_with_escalation.
    """
    return cli_worker.invoke(inv, system_prompt, allowed_tools)
