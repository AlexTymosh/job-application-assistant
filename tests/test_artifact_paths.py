from pathlib import Path

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

ARTIFACT_DIR_NAME = "2026-05-14_09-26-01__unknown-company__unknown-role__22222222"


def test_application_artifact_dir_is_built_from_applications_dir() -> None:
    applications_dir = Path("/private/profile/applications")

    assert build_application_artifact_dir(
        applications_dir=applications_dir,
        artifact_dir_name=ARTIFACT_DIR_NAME,
    ) == Path(f"/private/profile/applications/{ARTIFACT_DIR_NAME}")


def test_raw_job_text_paths_are_stable_and_privacy_safe() -> None:
    applications_dir = Path("/private/profile/applications")

    absolute_path = build_raw_job_text_path(
        applications_dir=applications_dir,
        artifact_dir_name=ARTIFACT_DIR_NAME,
    )
    relative_path = build_raw_job_text_relative_path(
        artifact_dir_name=ARTIFACT_DIR_NAME,
    )

    assert absolute_path == Path(
        f"/private/profile/applications/{ARTIFACT_DIR_NAME}/job_raw.txt"
    )
    assert relative_path == f"applications/{ARTIFACT_DIR_NAME}/job_raw.txt"
    assert "/private/profile" not in relative_path


def test_tailored_cv_markdown_paths_are_stable_and_privacy_safe() -> None:
    applications_dir = Path("/private/profile/applications")

    absolute_path = build_tailored_cv_markdown_path(
        applications_dir=applications_dir,
        artifact_dir_name=ARTIFACT_DIR_NAME,
    )
    relative_path = build_tailored_cv_markdown_relative_path(
        artifact_dir_name=ARTIFACT_DIR_NAME,
    )

    assert absolute_path == Path(
        f"/private/profile/applications/{ARTIFACT_DIR_NAME}/tailored_cv.md"
    )
    assert relative_path == f"applications/{ARTIFACT_DIR_NAME}/tailored_cv.md"
    assert "/private/profile" not in relative_path


def test_tailored_cv_html_paths_are_stable_and_privacy_safe() -> None:
    applications_dir = Path("/private/profile/applications")

    absolute_path = build_tailored_cv_html_path(
        applications_dir=applications_dir,
        artifact_dir_name=ARTIFACT_DIR_NAME,
    )
    relative_path = build_tailored_cv_html_relative_path(
        artifact_dir_name=ARTIFACT_DIR_NAME,
    )

    assert absolute_path == Path(
        f"/private/profile/applications/{ARTIFACT_DIR_NAME}/tailored_cv.html"
    )
    assert relative_path == f"applications/{ARTIFACT_DIR_NAME}/tailored_cv.html"
    assert "/private/profile" not in relative_path


def test_tailored_cv_pdf_paths_are_stable_and_privacy_safe() -> None:
    applications_dir = Path("/private/profile/applications")

    absolute_path = build_tailored_cv_pdf_path(
        applications_dir=applications_dir,
        artifact_dir_name=ARTIFACT_DIR_NAME,
    )
    relative_path = build_tailored_cv_pdf_relative_path(
        artifact_dir_name=ARTIFACT_DIR_NAME,
    )

    assert absolute_path == Path(
        f"/private/profile/applications/{ARTIFACT_DIR_NAME}/tailored_cv.pdf"
    )
    assert relative_path == f"applications/{ARTIFACT_DIR_NAME}/tailored_cv.pdf"
    assert "/private/profile" not in relative_path


def test_tailored_cv_docx_paths_are_stable_and_privacy_safe() -> None:
    applications_dir = Path("/private/profile/applications")

    absolute_path = build_tailored_cv_docx_path(
        applications_dir=applications_dir,
        artifact_dir_name=ARTIFACT_DIR_NAME,
    )
    relative_path = build_tailored_cv_docx_relative_path(
        artifact_dir_name=ARTIFACT_DIR_NAME,
    )

    assert absolute_path == Path(
        f"/private/profile/applications/{ARTIFACT_DIR_NAME}/tailored_cv.docx"
    )
    assert relative_path == f"applications/{ARTIFACT_DIR_NAME}/tailored_cv.docx"
    assert "/private/profile" not in relative_path
