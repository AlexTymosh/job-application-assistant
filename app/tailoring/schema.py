from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

TargetType = Literal[
    "summary", "skills", "work_experience_bullets", "education_achievements"
]
Operation = Literal["rewrite", "create", "hide", "reorder"]
RiskLevel = Literal["low", "medium", "high"]


class AiChangeProposalSchema(BaseModel):
    target_type: TargetType
    target_id: int = Field(gt=0)
    operation: Operation
    before_text: str
    after_text: str
    reason: str
    risk_level: RiskLevel = "low"
    requirement_ids: list[int] = Field(default_factory=list)
    master_cv_entry_ids: list[int] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @field_validator("after_text")
    @classmethod
    def after_text_required_for_content_changes(cls, value: str, info):  # type: ignore[no-untyped-def]
        operation = info.data.get("operation")
        if operation in {"rewrite", "create"} and not value.strip():
            raise ValueError("after_text is required for content-changing proposals.")
        return value
