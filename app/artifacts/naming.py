from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from uuid import UUID

MAX_COMPANY_SLUG_LENGTH = 48
MAX_ROLE_SLUG_LENGTH = 64
SHORT_ID_LENGTH = 8
MAX_ARTIFACT_DIR_NAME_LENGTH = 160

UNKNOWN_COMPANY_SLUG = "unknown-company"
UNKNOWN_ROLE_SLUG = "unknown-role"

_SEPARATOR = "__"
_UNSAFE_WINDOWS_FILENAME_CHARS = '<>:"/\\|?*'
_UNSAFE_TRANSLATION = str.maketrans(
    {char: "-" for char in _UNSAFE_WINDOWS_FILENAME_CHARS}
)
_CONTROL_CHAR_PATTERN = re.compile(r"[\x00-\x1f\x7f]")
_WHITESPACE_UNDERSCORE_PATTERN = re.compile(r"[\s_]+")
_HYPHEN_PATTERN = re.compile(r"-+")
_UNSUPPORTED_ASCII_PATTERN = re.compile(r"[^a-z0-9.-]+")
_WINDOWS_RESERVED_NAMES = {
    "con",
    "prn",
    "aux",
    "nul",
    *(f"com{number}" for number in range(1, 10)),
    *(f"lpt{number}" for number in range(1, 10)),
}


def slugify_artifact_part(value: str | None, fallback: str, max_length: int) -> str:
    """Return a Windows-safe, length-limited ASCII slug for an artefact path part."""

    if max_length < 1:
        raise ValueError("max_length must be at least 1.")

    fallback_slug = _normalise_slug(fallback) or "unknown"
    raw_value = value.strip() if value is not None else ""
    slug = _normalise_slug(raw_value) or fallback_slug
    slug = _avoid_reserved_windows_name(slug, fallback_slug)
    slug = _truncate_slug(slug, max_length)

    if not slug:
        slug = _truncate_slug(fallback_slug, max_length)

    return _avoid_reserved_windows_name(slug, fallback_slug)


def build_application_artifact_dir_name(
    *,
    created_at: datetime,
    application_id: UUID,
    company_name: str | None,
    job_title: str | None,
) -> str:
    """Build the stable human-readable artefact directory name for an application."""

    timestamp = created_at.strftime("%Y-%m-%d_%H-%M-%S")
    short_id = application_id.hex[:SHORT_ID_LENGTH]
    company_slug = slugify_artifact_part(
        company_name,
        fallback=UNKNOWN_COMPANY_SLUG,
        max_length=MAX_COMPANY_SLUG_LENGTH,
    )
    role_slug = slugify_artifact_part(
        job_title,
        fallback=UNKNOWN_ROLE_SLUG,
        max_length=MAX_ROLE_SLUG_LENGTH,
    )

    return _fit_artifact_dir_name(
        timestamp=timestamp,
        company_slug=company_slug,
        role_slug=role_slug,
        short_id=short_id,
    )


def _normalise_slug(value: str) -> str:
    normalised = unicodedata.normalize("NFKD", value.strip().lower())
    ascii_value = normalised.encode("ascii", "ignore").decode("ascii")
    ascii_value = ascii_value.translate(_UNSAFE_TRANSLATION)
    ascii_value = _CONTROL_CHAR_PATTERN.sub("", ascii_value)
    ascii_value = _WHITESPACE_UNDERSCORE_PATTERN.sub("-", ascii_value)
    ascii_value = _UNSUPPORTED_ASCII_PATTERN.sub("-", ascii_value)
    ascii_value = _HYPHEN_PATTERN.sub("-", ascii_value)
    return ascii_value.strip("-.")


def _truncate_slug(slug: str, max_length: int) -> str:
    if len(slug) <= max_length:
        return slug.strip("-.")
    return slug[:max_length].strip("-.")


def _avoid_reserved_windows_name(slug: str, fallback_slug: str) -> str:
    if slug.lower() not in _WINDOWS_RESERVED_NAMES:
        return slug

    replacement = f"{slug}-item".strip("-.")
    if replacement.lower() not in _WINDOWS_RESERVED_NAMES:
        return replacement
    return fallback_slug


def _fit_artifact_dir_name(
    *,
    timestamp: str,
    company_slug: str,
    role_slug: str,
    short_id: str,
) -> str:
    fixed_length = len(timestamp) + len(short_id) + (len(_SEPARATOR) * 3)
    available_for_slugs = MAX_ARTIFACT_DIR_NAME_LENGTH - fixed_length

    if available_for_slugs < len(UNKNOWN_COMPANY_SLUG) + len(UNKNOWN_ROLE_SLUG):
        raise ValueError(
            "MAX_ARTIFACT_DIR_NAME_LENGTH is too small for required parts."
        )

    if len(company_slug) + len(role_slug) > available_for_slugs:
        overflow = len(company_slug) + len(role_slug) - available_for_slugs
        role_slug = _truncate_slug(
            role_slug, max(len(UNKNOWN_ROLE_SLUG), len(role_slug) - overflow)
        )

    if len(company_slug) + len(role_slug) > available_for_slugs:
        overflow = len(company_slug) + len(role_slug) - available_for_slugs
        company_slug = _truncate_slug(
            company_slug,
            max(len(UNKNOWN_COMPANY_SLUG), len(company_slug) - overflow),
        )

    company_slug = company_slug or UNKNOWN_COMPANY_SLUG
    role_slug = role_slug or UNKNOWN_ROLE_SLUG
    dir_name = _SEPARATOR.join([timestamp, company_slug, role_slug, short_id])

    if len(dir_name) > MAX_ARTIFACT_DIR_NAME_LENGTH:
        raise ValueError("Application artefact directory name exceeds the limit.")

    return dir_name
