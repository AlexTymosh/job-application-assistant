from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, field_validator

from app.core.config import LlmExtractionMode

SETTING_LLM_EXTRACTION_MODE = "llm.extraction_mode"
SETTING_REQUIRE_HUMAN_APPROVAL = "workflow.require_human_approval_before_export"
SETTING_EXPORT_MARKDOWN = "exports.markdown"
SETTING_EXPORT_HTML = "exports.html"
SETTING_EXPORT_PDF = "exports.pdf"
SETTING_EXPORT_DOCX = "exports.docx"
SETTING_DEFAULT_PROFILE_NAME = "profiles.default_profile_name"
SETTING_DEFAULT_PROFILE_DATA_DIR = "profiles.default_profile_data_dir"
SETTING_OPENAI_API_KEY_CONFIGURED = "secrets.openai_api_key_configured"

MANAGED_SETTING_KEYS = frozenset(
    {
        SETTING_LLM_EXTRACTION_MODE,
        SETTING_REQUIRE_HUMAN_APPROVAL,
        SETTING_EXPORT_MARKDOWN,
        SETTING_EXPORT_HTML,
        SETTING_EXPORT_PDF,
        SETTING_EXPORT_DOCX,
        SETTING_DEFAULT_PROFILE_NAME,
        SETTING_DEFAULT_PROFILE_DATA_DIR,
        SETTING_OPENAI_API_KEY_CONFIGURED,
    }
)

_SECRET_KEY_FRAGMENTS = ("api_key", "token", "secret")


class ManagedAppSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    llm_extraction_mode: LlmExtractionMode | None = None
    require_human_approval_before_export: bool | None = None
    export_markdown: bool | None = None
    export_html: bool | None = None
    export_pdf: bool | None = None
    export_docx: bool | None = None
    default_profile_name: str | None = None
    default_profile_data_dir: Path | None = None
    openai_api_key_configured: bool | None = None

    @field_validator("default_profile_name")
    @classmethod
    def validate_default_profile_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("Default profile name must not be blank.")
        return stripped


class StoredAppSetting(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: str
    value: Any


def validate_managed_setting_key(key: str) -> str:
    normalised_key = key.strip()
    if not normalised_key:
        raise ValueError("Setting key must not be blank.")
    if _is_forbidden_secret_key(normalised_key):
        raise ValueError(
            f"Setting key is reserved for secret storage: {normalised_key}"
        )
    if normalised_key not in MANAGED_SETTING_KEYS:
        raise ValueError(f"Unsupported managed app setting key: {normalised_key}")
    return normalised_key


def is_managed_setting_key(key: str) -> bool:
    return key in MANAGED_SETTING_KEYS


def key_to_model_field(key: str) -> str:
    return {
        SETTING_LLM_EXTRACTION_MODE: "llm_extraction_mode",
        SETTING_REQUIRE_HUMAN_APPROVAL: "require_human_approval_before_export",
        SETTING_EXPORT_MARKDOWN: "export_markdown",
        SETTING_EXPORT_HTML: "export_html",
        SETTING_EXPORT_PDF: "export_pdf",
        SETTING_EXPORT_DOCX: "export_docx",
        SETTING_DEFAULT_PROFILE_NAME: "default_profile_name",
        SETTING_DEFAULT_PROFILE_DATA_DIR: "default_profile_data_dir",
        SETTING_OPENAI_API_KEY_CONFIGURED: "openai_api_key_configured",
    }[key]


def model_field_to_key(field_name: str) -> str:
    return {
        "llm_extraction_mode": SETTING_LLM_EXTRACTION_MODE,
        "require_human_approval_before_export": SETTING_REQUIRE_HUMAN_APPROVAL,
        "export_markdown": SETTING_EXPORT_MARKDOWN,
        "export_html": SETTING_EXPORT_HTML,
        "export_pdf": SETTING_EXPORT_PDF,
        "export_docx": SETTING_EXPORT_DOCX,
        "default_profile_name": SETTING_DEFAULT_PROFILE_NAME,
        "default_profile_data_dir": SETTING_DEFAULT_PROFILE_DATA_DIR,
        "openai_api_key_configured": SETTING_OPENAI_API_KEY_CONFIGURED,
    }[field_name]


def value_kind_for_key(
    key: str,
) -> Literal["llm_mode", "bool", "string", "path"]:
    return {
        SETTING_LLM_EXTRACTION_MODE: "llm_mode",
        SETTING_REQUIRE_HUMAN_APPROVAL: "bool",
        SETTING_EXPORT_MARKDOWN: "bool",
        SETTING_EXPORT_HTML: "bool",
        SETTING_EXPORT_PDF: "bool",
        SETTING_EXPORT_DOCX: "bool",
        SETTING_DEFAULT_PROFILE_NAME: "string",
        SETTING_DEFAULT_PROFILE_DATA_DIR: "path",
        SETTING_OPENAI_API_KEY_CONFIGURED: "bool",
    }[key]


def serialise_setting_value(key: str, value: Any) -> Any:
    validate_managed_setting_key(key)
    if key == SETTING_OPENAI_API_KEY_CONFIGURED and not isinstance(value, bool):
        raise ValueError("OpenAI API key configured metadata must be a boolean.")
    kind = value_kind_for_key(key)
    if kind == "bool":
        if not isinstance(value, bool):
            raise ValueError(f"Setting {key} must be a boolean.")
        return value
    if kind == "llm_mode":
        return LlmExtractionMode(value).value
    if kind == "string":
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Setting {key} must be a non-blank string.")
        return value.strip()
    if kind == "path":
        if isinstance(value, Path):
            return value.expanduser().as_posix()
        if isinstance(value, str) and value.strip():
            return str(Path(value).expanduser())
        raise ValueError(f"Setting {key} must be a non-blank path.")
    raise ValueError(f"Unsupported setting value kind for {key}: {kind}")


def validate_stored_setting_value(key: str, value: Any) -> Any:
    serialised = serialise_setting_value(key, value)
    if value_kind_for_key(key) == "path":
        return Path(serialised)
    if value_kind_for_key(key) == "llm_mode":
        return LlmExtractionMode(serialised)
    return serialised


def _is_forbidden_secret_key(key: str) -> bool:
    if key == SETTING_OPENAI_API_KEY_CONFIGURED:
        return False
    lowered_key = key.lower()
    return any(fragment in lowered_key for fragment in _SECRET_KEY_FRAGMENTS)
