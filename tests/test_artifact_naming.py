from __future__ import annotations

from datetime import UTC, datetime

from app.artifacts.naming import (
    MAX_ARTIFACT_DIR_NAME_LENGTH,
    build_application_artifact_dir_name,
    format_application_display_number,
    format_application_path_number,
    slugify_artifact_part,
)

CREATED_AT = datetime(2026, 5, 14, 9, 26, 1, tzinfo=UTC)
APPLICATION_NUMBER = 1
UNSAFE_WINDOWS_CHARS = set('<>:"/\\|?*')


def test_application_artifact_dir_name_uses_normal_company_and_title() -> None:
    dir_name = build_application_artifact_dir_name(
        created_at=CREATED_AT,
        application_number=APPLICATION_NUMBER,
        company_name="IBM",
        job_title="Software Engineer",
    )

    assert "ibm__software-engineer" in dir_name


def test_application_artifact_dir_name_uses_unknown_fallbacks() -> None:
    dir_name = build_application_artifact_dir_name(
        created_at=CREATED_AT,
        application_number=APPLICATION_NUMBER,
        company_name=None,
        job_title=None,
    )

    assert "unknown-company__unknown-role" in dir_name


def test_slugify_removes_unsafe_windows_filename_characters() -> None:
    company_slug = slugify_artifact_part(
        "ACME:Cloud/AI*Team?",
        fallback="unknown-company",
        max_length=48,
    )
    role_slug = slugify_artifact_part(
        "Senior <Backend> Engineer",
        fallback="unknown-role",
        max_length=64,
    )

    assert company_slug == "acme-cloud-ai-team"
    assert role_slug == "senior-backend-engineer"
    assert not UNSAFE_WINDOWS_CHARS.intersection(company_slug)
    assert not UNSAFE_WINDOWS_CHARS.intersection(role_slug)


def test_slugify_collapses_repeated_spaces_and_separators() -> None:
    slug = slugify_artifact_part(
        "  Senior___Backend   Engineer -- Platform  ",
        fallback="unknown-role",
        max_length=64,
    )

    assert slug == "senior-backend-engineer-platform"


def test_long_company_and_role_names_are_truncated() -> None:
    company_slug = slugify_artifact_part("Company " * 20, "unknown-company", 24)
    role_slug = slugify_artifact_part(
        "Principal Backend Platform Engineer " * 20, "unknown-role", 32
    )

    assert len(company_slug) <= 24
    assert len(role_slug) <= 32
    assert not company_slug.endswith(("-", "."))
    assert not role_slug.endswith(("-", "."))


def test_final_directory_name_length_is_limited() -> None:
    dir_name = build_application_artifact_dir_name(
        created_at=CREATED_AT,
        application_number=APPLICATION_NUMBER,
        company_name="Very Long Company Name " * 30,
        job_title="Very Long Role Title " * 40,
    )

    assert len(dir_name) <= MAX_ARTIFACT_DIR_NAME_LENGTH


def test_application_number_suffix_is_preserved() -> None:
    dir_name = build_application_artifact_dir_name(
        created_at=CREATED_AT,
        application_number=APPLICATION_NUMBER,
        company_name="IBM",
        job_title="Software Engineer",
    )

    assert dir_name.endswith("app-000001")


def test_timestamp_prefix_is_preserved() -> None:
    dir_name = build_application_artifact_dir_name(
        created_at=CREATED_AT,
        application_number=APPLICATION_NUMBER,
        company_name="IBM",
        job_title="Software Engineer",
    )

    assert dir_name.startswith("2026-05-14_09-26-01__")


def test_directory_name_is_deterministic_for_same_inputs() -> None:
    first = build_application_artifact_dir_name(
        created_at=CREATED_AT,
        application_number=APPLICATION_NUMBER,
        company_name="IBM",
        job_title="Software Engineer",
    )
    second = build_application_artifact_dir_name(
        created_at=CREATED_AT,
        application_number=APPLICATION_NUMBER,
        company_name="IBM",
        job_title="Software Engineer",
    )

    assert first == second


def test_directory_name_does_not_end_with_hyphen_or_dot() -> None:
    dir_name = build_application_artifact_dir_name(
        created_at=CREATED_AT,
        application_number=APPLICATION_NUMBER,
        company_name="Example...---",
        job_title="Role...---",
    )

    assert not dir_name.endswith(("-", "."))


def test_application_number_formatters_are_stable() -> None:
    assert format_application_display_number(1) == "APP-000001"
    assert format_application_path_number(1) == "app-000001"
