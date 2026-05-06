# pyright: strict
"""Worker invocation with timeout, retry, schema validation.

dispatch_worker is the public seam between the orchestrator and cli_worker.

Logging: timeout events SHOULD be written to log.jsonl once state/log.py
(Task 4.1) exists. For now, WorkerResult.stop_reason == "timeout" is the
only signal.

Cost tracking: cost.jsonl logging (Task 4.2) will hook into the attempt list
accumulated here. Each attempt's WorkerResult carries tokens/cost data.

NOTE: HTTP 429/5xx backoff is aspirational for v1.1 SDK-mode workers. The
claude CLI conflates all errors into non-zero exit codes, so CLI mode performs
retry-once-on-non-zero-exit without HTTP-aware backoff.
"""

from __future__ import annotations

import dataclasses

from lem.schema.parser import parse_file
from lem.schema.validator import validate
from lem.types import WorkerInvocation, WorkerResult
from lem.workers import cli_worker

_AUTH_EXIT_CODE = 69


def dispatch_worker(
    inv: WorkerInvocation,
    system_prompt: str,
    allowed_tools: list[str],
    *,
    output_schema: dict[str, object] | None = None,
) -> WorkerResult:
    """Invoke the CLI worker with retry-on-schema-failure and non-zero-exit retry.

    Decision tree per attempt:
    - exit_code == 69 (auth) → return immediately, no retry.
    - stop_reason == "timeout" → return immediately, no retry.
    - exit_code != 0 (other) → retry once with no backoff, then return.
    - exit_code == 0, output_schema is None → return as-is.
    - exit_code == 0, output_schema given → validate output; if invalid,
      retry once with errors as continuation prompt; on second failure,
      return with schema_errors populated.
    """
    result = cli_worker.invoke(inv, system_prompt, allowed_tools)

    if _is_terminal(result):
        return result

    if result.exit_code != 0:
        return _retry_nonzero(inv, system_prompt, allowed_tools)

    return _handle_success(inv, system_prompt, allowed_tools, result, output_schema)


def _is_terminal(result: WorkerResult) -> bool:
    return result.exit_code == _AUTH_EXIT_CODE or result.stop_reason == "timeout"


def _retry_nonzero(
    inv: WorkerInvocation,
    system_prompt: str,
    allowed_tools: list[str],
) -> WorkerResult:
    return cli_worker.invoke(inv, system_prompt, allowed_tools)


def _handle_success(
    inv: WorkerInvocation,
    system_prompt: str,
    allowed_tools: list[str],
    result: WorkerResult,
    output_schema: dict[str, object] | None,
) -> WorkerResult:
    if output_schema is None:
        return result

    errors = _validate_output(result, output_schema)
    if not errors:
        return dataclasses.replace(result, schema_valid=True)

    return _retry_schema_failure(
        inv, system_prompt, allowed_tools, errors, output_schema
    )


def _validate_output(
    result: WorkerResult,
    output_schema: dict[str, object],
) -> list[str]:
    if not result.output_path.exists():
        return ["output file not written"]
    doc = parse_file(result.output_path)
    validation = validate(doc, output_schema)
    return list(validation.errors)


def _retry_schema_failure(
    inv: WorkerInvocation,
    system_prompt: str,
    allowed_tools: list[str],
    errors: list[str],
    output_schema: dict[str, object],
) -> WorkerResult:
    retry_inv = dataclasses.replace(
        inv,
        extra_context={
            **inv.extra_context,
            "schema_errors": "\n".join(errors),
            "retry_instruction": (
                "Your previous output had schema errors listed above. Fix them."
            ),
        },
    )
    retry_result = cli_worker.invoke(retry_inv, system_prompt, allowed_tools)

    if retry_result.exit_code != 0:
        return dataclasses.replace(
            retry_result, schema_valid=False, schema_errors=errors
        )

    retry_errors = _validate_output(retry_result, output_schema)
    if not retry_errors:
        return dataclasses.replace(retry_result, schema_valid=True)

    return dataclasses.replace(
        retry_result, schema_valid=False, schema_errors=retry_errors
    )
