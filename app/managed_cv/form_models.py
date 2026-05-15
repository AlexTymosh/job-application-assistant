from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from app.cv.models import AllowedClaimLevel, FactCategory


class ManagedCvEditorFormError(ValueError):
    """Raised when a managed CV editor form cannot be parsed safely."""


class CvBlockEditForm(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content_markdown: str
    display_order: int = Field(ge=0)
    is_enabled: bool = False
    selected_fact_ids: tuple[str, ...] = ()

    @field_validator("content_markdown")
    @classmethod
    def reject_blank_markdown(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("CV block markdown must not be empty.")
        return stripped

    @field_validator("selected_fact_ids")
    @classmethod
    def clean_fact_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        cleaned = tuple(dict.fromkeys(item.strip() for item in value if item.strip()))
        return cleaned


class FactCreateForm(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fact_key: str
    category: FactCategory
    name: str
    allowed_claim_level: AllowedClaimLevel
    evidence: str
    is_active: bool = False

    @field_validator("fact_key", "name", "evidence")
    @classmethod
    def reject_blank_required_text(cls, value: str) -> str:
        return _clean_required_text(value)


class FactEditForm(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: FactCategory
    name: str
    allowed_claim_level: AllowedClaimLevel
    evidence: str
    is_active: bool = False

    @field_validator("name", "evidence")
    @classmethod
    def reject_blank_required_text(cls, value: str) -> str:
        return _clean_required_text(value)


def parse_cv_block_edit_form(form: dict[str, str | list[str]]) -> CvBlockEditForm:
    try:
        return CvBlockEditForm(
            content_markdown=str(form.get("content_markdown", "")),
            display_order=int(str(form.get("display_order", ""))),
            is_enabled=_checkbox_value(form.get("is_enabled")),
            selected_fact_ids=_multi_value(form.get("selected_fact_ids")),
        )
    except (TypeError, ValueError, ValidationError) as exc:
        raise ManagedCvEditorFormError(_form_error_message(exc)) from exc


def parse_fact_create_form(form: dict[str, str | list[str]]) -> FactCreateForm:
    try:
        return FactCreateForm(
            fact_key=str(form.get("fact_key", "")),
            category=FactCategory(str(form.get("category", ""))),
            name=str(form.get("name", "")),
            allowed_claim_level=AllowedClaimLevel(
                str(form.get("allowed_claim_level", ""))
            ),
            evidence=str(form.get("evidence", "")),
            is_active=_checkbox_value(form.get("is_active")),
        )
    except (TypeError, ValueError, ValidationError) as exc:
        raise ManagedCvEditorFormError(_form_error_message(exc)) from exc


def parse_fact_edit_form(form: dict[str, str | list[str]]) -> FactEditForm:
    try:
        return FactEditForm(
            category=FactCategory(str(form.get("category", ""))),
            name=str(form.get("name", "")),
            allowed_claim_level=AllowedClaimLevel(
                str(form.get("allowed_claim_level", ""))
            ),
            evidence=str(form.get("evidence", "")),
            is_active=_checkbox_value(form.get("is_active")),
        )
    except (TypeError, ValueError, ValidationError) as exc:
        raise ManagedCvEditorFormError(_form_error_message(exc)) from exc


def _checkbox_value(value: str | list[str] | None) -> bool:
    if isinstance(value, list):
        return "on" in value
    return value == "on"


def _multi_value(value: str | list[str] | None) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, list):
        return tuple(value)
    return (value,)


def _clean_required_text(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError("Value must not be empty or whitespace-only.")
    return stripped


def _form_error_message(exc: Exception) -> str:
    if isinstance(exc, ValidationError):
        first = exc.errors()[0]
        location = ".".join(str(part) for part in first.get("loc", ()))
        message = str(first.get("msg", "Invalid form value."))
        return f"{location}: {message}" if location else message
    return str(exc) or "Invalid form value."
