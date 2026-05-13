from __future__ import annotations

from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.cv.models import CvSectionName


class StrictTailoringSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TailoringRiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TailoringAction(StrEnum):
    REPLACE_SECTION = "replace_section"
    KEEP_SECTION = "keep_section"
    ADD_WARNING = "add_warning"


class TailoringWarningCode(StrEnum):
    MISSING_FACT_ID = "missing_fact_id"
    UNKNOWN_FACT_ID = "unknown_fact_id"
    UNSAFE_CLAIM = "unsafe_claim"
    UNSUPPORTED_SECTION = "unsupported_section"
    EMPTY_TAILORED_TEXT = "empty_tailored_text"
    NO_RELEVANT_REQUIREMENT = "no_relevant_requirement"
    OTHER = "other"


class TailoringWarning(StrictTailoringSchema):
    code: TailoringWarningCode
    message: str
    section: CvSectionName | None = None
    fact_ids: list[str] = Field(default_factory=list)

    @field_validator("message")
    @classmethod
    def require_message(cls, value: str) -> str:
        normalised_value = value.strip()

        if not normalised_value:
            raise ValueError("Warning message must not be empty.")

        return normalised_value

    @field_validator("fact_ids")
    @classmethod
    def normalise_fact_ids(cls, value: list[str]) -> list[str]:
        normalised_fact_ids = [fact_id.strip() for fact_id in value]

        return [fact_id for fact_id in normalised_fact_ids if fact_id]


class CvChange(StrictTailoringSchema):
    section: CvSectionName
    action: TailoringAction
    before_text: str
    after_text: str
    reason: str
    job_requirement_ids: list[str]
    cv_fact_ids: list[str]
    risk_level: TailoringRiskLevel

    @field_validator("before_text", "after_text", "reason")
    @classmethod
    def require_non_empty_text(cls, value: str) -> str:
        normalised_value = value.strip()

        if not normalised_value:
            raise ValueError("Value must not be empty.")

        return normalised_value

    @field_validator("job_requirement_ids", "cv_fact_ids")
    @classmethod
    def normalise_non_empty_ids(cls, value: list[str]) -> list[str]:
        normalised_values = [item.strip() for item in value]

        if any(not item for item in normalised_values):
            raise ValueError("ID lists must not contain empty values.")

        return normalised_values

    @model_validator(mode="after")
    def validate_replacement_safety(self) -> Self:
        if self.action is not TailoringAction.REPLACE_SECTION:
            return self

        if not self.cv_fact_ids:
            raise ValueError("Replacement changes must reference at least one fact ID.")

        if self.before_text.strip() == self.after_text.strip():
            raise ValueError("Replacement changes must alter the section text.")

        return self


class TailoringResult(StrictTailoringSchema):
    tailored_markdown: str
    changes: list[CvChange]
    warnings: list[TailoringWarning] = Field(default_factory=list)

    @field_validator("tailored_markdown")
    @classmethod
    def require_tailored_markdown(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Tailored Markdown must not be empty.")

        return value

    @model_validator(mode="after")
    def validate_result_safety(self) -> Self:
        if not self.changes and not self.warnings:
            raise ValueError("Warnings are required when no CV changes were made.")

        for change in self.changes:
            if (
                change.action is TailoringAction.REPLACE_SECTION
                and not change.cv_fact_ids
            ):
                raise ValueError(
                    "Every replacement change must reference at least one fact ID."
                )

        return self
