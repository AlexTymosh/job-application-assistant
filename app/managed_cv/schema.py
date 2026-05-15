from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.cv.models import AllowedClaimLevel, CvSectionName, FactCategory


class StrictManagedCvModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class ManagedCvVariantRecord(StrictManagedCvModel):
    id: str
    profile_id: str
    name: str
    display_name: str | None = None
    is_active: bool = True

    @field_validator("id", "profile_id", "name")
    @classmethod
    def reject_blank_required_text(cls, value: str) -> str:
        return _clean_required_text(value)

    @field_validator("display_name")
    @classmethod
    def clean_optional_text(cls, value: str | None) -> str | None:
        return _clean_optional_text(value)


class ManagedCvVariantAliasRecord(StrictManagedCvModel):
    id: str
    variant_id: str
    alias: str

    @field_validator("id", "variant_id", "alias")
    @classmethod
    def reject_blank_required_text(cls, value: str) -> str:
        return _clean_required_text(value)


class ManagedCvSectionRecord(StrictManagedCvModel):
    id: str
    variant_id: str
    section_key: str | CvSectionName
    title: str
    display_order: int = Field(ge=0)
    is_required: bool = False

    @field_validator("id", "variant_id", "section_key", "title")
    @classmethod
    def reject_blank_required_text(cls, value: str | CvSectionName) -> str:
        return _clean_required_text(
            str(value.value if hasattr(value, "value") else value)
        )


class ManagedCvBlockRecord(StrictManagedCvModel):
    id: str
    section_id: str
    block_key: str
    content_markdown: str
    display_order: int = Field(ge=0)
    is_enabled: bool = True

    @field_validator("id", "section_id", "block_key", "content_markdown")
    @classmethod
    def reject_blank_required_text(cls, value: str) -> str:
        return _clean_required_text(value)


class ManagedFactRecord(StrictManagedCvModel):
    id: str
    profile_id: str
    fact_key: str
    category: FactCategory
    name: str
    allowed_claim_level: AllowedClaimLevel
    evidence: str
    is_active: bool = True

    @field_validator("id", "profile_id", "fact_key", "name", "evidence")
    @classmethod
    def reject_blank_required_text(cls, value: str) -> str:
        return _clean_required_text(value)


class ManagedCvBlockFactLinkRecord(StrictManagedCvModel):
    block_id: str
    fact_id: str

    @field_validator("block_id", "fact_id")
    @classmethod
    def reject_blank_required_text(cls, value: str) -> str:
        return _clean_required_text(value)


def _clean_required_text(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError("Value must not be empty or whitespace-only.")
    return stripped


def _clean_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None
