from __future__ import annotations

from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.llm.schemas import RequirementPriority


class StrictReportModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CoverageLevel(StrEnum):
    FULL = "full"
    PARTIAL = "partial"
    MISSING = "missing"
    NOT_APPLICABLE = "not_applicable"


class ReportRiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class EvidenceMatrixItem(StrictReportModel):
    requirement_id: str
    requirement_text: str
    requirement_priority: RequirementPriority
    coverage: CoverageLevel
    fact_ids: list[str] = Field(default_factory=list)
    matched_fact_names: list[str] = Field(default_factory=list)
    risk_level: ReportRiskLevel
    comment: str

    @field_validator("requirement_id", "requirement_text", "comment")
    @classmethod
    def require_non_empty_text(cls, value: str) -> str:
        normalised_value = value.strip()

        if not normalised_value:
            raise ValueError("Value must not be empty.")

        return normalised_value

    @field_validator("fact_ids", "matched_fact_names")
    @classmethod
    def normalise_non_empty_values(cls, value: list[str]) -> list[str]:
        normalised_values = [item.strip() for item in value]

        if any(not item for item in normalised_values):
            raise ValueError("ID and name lists must not contain empty values.")

        return normalised_values


class KeywordCoverageItem(StrictReportModel):
    keyword: str
    is_covered: bool
    source: str | None = None

    @field_validator("keyword")
    @classmethod
    def require_keyword(cls, value: str) -> str:
        normalised_value = value.strip()

        if not normalised_value:
            raise ValueError("Keyword must not be empty.")

        return normalised_value

    @field_validator("source")
    @classmethod
    def normalise_source(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalised_value = value.strip()
        return normalised_value or None


class MissingSkill(StrictReportModel):
    requirement_id: str
    requirement_text: str
    priority: RequirementPriority
    reason: str

    @field_validator("requirement_id", "requirement_text", "reason")
    @classmethod
    def require_non_empty_text(cls, value: str) -> str:
        normalised_value = value.strip()

        if not normalised_value:
            raise ValueError("Value must not be empty.")

        return normalised_value


class CvMatchReport(StrictReportModel):
    application_id: str
    overall_summary: str
    must_have_total: int = Field(ge=0)
    must_have_covered: int = Field(ge=0)
    nice_to_have_total: int = Field(ge=0)
    nice_to_have_covered: int = Field(ge=0)
    keyword_coverage: list[KeywordCoverageItem] = Field(default_factory=list)
    missing_skills: list[MissingSkill] = Field(default_factory=list)
    evidence_matrix: list[EvidenceMatrixItem] = Field(min_length=1)
    risk_level: ReportRiskLevel
    warnings: list[str] = Field(default_factory=list)

    @field_validator("application_id", "overall_summary")
    @classmethod
    def require_non_empty_text(cls, value: str) -> str:
        normalised_value = value.strip()

        if not normalised_value:
            raise ValueError("Value must not be empty.")

        return normalised_value

    @field_validator("warnings")
    @classmethod
    def normalise_warnings(cls, value: list[str]) -> list[str]:
        normalised_warnings = [warning.strip() for warning in value]

        return [warning for warning in normalised_warnings if warning]

    @model_validator(mode="after")
    def validate_counts(self) -> Self:
        if self.must_have_covered > self.must_have_total:
            raise ValueError("Covered must-have count cannot exceed total count.")

        if self.nice_to_have_covered > self.nice_to_have_total:
            raise ValueError("Covered nice-to-have count cannot exceed total count.")

        return self
