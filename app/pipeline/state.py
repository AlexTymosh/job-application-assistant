from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.llm.schemas import ExtractedJob


class ApplicationRunState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    application_id: str
    profile_name: str
    selected_cv_variant: str | None = None
    input_url: str | None = None
    manual_job_text: str | None = None
    job_text_hash: str | None = None
    extracted_job: ExtractedJob | None = None
    warning_codes: list[str] = Field(default_factory=list)
    artifact_paths: list[str] = Field(default_factory=list)
    status: str = "draft"
