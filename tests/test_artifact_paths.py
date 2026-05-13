from pathlib import Path
from uuid import UUID

from app.artifacts.paths import (
    build_application_artifact_dir,
    build_raw_job_text_path,
    build_raw_job_text_relative_path,
    build_tailored_cv_docx_path,
    build_tailored_cv_docx_relative_path,
    build_tailored_cv_html_path,
    build_tailored_cv_html_relative_path,
    build_tailored_cv_markdown_path,
    build_tailored_cv_markdown_relative_path,
    build_tailored_cv_pdf_path,
    build_tailored_cv_pdf_relative_path,
)


def test_application_artifact_dir_is_built_from_applications_dir() -> None:
    application_id = UUID("11111111-1111-1111-1111-111111111111")
    applications_dir = Path("/private/profile/applications")

    assert build_application_artifact_dir(
        applications_dir=applications_dir,
        application_id=application_id,
    ) == Path("/private/profile/applications/11111111-1111-1111-1111-111111111111")


def test_raw_job_text_paths_are_stable_and_privacy_safe() -> None:
    application_id = UUID("22222222-2222-2222-2222-222222222222")
    applications_dir = Path("/private/profile/applications")

    absolute_path = build_raw_job_text_path(
        applications_dir=applications_dir,
        application_id=application_id,
    )
    relative_path = build_raw_job_text_relative_path(application_id=application_id)

    assert absolute_path == Path(
        "/private/profile/applications/22222222-2222-2222-2222-222222222222/job_raw.txt"
    )
    assert (
        relative_path == "applications/22222222-2222-2222-2222-222222222222/job_raw.txt"
    )
    assert "/private/profile" not in relative_path


def test_tailored_cv_markdown_paths_are_stable_and_privacy_safe() -> None:
    application_id = UUID("44444444-4444-4444-4444-444444444444")
    applications_dir = Path("/private/profile/applications")

    absolute_path = build_tailored_cv_markdown_path(
        applications_dir=applications_dir,
        application_id=application_id,
    )
    relative_path = build_tailored_cv_markdown_relative_path(
        application_id=application_id,
    )

    assert absolute_path == Path(
        "/private/profile/applications/44444444-4444-4444-4444-444444444444/tailored_cv.md"
    )
    assert (
        relative_path
        == "applications/44444444-4444-4444-4444-444444444444/tailored_cv.md"
    )
    assert "/private/profile" not in relative_path


def test_tailored_cv_html_paths_are_stable_and_privacy_safe() -> None:
    application_id = UUID("55555555-5555-5555-5555-555555555555")
    applications_dir = Path("/private/profile/applications")

    absolute_path = build_tailored_cv_html_path(
        applications_dir=applications_dir,
        application_id=application_id,
    )
    relative_path = build_tailored_cv_html_relative_path(application_id=application_id)

    assert absolute_path == Path(
        "/private/profile/applications/55555555-5555-5555-5555-555555555555/tailored_cv.html"
    )
    assert (
        relative_path
        == "applications/55555555-5555-5555-5555-555555555555/tailored_cv.html"
    )
    assert "/private/profile" not in relative_path


def test_tailored_cv_pdf_paths_are_stable_and_privacy_safe() -> None:
    application_id = UUID("88888888-8888-8888-8888-888888888888")
    applications_dir = Path("/private/profile/applications")

    absolute_path = build_tailored_cv_pdf_path(
        applications_dir=applications_dir,
        application_id=application_id,
    )
    relative_path = build_tailored_cv_pdf_relative_path(application_id=application_id)

    assert absolute_path == Path(
        "/private/profile/applications/88888888-8888-8888-8888-888888888888/tailored_cv.pdf"
    )
    assert (
        relative_path
        == "applications/88888888-8888-8888-8888-888888888888/tailored_cv.pdf"
    )
    assert "/private/profile" not in relative_path


def test_tailored_cv_docx_paths_are_stable_and_privacy_safe() -> None:
    application_id = UUID("99999999-9999-9999-9999-999999999999")
    applications_dir = Path("/private/profile/applications")

    absolute_path = build_tailored_cv_docx_path(
        applications_dir=applications_dir,
        application_id=application_id,
    )
    relative_path = build_tailored_cv_docx_relative_path(application_id=application_id)

    assert absolute_path == Path(
        "/private/profile/applications/99999999-9999-9999-9999-999999999999/tailored_cv.docx"
    )
    assert (
        relative_path
        == "applications/99999999-9999-9999-9999-999999999999/tailored_cv.docx"
    )
    assert "/private/profile" not in relative_path
