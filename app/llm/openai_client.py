from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.llm.errors import (
    JobExtractionError,
    JobExtractionValidationError,
    OpenAIExtractionError,
    OpenAIExtractionRefusalError,
    OpenAIExtractionResponseError,
)
from app.llm.schemas import ExtractedJob

_PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "job_extraction.md"


class OpenAIJobExtractionClient:
    """OpenAI Structured Outputs client for job extraction.

    The SDK client is injectable so tests can use local test doubles without
    network access or an OpenAI API key.
    """

    def __init__(
        self,
        model: str,
        client: object | None = None,
        api_key: str | None = None,
    ) -> None:
        normalised_model = model.strip()

        if not normalised_model:
            raise OpenAIExtractionError("OpenAI extraction model must not be empty.")

        self._model = normalised_model
        self._api_key = api_key.strip() if api_key is not None else None
        self._client = client if client is not None else self._build_default_client()
        self._system_prompt = _PROMPT_PATH.read_text(encoding="utf-8")

    def extract_job(self, job_text: str) -> ExtractedJob:
        normalised_job_text = job_text.strip()

        if not normalised_job_text:
            raise JobExtractionError("Job text must not be empty.")

        try:
            response = self._client.responses.parse(  # type: ignore[attr-defined]
                model=self._model,
                input=[
                    {"role": "system", "content": self._system_prompt},
                    {"role": "user", "content": normalised_job_text},
                ],
                text_format=ExtractedJob,
            )
        except (JobExtractionError, OpenAIExtractionError):
            raise
        except ValidationError as exc:
            raise JobExtractionValidationError(
                "OpenAI job extraction response failed schema validation."
            ) from exc
        except (
            Exception
        ) as exc:  # pragma: no cover - concrete SDK errors vary by version.
            raise OpenAIExtractionError(
                "OpenAI job extraction request failed."
            ) from exc

        refusal = _find_refusal(response)
        if refusal is not None:
            raise OpenAIExtractionRefusalError(
                f"OpenAI refused structured job extraction: {refusal}"
            )

        parsed = getattr(response, "output_parsed", None)
        if isinstance(parsed, ExtractedJob):
            return parsed

        if isinstance(parsed, dict):
            try:
                return ExtractedJob.model_validate(parsed)
            except ValidationError as exc:
                raise JobExtractionValidationError(
                    "OpenAI job extraction response failed schema validation."
                ) from exc

        raise OpenAIExtractionResponseError(
            "OpenAI response did not contain a parsed ExtractedJob."
        )

    def _build_default_client(self) -> object:
        if self._api_key is None or not self._api_key.strip():
            raise OpenAIExtractionError("OpenAI API key is not configured.")

        from openai import OpenAI

        return OpenAI(api_key=self._api_key)


def _find_refusal(value: object) -> str | None:
    return _find_refusal_in_value(value, seen_ids=set())


def _find_refusal_in_value(value: object, *, seen_ids: set[int]) -> str | None:
    if value is None or isinstance(value, str | bytes | int | float | bool):
        return None

    value_id = id(value)
    if value_id in seen_ids:
        return None

    seen_ids.add(value_id)

    if isinstance(value, dict):
        refusal = value.get("refusal")
        if isinstance(refusal, str) and refusal.strip():
            return refusal.strip()

        for nested_value in value.values():
            nested_refusal = _find_refusal_in_value(nested_value, seen_ids=seen_ids)
            if nested_refusal is not None:
                return nested_refusal

        return None

    if isinstance(value, list | tuple):
        for nested_value in value:
            nested_refusal = _find_refusal_in_value(nested_value, seen_ids=seen_ids)
            if nested_refusal is not None:
                return nested_refusal

        return None

    refusal_attr = getattr(value, "refusal", None)
    if isinstance(refusal_attr, str) and refusal_attr.strip():
        return refusal_attr.strip()

    for attribute_name in ("output", "content"):
        nested_value: Any = getattr(value, attribute_name, None)
        nested_refusal = _find_refusal_in_value(nested_value, seen_ids=seen_ids)
        if nested_refusal is not None:
            return nested_refusal

    return None
