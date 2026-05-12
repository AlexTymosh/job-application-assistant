import pytest
from pydantic import ValidationError

from app.jobs.input_models import JobInput


def test_job_input_requires_url_or_manual_text() -> None:
    with pytest.raises(ValidationError):
        JobInput.model_validate({})


def test_job_input_rejects_short_manual_text() -> None:
    with pytest.raises(ValidationError):
        JobInput.model_validate({"manual_text": "too short"})


def test_job_input_accepts_manual_text() -> None:
    manual_text = "Python developer role. " * 20

    job_input = JobInput.model_validate({"manual_text": manual_text})

    assert job_input.manual_text == manual_text


def test_job_input_accepts_source_url() -> None:
    job_input = JobInput.model_validate(
        {"source_url": "https://example.com/jobs/backend-developer"}
    )

    assert str(job_input.source_url).startswith("https://example.com")


def test_job_input_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        JobInput.model_validate(
            {
                "manual_text": "Python developer role. " * 20,
                "unexpected": "value",
            }
        )
