from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RequirementPriority(StrEnum):
    MUST_HAVE = "must_have"
    NICE_TO_HAVE = "nice_to_have"
    UNKNOWN = "unknown"


class RequirementCategory(StrEnum):
    PROGRAMMING_LANGUAGE = "programming_language"
    FRAMEWORK = "framework"
    DATABASE = "database"
    CLOUD = "cloud"
    TESTING = "testing"
    DEVOPS = "devops"
    ARCHITECTURE = "architecture"
    COMMUNICATION = "communication"
    DOMAIN_KNOWLEDGE = "domain_knowledge"
    EDUCATION = "education"
    RESPONSIBILITY = "responsibility"
    OTHER = "other"


class SeniorityLevel(StrEnum):
    INTERNSHIP = "internship"
    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"
    LEAD = "lead"
    PRINCIPAL = "principal"
    UNKNOWN = "unknown"


class EmploymentType(StrEnum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    TEMPORARY = "temporary"
    INTERNSHIP = "internship"
    UNKNOWN = "unknown"


class WorkArrangement(StrEnum):
    ONSITE = "onsite"
    HYBRID = "hybrid"
    REMOTE = "remote"
    UNKNOWN = "unknown"


class ExtractionWarningCode(StrEnum):
    PROMPT_INJECTION_RISK = "prompt_injection_risk"
    INCOMPLETE_JOB_TEXT = "incomplete_job_text"
    AMBIGUOUS_REQUIREMENT = "ambiguous_requirement"
    MISSING_COMPANY_NAME = "missing_company_name"
    MISSING_JOB_TITLE = "missing_job_title"
    UNSUPPORTED_LANGUAGE = "unsupported_language"
    OTHER = "other"


class JobRequirement(StrictSchema):
    id: str
    text: str
    priority: RequirementPriority
    category: RequirementCategory
    keywords: list[str] = Field(default_factory=list)
    source_excerpt: str | None = None

    @field_validator("id", "text")
    @classmethod
    def require_non_empty_text(cls, value: str) -> str:
        normalised_value = value.strip()

        if not normalised_value:
            raise ValueError("Value must not be empty.")

        return normalised_value

    @field_validator("keywords")
    @classmethod
    def normalise_keywords(cls, value: list[str]) -> list[str]:
        normalised_keywords = [keyword.strip() for keyword in value]

        return [keyword for keyword in normalised_keywords if keyword]


class ExtractionWarning(StrictSchema):
    code: ExtractionWarningCode
    message: str
    source_excerpt: str | None = None

    @field_validator("message")
    @classmethod
    def require_message(cls, value: str) -> str:
        normalised_value = value.strip()

        if not normalised_value:
            raise ValueError("Warning message must not be empty.")

        return normalised_value


class ExtractedJob(StrictSchema):
    job_title: str | None = None
    company_name: str | None = None
    company_domain: str | None = None
    location: str | None = None
    salary_text: str | None = None
    employment_type: EmploymentType = EmploymentType.UNKNOWN
    seniority_level: SeniorityLevel = SeniorityLevel.UNKNOWN
    work_arrangement: WorkArrangement = WorkArrangement.UNKNOWN
    requirements: list[JobRequirement] = Field(min_length=1)
    responsibilities: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    warnings: list[ExtractionWarning] = Field(default_factory=list)

    @field_validator("responsibilities", "technologies")
    @classmethod
    def normalise_string_list(cls, value: list[str]) -> list[str]:
        normalised_values = [item.strip() for item in value]

        return [item for item in normalised_values if item]
