from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from starlette.datastructures import FormData

from app.core.config import LlmExtractionMode
from app.settings.schema import (
    SETTING_DEFAULT_PROFILE_DATA_DIR,
    SETTING_DEFAULT_PROFILE_NAME,
    SETTING_EXPORT_DOCX,
    SETTING_EXPORT_HTML,
    SETTING_EXPORT_MARKDOWN,
    SETTING_EXPORT_PDF,
    SETTING_LLM_EXTRACTION_MODE,
    SETTING_REQUIRE_HUMAN_APPROVAL,
    ManagedAppSettings,
)
from app.settings.service import AppSettingsService

_SETTINGS_FORM_FIELDS = frozenset(
    {
        SETTING_LLM_EXTRACTION_MODE,
        SETTING_REQUIRE_HUMAN_APPROVAL,
        SETTING_EXPORT_MARKDOWN,
        SETTING_EXPORT_HTML,
        SETTING_EXPORT_PDF,
        SETTING_EXPORT_DOCX,
        SETTING_DEFAULT_PROFILE_NAME,
        SETTING_DEFAULT_PROFILE_DATA_DIR,
    }
)
_CHECKBOX_FIELDS = frozenset(
    {
        SETTING_REQUIRE_HUMAN_APPROVAL,
        SETTING_EXPORT_MARKDOWN,
        SETTING_EXPORT_HTML,
        SETTING_EXPORT_PDF,
        SETTING_EXPORT_DOCX,
    }
)
_TRUE_VALUES = frozenset({"1", "true", "on", "yes"})
_FALSE_VALUES = frozenset({"0", "false", "off", "no"})
_SECRET_FORM_FRAGMENTS = ("api_key", "token", "secret")


@dataclass(frozen=True)
class SettingsFormResult:
    settings: ManagedAppSettings
    clear_default_profile_selection: bool


class SettingsFormError(ValueError):
    """Raised when submitted settings form data is invalid."""


def parse_settings_form(form: FormData | dict[str, Any]) -> SettingsFormResult:
    submitted = {str(key): value for key, value in form.items()}
    _reject_secret_form_fields(submitted)

    llm_mode = _parse_llm_mode(submitted.get(SETTING_LLM_EXTRACTION_MODE))
    default_profile_name = _normalise_optional_string(
        submitted.get(SETTING_DEFAULT_PROFILE_NAME)
    )
    default_profile_data_dir = _normalise_optional_string(
        submitted.get(SETTING_DEFAULT_PROFILE_DATA_DIR)
    )

    if bool(default_profile_name) != bool(default_profile_data_dir):
        raise SettingsFormError(
            "Default profile name and data directory must be provided together."
        )

    unknown_fields = sorted(set(submitted) - _SETTINGS_FORM_FIELDS)
    if unknown_fields:
        raise SettingsFormError(
            "Unsupported settings form field: " + ", ".join(unknown_fields)
        )

    checkbox_values = {
        key: _parse_checkbox(key, submitted.get(key)) for key in _CHECKBOX_FIELDS
    }

    return SettingsFormResult(
        settings=ManagedAppSettings(
            llm_extraction_mode=llm_mode,
            require_human_approval_before_export=checkbox_values[
                SETTING_REQUIRE_HUMAN_APPROVAL
            ],
            export_markdown=checkbox_values[SETTING_EXPORT_MARKDOWN],
            export_html=checkbox_values[SETTING_EXPORT_HTML],
            export_pdf=checkbox_values[SETTING_EXPORT_PDF],
            export_docx=checkbox_values[SETTING_EXPORT_DOCX],
            default_profile_name=default_profile_name,
            default_profile_data_dir=(
                Path(default_profile_data_dir) if default_profile_data_dir else None
            ),
        ),
        clear_default_profile_selection=(
            default_profile_name is None and default_profile_data_dir is None
        ),
    )


def persist_settings_form(
    service: AppSettingsService,
    result: SettingsFormResult,
) -> None:
    service.save_managed_settings(result.settings)
    if result.clear_default_profile_selection:
        service.delete_setting(SETTING_DEFAULT_PROFILE_NAME)
        service.delete_setting(SETTING_DEFAULT_PROFILE_DATA_DIR)


def _parse_llm_mode(value: Any) -> LlmExtractionMode:
    normalised = _normalise_required_string(value, "LLM extraction mode")
    try:
        return LlmExtractionMode(normalised)
    except ValueError as exc:
        raise SettingsFormError(
            "Unsupported LLM extraction mode. Choose fake or openai."
        ) from exc


def _parse_checkbox(key: str, value: Any) -> bool:
    if value is None:
        return False
    normalised = _normalise_required_string(value, key).lower()
    if normalised in _TRUE_VALUES:
        return True
    if normalised in _FALSE_VALUES:
        return False
    raise SettingsFormError(f"Invalid boolean value for {key}.")


def _normalise_optional_string(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise SettingsFormError("Settings form values must be strings.")
    stripped = value.strip()
    return stripped or None


def _normalise_required_string(value: Any, label: str) -> str:
    normalised = _normalise_optional_string(value)
    if normalised is None:
        raise SettingsFormError(f"{label} is required.")
    return normalised


def _reject_secret_form_fields(submitted: dict[str, Any]) -> None:
    secret_fields = [
        key
        for key in submitted
        if any(fragment in key.lower() for fragment in _SECRET_FORM_FRAGMENTS)
    ]
    if secret_fields:
        raise SettingsFormError(
            "Raw secrets are not accepted on this page: " + ", ".join(secret_fields)
        )
