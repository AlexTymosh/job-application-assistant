from __future__ import annotations

import os
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field


class StrictConfigModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AppConfig(StrictConfigModel):
    profile_name: str
    data_dir: Path


class WorkflowConfig(StrictConfigModel):
    require_human_approval_before_export: bool = True
    stop_on_blacklist: bool = True
    warn_on_duplicate: bool = True
    stop_on_prompt_injection: bool = False


class LlmExtractionMode(StrEnum):
    FAKE = "fake"
    OPENAI = "openai"


class LlmConfig(StrictConfigModel):
    provider: str = "openai"
    extraction_mode: LlmExtractionMode = LlmExtractionMode.FAKE
    model_extract: str | None = None
    model_tailor: str | None = None
    model_qa: str | None = None
    temperature_extract: float = 0.0
    temperature_tailor: float = 0.2
    temperature_qa: float = 0.0
    use_structured_outputs: bool = True


class CvConfig(StrictConfigModel):
    default_variant: str
    variants: list[str] = Field(default_factory=list)


class ExportConfig(StrictConfigModel):
    markdown: bool = True
    html: bool = True
    pdf: bool = True
    docx: bool = True


class GuardrailsConfig(StrictConfigModel):
    allow_new_skills: bool = False
    allow_fake_metrics: bool = False
    require_fact_ids: bool = True
    require_evidence_matrix: bool = True
    max_summary_words: int = 80
    british_english: bool = True


class JobReaderConfig(StrictConfigModel):
    allow_url_input: bool = True
    allow_manual_text_input: bool = True
    min_extracted_text_chars: int = 1200


class FutureIntegrationsConfig(StrictConfigModel):
    reed_api_enabled: bool = False
    auto_apply_enabled: bool = False


class ProjectConfig(StrictConfigModel):
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
    return resolve_project_path(profile_data_dir / filename)


def resolve_project_path(path: Path) -> Path:
    if path.is_absolute():
        return path

    return get_project_root() / path


def _apply_environment_overrides(loaded_data: dict[str, Any]) -> dict[str, Any]:
    llm_mode = os.getenv("LLM_EXTRACTION_MODE")
    if llm_mode is None or not llm_mode.strip():
        return loaded_data

    updated_data = dict(loaded_data)
    llm_data = dict(updated_data.get("llm") or {})
    llm_data["extraction_mode"] = llm_mode.strip()
    updated_data["llm"] = llm_data
    return updated_data


def _normalise_unresolved_env_placeholders(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _normalise_unresolved_env_placeholders(nested_value)
            for key, nested_value in value.items()
        }

    if isinstance(value, list):
        return [_normalise_unresolved_env_placeholders(item) for item in value]

    if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
        return None

    return value


def load_profile_config(config_path: Path | None = None) -> ProjectConfig:
    resolved_path = (
        resolve_project_path(config_path) if config_path else get_default_config_path()
    )

    if not resolved_path.is_file():
        raise FileNotFoundError(f"Profile config file not found: {resolved_path}")

    raw_content = resolved_path.read_text(encoding="utf-8")
    expanded_content = os.path.expandvars(raw_content)
    loaded_data: dict[str, Any] = yaml.safe_load(expanded_content) or {}
    overridden_data = _apply_environment_overrides(loaded_data)
    normalised_data = _normalise_unresolved_env_placeholders(overridden_data)

    return ProjectConfig.model_validate(normalised_data)


def validate_llm_runtime_config(
    config: ProjectConfig,
    *,
    has_openai_api_key: bool | None = None,
) -> None:
    if config.llm.extraction_mode is LlmExtractionMode.FAKE:
        return

    if config.llm.extraction_mode is LlmExtractionMode.OPENAI:
        if not config.llm.model_extract:
            raise ValueError(
                "OpenAI extraction mode requires llm.model_extract or "
                "OPENAI_MODEL_EXTRACT to be configured."
            )

        if has_openai_api_key is None:
            api_key = os.getenv("OPENAI_API_KEY")
            has_openai_api_key = api_key is not None and bool(api_key.strip())
        if not has_openai_api_key:
            raise ValueError(
                "OpenAI extraction mode requires an OpenAI API key in the OS "
                "keyring or OPENAI_API_KEY environment fallback."
            )

        return

    raise ValueError(f"Unsupported LLM extraction mode: {config.llm.extraction_mode}")
