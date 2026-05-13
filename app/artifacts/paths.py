from __future__ import annotations

from pathlib import Path
from uuid import UUID

RAW_JOB_TEXT_FILENAME = "job_raw.txt"
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
