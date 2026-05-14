"""add human-facing application numbers

Revision ID: 0003_add_application_numbers
Revises: 0002_add_application_artifact_dir_name
Create Date: 2026-05-14 12:00:00.000000
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from datetime import datetime

import sqlalchemy as sa

from alembic import op

revision: str = "0003_add_application_numbers"
down_revision: str | None = "0002_add_application_artifact_dir_name"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MAX_ARTIFACT_DIR_NAME_LENGTH = 160
MAX_COMPANY_SLUG_LENGTH = 48
MAX_ROLE_SLUG_LENGTH = 64
APPLICATION_NUMBER_WIDTH = 6
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


def upgrade() -> None:
    op.drop_index(op.f("ix_applications_artifact_dir_name"), table_name="applications")
    op.create_index(
        op.f("ix_applications_artifact_dir_name"),
        "applications",
        ["artifact_dir_name"],
        unique=False,
    )
    op.add_column(
        "applications",
        sa.Column("application_number", sa.Integer(), nullable=True),
    )

    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            """
            SELECT
                id, profile_name, created_at, company_name, job_title,
                artifact_dir_name
            FROM applications
            ORDER BY profile_name ASC, created_at ASC, id ASC
            """
        )
    ).mappings()

    next_numbers_by_profile: dict[str, int] = {}
    for row in rows:
        profile_name = row["profile_name"]
        application_number = next_numbers_by_profile.get(profile_name, 1)
        next_numbers_by_profile[profile_name] = application_number + 1

        bind.execute(
            sa.text(
                """
                UPDATE applications
                SET application_number = :application_number
                WHERE id = :application_id
                """
            ),
            {
                "application_number": application_number,
                "application_id": row["id"],
            },
        )

        if row["artifact_dir_name"] is None:
            bind.execute(
                sa.text(
                    """
                    UPDATE applications
                    SET artifact_dir_name = :artifact_dir_name
                    WHERE id = :application_id
                    """
                ),
                {
                    "artifact_dir_name": _build_application_artifact_dir_name(
                        created_at=row["created_at"],
                        application_number=application_number,
                        company_name=row["company_name"],
                        job_title=row["job_title"],
                    ),
                    "application_id": row["id"],
                },
            )

    op.create_index(
        "ix_applications_profile_name_application_number",
        "applications",
        ["profile_name", "application_number"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_applications_artifact_dir_name"), table_name="applications")
    op.create_index(
        op.f("ix_applications_artifact_dir_name"),
        "applications",
        ["artifact_dir_name"],
        unique=True,
    )
    op.drop_index(
        "ix_applications_profile_name_application_number",
        table_name="applications",
    )
    op.drop_column("applications", "application_number")


def _build_application_artifact_dir_name(
    *,
    created_at: object,
    application_number: int,
    company_name: str | None,
    job_title: str | None,
) -> str:
    timestamp = _format_timestamp(created_at)
    path_number = f"app-{application_number:0{APPLICATION_NUMBER_WIDTH}d}"
    company_slug = _slugify_artifact_part(
        company_name,
        fallback=UNKNOWN_COMPANY_SLUG,
        max_length=MAX_COMPANY_SLUG_LENGTH,
    )
    role_slug = _slugify_artifact_part(
        job_title,
        fallback=UNKNOWN_ROLE_SLUG,
        max_length=MAX_ROLE_SLUG_LENGTH,
    )
    return _fit_artifact_dir_name(
        timestamp=timestamp,
        company_slug=company_slug,
        role_slug=role_slug,
        path_number=path_number,
    )


def _format_timestamp(value: object) -> str:
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d_%H-%M-%S")
    if isinstance(value, str):
        return datetime.fromisoformat(value).strftime("%Y-%m-%d_%H-%M-%S")
    raise TypeError("created_at must be a datetime or ISO datetime string.")


def _slugify_artifact_part(value: str | None, fallback: str, max_length: int) -> str:
    fallback_slug = _normalise_slug(fallback) or "unknown"
    raw_value = value.strip() if value is not None else ""
    slug = _normalise_slug(raw_value) or fallback_slug
    slug = _avoid_reserved_windows_name(slug, fallback_slug)
    slug = _truncate_slug(slug, max_length)
    if not slug:
        slug = _truncate_slug(fallback_slug, max_length)
    return _avoid_reserved_windows_name(slug, fallback_slug)


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
    path_number: str,
) -> str:
    fixed_length = len(timestamp) + len(path_number) + (len(_SEPARATOR) * 3)
    available_for_slugs = MAX_ARTIFACT_DIR_NAME_LENGTH - fixed_length

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

    dir_name = _SEPARATOR.join(
        [
            timestamp,
            company_slug or UNKNOWN_COMPANY_SLUG,
            role_slug or UNKNOWN_ROLE_SLUG,
            path_number,
        ]
    )

    if len(dir_name) > MAX_ARTIFACT_DIR_NAME_LENGTH:
        raise ValueError("Application artefact directory name exceeds the limit.")

    return dir_name
