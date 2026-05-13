from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from app.llm.errors import (
    JobExtractionError,
    OpenAIExtractionRefusalError,
    OpenAIExtractionResponseError,
)
from app.llm.openai_client import OpenAIJobExtractionClient
from app.llm.schemas import (
    ExtractedJob,
    JobRequirement,
    RequirementCategory,
    RequirementPriority,
)


@dataclass
class FakeOpenAIResponse:
    output_parsed: object | None = None
    output: object | None = None


class FakeResponsesResource:
    def __init__(self, response: FakeOpenAIResponse) -> None:
        self._response = response
        self.calls: list[dict[str, Any]] = []

    def parse(self, **kwargs: Any) -> FakeOpenAIResponse:
        self.calls.append(kwargs)
        return self._response


class FakeOpenAIClient:
    def __init__(self, response: FakeOpenAIResponse) -> None:
        self.responses = FakeResponsesResource(response)


def build_extracted_job() -> ExtractedJob:
    return ExtractedJob(
        job_title="Backend Developer",
        company_name="Example Company",
        requirements=[
            JobRequirement(
                id="req_python",
                text="Work with Python.",
                priority=RequirementPriority.MUST_HAVE,
                category=RequirementCategory.PROGRAMMING_LANGUAGE,
                keywords=["Python"],
                source_excerpt="Work with Python.",
            )
        ],
        responsibilities=["Build backend APIs."],
        technologies=["Python"],
    )


def test_blank_input_raises_job_extraction_error() -> None:
    fake_sdk = FakeOpenAIClient(FakeOpenAIResponse(output_parsed=build_extracted_job()))
    client = OpenAIJobExtractionClient(model="gpt-test", client=fake_sdk)

    with pytest.raises(JobExtractionError):
        client.extract_job("   ")

    assert fake_sdk.responses.calls == []


def test_successful_mocked_structured_response_returns_extracted_job() -> None:
    extracted_job = build_extracted_job()
    fake_sdk = FakeOpenAIClient(FakeOpenAIResponse(output_parsed=extracted_job))
    client = OpenAIJobExtractionClient(model="gpt-test", client=fake_sdk)

    result = client.extract_job("Backend role requiring Python.")

    assert result == extracted_job
    assert fake_sdk.responses.calls[0]["model"] == "gpt-test"
    assert fake_sdk.responses.calls[0]["text_format"] is ExtractedJob
    assert fake_sdk.responses.calls[0]["input"][0]["role"] == "system"
    assert "untrusted data" in fake_sdk.responses.calls[0]["input"][0]["content"]


def test_parsed_dict_response_is_validated_into_extracted_job() -> None:
    fake_sdk = FakeOpenAIClient(
        FakeOpenAIResponse(output_parsed=build_extracted_job().model_dump(mode="json"))
    )
    client = OpenAIJobExtractionClient(model="gpt-test", client=fake_sdk)

    result = client.extract_job("Backend role requiring Python.")

    assert isinstance(result, ExtractedJob)
    assert result.job_title == "Backend Developer"


def test_refusal_response_raises_refusal_error() -> None:
    fake_sdk = FakeOpenAIClient(
        FakeOpenAIResponse(
            output_parsed=None,
            output=[{"content": [{"refusal": "I cannot comply."}]}],
        )
    )
    client = OpenAIJobExtractionClient(model="gpt-test", client=fake_sdk)

    with pytest.raises(OpenAIExtractionRefusalError):
        client.extract_job("Backend role requiring Python.")


def test_missing_parsed_output_raises_response_error() -> None:
    fake_sdk = FakeOpenAIClient(FakeOpenAIResponse(output_parsed=None))
    client = OpenAIJobExtractionClient(model="gpt-test", client=fake_sdk)

    with pytest.raises(OpenAIExtractionResponseError):
        client.extract_job("Backend role requiring Python.")


def test_malformed_parsed_output_raises_response_error() -> None:
    fake_sdk = FakeOpenAIClient(FakeOpenAIResponse(output_parsed="not structured"))
    client = OpenAIJobExtractionClient(model="gpt-test", client=fake_sdk)

    with pytest.raises(OpenAIExtractionResponseError):
        client.extract_job("Backend role requiring Python.")


def test_fake_injected_client_does_not_require_openai_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    fake_sdk = FakeOpenAIClient(FakeOpenAIResponse(output_parsed=build_extracted_job()))
    client = OpenAIJobExtractionClient(model="gpt-test", client=fake_sdk)

    result = client.extract_job("Backend role requiring Python.")

    assert result.requirements[0].id == "req_python"
    assert len(fake_sdk.responses.calls) == 1
