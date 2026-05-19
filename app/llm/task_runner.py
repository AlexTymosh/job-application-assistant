from __future__ import annotations

from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from app.core.errors import TailoringWorkflowError
from app.llm.tailoring_client import SectionTailoringClient, parse_model_json_response
from app.llm.task_logging import AiTaskLogger

ResponseModelT = TypeVar("ResponseModelT", bound=BaseModel)


class AiTaskRunner:
    """Runs one Variant-only AI task with task-level diagnostics."""

    def __init__(
        self,
        *,
        client: SectionTailoringClient,
        logger: AiTaskLogger,
        application_id: int,
        profile_id: int,
        resume_id: int,
        prompt_variant_id: int,
        prompt_variant_name: str,
        model: str,
        llm_mode: str,
        trace_id: str,
    ) -> None:
        self.client = client
        self.logger = logger
        self.application_id = application_id
        self.profile_id = profile_id
        self.resume_id = resume_id
        self.prompt_variant_id = prompt_variant_id
        self.prompt_variant_name = prompt_variant_name
        self.model = model
        self.llm_mode = llm_mode
        self.trace_id = trace_id

    def run_json_task(
        self,
        *,
        task_name: str,
        payload: dict[str, Any],
        prompt: str,
        response_model: type[ResponseModelT],
    ) -> ResponseModelT:
        self._log(
            task_name=task_name,
            status="started",
            safe_payload=payload,
        )
        raw_response = ""
        try:
            raw_response = self.client.complete_text(
                task_name=task_name,
                payload=payload,
                prompt=prompt,
                model=self.model,
            )
            self._log(
                task_name=task_name,
                status="response_received",
                raw_response=raw_response,
            )
        except TailoringWorkflowError as exc:
            self._log(
                task_name=task_name,
                status=exc.error_kind or "provider_error",
                error=str(exc),
            )
            raise TailoringWorkflowError(
                str(exc),
                task_name=task_name,
                trace_id=self.trace_id,
                error_kind=exc.error_kind or "provider_error",
            ) from exc
        except Exception as exc:  # pragma: no cover - defensive provider boundary
            self._log(
                task_name=task_name,
                status="provider_error",
                error=str(exc),
            )
            raise TailoringWorkflowError(
                "AI provider could not complete the task.",
                task_name=task_name,
                trace_id=self.trace_id,
                error_kind="provider_error",
            ) from exc

        try:
            parsed = parse_model_json_response(raw_response)
        except TailoringWorkflowError as exc:
            self._log(
                task_name=task_name,
                status="parse_error",
                error=str(exc),
                raw_response=raw_response,
            )
            raise TailoringWorkflowError(
                str(exc),
                task_name=task_name,
                trace_id=self.trace_id,
                error_kind="parse_error",
            ) from exc

        try:
            validated = response_model.model_validate(parsed)
        except ValidationError as exc:
            self._log(
                task_name=task_name,
                status="validation_error",
                error=str(exc),
                raw_response=raw_response,
                parsed_response=parsed,
            )
            raise TailoringWorkflowError(
                "AI returned JSON that does not match the expected response contract.",
                task_name=task_name,
                trace_id=self.trace_id,
                error_kind="validation_error",
            ) from exc

        self._log(
            task_name=task_name,
            status="success",
            parsed_response=validated.model_dump(),
        )
        return validated

    def _log(self, *, task_name: str, status: str, **extra: Any) -> None:
        self.logger.log(
            {
                "application_id": self.application_id,
                "profile_id": self.profile_id,
                "resume_id": self.resume_id,
                "task_name": task_name,
                "prompt_variant_id": self.prompt_variant_id,
                "prompt_variant_name": self.prompt_variant_name,
                "model": self.model,
                "llm_mode": self.llm_mode,
                "trace_id": self.trace_id,
                "status": status,
                **extra,
            }
        )
