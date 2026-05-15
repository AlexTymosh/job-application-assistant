from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from app.cv.models import AllowedClaimLevel, FactCategory


class StrictImportModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ImportAction(StrEnum):
    CREATE = "create"
    SKIP = "skip"
    CONFLICT = "conflict"


class PlannedCvBlock(StrictImportModel):
    block_key: str
    display_order: int = 0
    content_markdown: str
    is_enabled: bool = True
    action: ImportAction
    message: str | None = None


class PlannedCvSection(StrictImportModel):
    section_key: str
    title: str
    display_order: int
    is_required: bool
    action: ImportAction
    message: str | None = None
    blocks: list[PlannedCvBlock] = Field(default_factory=list)


class PlannedCvVariant(StrictImportModel):
    name: str
    display_name: str
    source_filename: str
    action: ImportAction
    message: str | None = None
    sections: list[PlannedCvSection] = Field(default_factory=list)


class PlannedFact(StrictImportModel):
    fact_key: str
    category: FactCategory
    name: str
    allowed_claim_level: AllowedClaimLevel
    evidence: str
    is_active: bool = True
    action: ImportAction
    message: str | None = None


class ImportTotals(StrictImportModel):
    variants_create: int = 0
    variants_skip: int = 0
    sections_create: int = 0
    sections_skip: int = 0
    blocks_create: int = 0
    blocks_skip: int = 0
    facts_create: int = 0
    facts_skip: int = 0
    conflicts: int = 0


class ImportPreview(StrictImportModel):
    source_profile_id: str
    source_profile_name: str
    source_profile_path: Path
    source_profile_path_label: str
    cv_variants: list[PlannedCvVariant]
    facts: list[PlannedFact]
    conflicts: list[str]
    apply_allowed: bool
    totals: ImportTotals


class ImportApplyResult(StrictImportModel):
    preview: ImportPreview
    created_variants: int = 0
    created_sections: int = 0
    created_blocks: int = 0
    created_facts: int = 0
