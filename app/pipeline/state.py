from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.llm.schemas import ExtractedJob
from app.llm.tailoring_schemas import CvChange


class ApplicationRunState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    application_id: str
    profile_name: str
    selected_cv_variant: str | None = None
    input_url: str | None = None
    manual_job_text: str | None = None
    job_text_hash: str | None = None
    extracted_job: ExtractedJob | None = None
    original_cv_markdown: str | None = None
    tailored_cv_markdown: str | None = None
    cv_changes: list[CvChange] = Field(default_factory=list)
    tailoring_warning_codes: list[str] = Field(default_factory=list)
    warning_codes: list[str] = Field(default_factory=list)
    artifact_paths: list[str] = Field(default_factory=list)
    status: str = "draft"
