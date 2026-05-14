from __future__ import annotations

from pathlib import Path

RAW_JOB_TEXT_FILENAME = "job_raw.txt"
EXTRACTED_JOB_FILENAME = "extracted_job.json"
TAILORED_CV_MARKDOWN_FILENAME = "tailored_cv.md"
TAILORED_CV_HTML_FILENAME = "tailored_cv.html"
TAILORED_CV_PDF_FILENAME = "tailored_cv.pdf"
TAILORED_CV_DOCX_FILENAME = "tailored_cv.docx"
APPLICATIONS_ARTEFACT_ROOT = "applications"


def build_application_artifact_dir(
    *,
    applications_dir: Path,
    artifact_dir_name: str,
) -> Path:
    return applications_dir / artifact_dir_name


def build_raw_job_text_path(
    *,
    applications_dir: Path,
    artifact_dir_name: str,
) -> Path:
    return (
        build_application_artifact_dir(
            applications_dir=applications_dir,
            artifact_dir_name=artifact_dir_name,
        )
        / RAW_JOB_TEXT_FILENAME
    )


def build_raw_job_text_relative_path(*, artifact_dir_name: str) -> str:
    return f"{APPLICATIONS_ARTEFACT_ROOT}/{artifact_dir_name}/{RAW_JOB_TEXT_FILENAME}"


def build_extracted_job_path(
    *,
    applications_dir: Path,
    artifact_dir_name: str,
) -> Path:
    return (
        build_application_artifact_dir(
            applications_dir=applications_dir,
            artifact_dir_name=artifact_dir_name,
        )
        / EXTRACTED_JOB_FILENAME
    )


def build_extracted_job_relative_path(*, artifact_dir_name: str) -> str:
    return f"{APPLICATIONS_ARTEFACT_ROOT}/{artifact_dir_name}/{EXTRACTED_JOB_FILENAME}"


def build_tailored_cv_markdown_path(
    *,
    applications_dir: Path,
    artifact_dir_name: str,
) -> Path:
    return (
        build_application_artifact_dir(
            applications_dir=applications_dir,
            artifact_dir_name=artifact_dir_name,
        )
        / TAILORED_CV_MARKDOWN_FILENAME
    )


def build_tailored_cv_markdown_relative_path(*, artifact_dir_name: str) -> str:
    return (
        f"{APPLICATIONS_ARTEFACT_ROOT}/{artifact_dir_name}/"
        f"{TAILORED_CV_MARKDOWN_FILENAME}"
    )


def build_tailored_cv_html_path(
    *,
    applications_dir: Path,
    artifact_dir_name: str,
) -> Path:
    return (
        build_application_artifact_dir(
            applications_dir=applications_dir,
            artifact_dir_name=artifact_dir_name,
        )
        / TAILORED_CV_HTML_FILENAME
    )


def build_tailored_cv_html_relative_path(*, artifact_dir_name: str) -> str:
    return (
        f"{APPLICATIONS_ARTEFACT_ROOT}/{artifact_dir_name}/{TAILORED_CV_HTML_FILENAME}"
    )


def build_tailored_cv_pdf_path(
    *,
    applications_dir: Path,
    artifact_dir_name: str,
) -> Path:
    return (
        build_application_artifact_dir(
            applications_dir=applications_dir,
            artifact_dir_name=artifact_dir_name,
        )
        / TAILORED_CV_PDF_FILENAME
    )


def build_tailored_cv_pdf_relative_path(*, artifact_dir_name: str) -> str:
    return (
        f"{APPLICATIONS_ARTEFACT_ROOT}/{artifact_dir_name}/{TAILORED_CV_PDF_FILENAME}"
    )


def build_tailored_cv_docx_path(
    *,
    applications_dir: Path,
    artifact_dir_name: str,
) -> Path:
    return (
        build_application_artifact_dir(
            applications_dir=applications_dir,
            artifact_dir_name=artifact_dir_name,
        )
        / TAILORED_CV_DOCX_FILENAME
    )


def build_tailored_cv_docx_relative_path(*, artifact_dir_name: str) -> str:
    return (
        f"{APPLICATIONS_ARTEFACT_ROOT}/{artifact_dir_name}/{TAILORED_CV_DOCX_FILENAME}"
    )
