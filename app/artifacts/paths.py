from __future__ import annotations

from pathlib import Path
from uuid import UUID

RAW_JOB_TEXT_FILENAME = "job_raw.txt"
EXTRACTED_JOB_FILENAME = "extracted_job.json"
TAILORED_CV_MARKDOWN_FILENAME = "tailored_cv.md"
TAILORED_CV_HTML_FILENAME = "tailored_cv.html"
APPLICATIONS_ARTEFACT_ROOT = "applications"


def build_application_artifact_dir(
    *,
    applications_dir: Path,
    application_id: UUID,
) -> Path:
    return applications_dir / str(application_id)


def build_raw_job_text_path(
    *,
    applications_dir: Path,
    application_id: UUID,
) -> Path:
    return (
        build_application_artifact_dir(
            applications_dir=applications_dir,
            application_id=application_id,
        )
        / RAW_JOB_TEXT_FILENAME
    )


def build_raw_job_text_relative_path(*, application_id: UUID) -> str:
    return f"{APPLICATIONS_ARTEFACT_ROOT}/{application_id}/{RAW_JOB_TEXT_FILENAME}"


def build_extracted_job_path(
    *,
    applications_dir: Path,
    application_id: UUID,
) -> Path:
    return (
        build_application_artifact_dir(
            applications_dir=applications_dir,
            application_id=application_id,
        )
        / EXTRACTED_JOB_FILENAME
    )


def build_extracted_job_relative_path(*, application_id: UUID) -> str:
    return f"{APPLICATIONS_ARTEFACT_ROOT}/{application_id}/{EXTRACTED_JOB_FILENAME}"


def build_tailored_cv_markdown_path(
    *,
    applications_dir: Path,
    application_id: UUID,
) -> Path:
    return (
        build_application_artifact_dir(
            applications_dir=applications_dir,
            application_id=application_id,
        )
        / TAILORED_CV_MARKDOWN_FILENAME
    )


def build_tailored_cv_markdown_relative_path(*, application_id: UUID) -> str:
    return (
        f"{APPLICATIONS_ARTEFACT_ROOT}/{application_id}/{TAILORED_CV_MARKDOWN_FILENAME}"
    )


def build_tailored_cv_html_path(
    *,
    applications_dir: Path,
    application_id: UUID,
) -> Path:
    return (
        build_application_artifact_dir(
            applications_dir=applications_dir,
            application_id=application_id,
        )
        / TAILORED_CV_HTML_FILENAME
    )


def build_tailored_cv_html_relative_path(*, application_id: UUID) -> str:
    return f"{APPLICATIONS_ARTEFACT_ROOT}/{application_id}/{TAILORED_CV_HTML_FILENAME}"
