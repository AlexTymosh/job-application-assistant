from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictCvModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CvSectionName(StrEnum):
    SUMMARY = "summary"
    SKILLS = "skills"
    EXPERIENCE = "experience"
    PROJECTS = "projects"


class FactCategory(StrEnum):
    SKILL = "skill"
    EXPERIENCE = "experience"
    PROJECT = "project"
    EDUCATION = "education"
    CERTIFICATION = "certification"
    LANGUAGE = "language"
    DOMAIN = "domain"
    OTHER = "other"


class AllowedClaimLevel(StrEnum):
    MENTION_ONLY = "mention_only"
    PRACTICAL = "practical"
    STRONG = "strong"
    DO_NOT_CLAIM = "do_not_claim"


class CvSection(StrictCvModel):
    name: CvSectionName
    start_marker: str
    end_marker: str
    content: str


class LoadedCv(StrictCvModel):
    path: Path
    markdown: str
    sections: dict[CvSectionName, CvSection]


class Fact(StrictCvModel):
    id: str
    category: FactCategory
    name: str
    allowed_claim_level: AllowedClaimLevel
    evidence: str

    @field_validator("id", "name", "evidence")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Value must not be empty or whitespace-only.")
        return value.strip()


class FactBank(StrictCvModel):
    facts: list[Fact] = Field(min_length=1)


class SelectedCvVariant(StrictCvModel):
    variant_name: str
    path: Path
    markdown: str
