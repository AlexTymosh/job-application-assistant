from pathlib import Path
from uuid import UUID

from app.artifacts.paths import (
    build_application_artifact_dir,
    build_raw_job_text_path,
    build_raw_job_text_relative_path,
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
