from __future__ import annotations

from pathlib import Path

from app.db.models import Application
from app.db.repositories import (
    ApplicationEventRepository,
    ApplicationRepository,
    ArtifactRepository,
)
from app.jobs.hashing import build_job_text_hash
from app.jobs.input_models import JobInput
from app.jobs.normalisation import normalise_url


class JobInputService:
    def __init__(
        self,
        applications: ApplicationRepository,
        artifacts: ArtifactRepository,
        events: ApplicationEventRepository,
        applications_dir: Path,
    ) -> None:
        self._applications = applications
        self._artifacts = artifacts
        self._events = events
        self._applications_dir = applications_dir

    def create_from_input(
        self,
        *,
        profile_name: str,
        selected_cv_variant: str,
        job_input: JobInput,
    ) -> Application:
        manual_text = job_input.manual_text or ""
        job_text_hash = build_job_text_hash(manual_text) if manual_text else None
        source_url = str(job_input.source_url) if job_input.source_url else None

        application = self._applications.create(
            profile_name=profile_name,
            source_url=source_url,
            selected_cv_variant=selected_cv_variant,
        )

        application.normalized_url = normalise_url(source_url)
        application.job_text_hash = job_text_hash

        application_dir = self._applications_dir / str(application.id)
        application_dir.mkdir(parents=True, exist_ok=True)

        if manual_text:
            raw_job_path = application_dir / "job_raw.txt"
            raw_job_path.write_text(manual_text, encoding="utf-8")

            self._artifacts.create(
                application_id=application.id,
                artifact_type="job_raw",
                path=str(raw_job_path),
            )

        self._events.create(
            application_id=application.id,
            event_type="job_input_created",
            message="Job input record created.",
        )

        return application
