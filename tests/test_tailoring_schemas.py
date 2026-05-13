import pytest
from pydantic import ValidationError

from app.cv.models import CvSectionName
from app.llm.tailoring_schemas import (
    CvChange,
    TailoringAction,
    TailoringResult,
    TailoringRiskLevel,
    TailoringWarning,
    TailoringWarningCode,
)


def build_change(**overrides: object) -> CvChange:
    data = {
        "section": CvSectionName.SUMMARY,
        "action": TailoringAction.REPLACE_SECTION,
        "before_text": "Original summary.",
        "after_text": "Tailored summary.",
        "reason": "Matched verified facts.",
        "job_requirement_ids": ["req_python"],
        "cv_fact_ids": ["fact_python_001"],
        "risk_level": TailoringRiskLevel.LOW,
    }
    data.update(overrides)
    return CvChange(**data)


def test_cv_change_rejects_replace_section_without_cv_fact_ids() -> None:
    with pytest.raises(ValidationError):
        build_change(cv_fact_ids=[])


def test_cv_change_rejects_empty_reason() -> None:
    with pytest.raises(ValidationError):
        build_change(reason="   ")


def test_cv_change_rejects_unchanged_replacement_text() -> None:
    with pytest.raises(ValidationError):
        build_change(before_text="Same text.", after_text="  Same text.  ")


def test_tailoring_result_rejects_empty_tailored_markdown() -> None:
    with pytest.raises(ValidationError):
        TailoringResult(
            tailored_markdown="   ",
            changes=[build_change()],
        )


def test_tailoring_warning_trims_message_and_removes_empty_fact_ids() -> None:
    warning = TailoringWarning(
        code=TailoringWarningCode.NO_RELEVANT_REQUIREMENT,
        message="  No matching fact.  ",
        fact_ids=[" fact_python_001 ", "", "   "],
    )

    assert warning.message == "No matching fact."
    assert warning.fact_ids == ["fact_python_001"]


def test_unknown_extra_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        TailoringWarning.model_validate(
            {
                "code": "other",
                "message": "Warning.",
                "unexpected": "value",
            }
        )
