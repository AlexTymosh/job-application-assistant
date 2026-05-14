from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.secrets.openai_key import OpenAISecretService, SecretStorageError
from app.settings.schema import SETTING_OPENAI_API_KEY_CONFIGURED
from app.settings.service import AppSettingsService

OPENAI_API_KEY_FORM_FIELD = "openai_api_key"
CLEAR_OPENAI_API_KEY_FORM_FIELD = "clear_openai_api_key"
_SECRET_FORM_FIELDS = frozenset(
    {OPENAI_API_KEY_FORM_FIELD, CLEAR_OPENAI_API_KEY_FORM_FIELD}
)
_TRUE_VALUES = frozenset({"1", "true", "on", "yes"})


@dataclass(frozen=True)
class OpenAISecretFormResult:
    has_secret_action: bool
    submitted_api_key: str | None = None
    clear_api_key: bool = False


class OpenAISecretFormError(ValueError):
    """Raised when submitted OpenAI secret form data is invalid."""


def split_openai_secret_form_fields(
    form: dict[str, Any],
) -> tuple[dict[str, Any], OpenAISecretFormResult]:
    settings_form = {
        key: value for key, value in form.items() if key not in _SECRET_FORM_FIELDS
    }
    submitted_api_key = _normalise_optional_string(form.get(OPENAI_API_KEY_FORM_FIELD))
    clear_api_key = _is_checked(form.get(CLEAR_OPENAI_API_KEY_FORM_FIELD))

    if submitted_api_key and clear_api_key:
        raise OpenAISecretFormError(
            "Choose either to save a new OpenAI API key or clear the stored key."
        )

    return settings_form, OpenAISecretFormResult(
        has_secret_action=submitted_api_key is not None or clear_api_key,
        submitted_api_key=submitted_api_key,
        clear_api_key=clear_api_key,
    )


def persist_openai_secret_form(
    *,
    app_settings_service: AppSettingsService,
    openai_secret_service: OpenAISecretService,
    result: OpenAISecretFormResult,
) -> None:
    try:
        if result.submitted_api_key is not None:
            openai_secret_service.set_api_key(result.submitted_api_key)
            app_settings_service.set_setting(SETTING_OPENAI_API_KEY_CONFIGURED, True)
            return

        if result.clear_api_key:
            openai_secret_service.delete_api_key()
            app_settings_service.set_setting(SETTING_OPENAI_API_KEY_CONFIGURED, False)
    except SecretStorageError:
        raise
    except ValueError as exc:
        raise OpenAISecretFormError(str(exc)) from exc


def _normalise_optional_string(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise OpenAISecretFormError("OpenAI API key form value must be a string.")
    stripped = value.strip()
    return stripped or None


def _is_checked(value: Any) -> bool:
    if value is None:
        return False
    if not isinstance(value, str):
        raise OpenAISecretFormError("Clear OpenAI API key value must be a string.")
    return value.strip().lower() in _TRUE_VALUES
