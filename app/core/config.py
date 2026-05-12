from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class AppConfig(BaseModel):
    profile_name: str
    data_dir: Path


class WorkflowConfig(BaseModel):
    require_human_approval_before_export: bool = True
    stop_on_blacklist: bool = True
    warn_on_duplicate: bool = True
    stop_on_prompt_injection: bool = False


class LlmConfig(BaseModel):
    provider: str = "openai"
    model_extract: str | None = None
    model_tailor: str | None = None
    model_qa: str | None = None
    temperature_extract: float = 0.0
    temperature_tailor: float = 0.2
    temperature_qa: float = 0.0
    use_structured_outputs: bool = True


class CvConfig(BaseModel):
    default_variant: str
    variants: list[str] = Field(default_factory=list)


class ExportConfig(BaseModel):
    markdown: bool = True
    html: bool = True
    pdf: bool = True
    docx: bool = True


class GuardrailsConfig(BaseModel):
    allow_new_skills: bool = False
    allow_fake_metrics: bool = False
    require_fact_ids: bool = True
    require_evidence_matrix: bool = True
    max_summary_words: int = 80
    british_english: bool = True


class JobReaderConfig(BaseModel):
    allow_url_input: bool = True
    allow_manual_text_input: bool = True
    min_extracted_text_chars: int = 1200


class FutureIntegrationsConfig(BaseModel):
    reed_api_enabled: bool = False
    auto_apply_enabled: bool = False


class ProjectConfig(BaseModel):
    app: AppConfig
    workflow: WorkflowConfig
    llm: LlmConfig
    cv: CvConfig
    exports: ExportConfig
    guardrails: GuardrailsConfig
    job_reader: JobReaderConfig
    future_integrations: FutureIntegrationsConfig


def get_project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def get_default_config_path() -> Path:
    profile_name = os.getenv("PROFILE_NAME", "example")
    profile_data_dir = Path(os.getenv("PROFILE_DATA_DIR", f"profiles/{profile_name}"))

    filename = "config.example.yaml" if profile_name == "example" else "config.yaml"
    return get_project_root() / profile_data_dir / filename


def load_profile_config(config_path: Path | None = None) -> ProjectConfig:
    resolved_path = config_path or get_default_config_path()

    if not resolved_path.is_file():
        raise FileNotFoundError(f"Profile config file not found: {resolved_path}")

    raw_content = resolved_path.read_text(encoding="utf-8")
    expanded_content = os.path.expandvars(raw_content)
    loaded_data: dict[str, Any] = yaml.safe_load(expanded_content) or {}

    return ProjectConfig.model_validate(loaded_data)
