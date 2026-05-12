from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from app.db.models import Application
from app.db.repositories import (
    ApplicationEventRepository,
    ApplicationRepository,
    ApplicationWarningRepository,
    ArtifactRepository,
)
from app.jobs.input_models import JobInput
from app.jobs.service import JobInputService
from app.preflight.persistence import persist_preflight_warnings
from app.preflight.service import PreflightResult, PreflightService


@dataclass(frozen=True)
class ApplicationIntakeResult:
    application: Application
    preflight: PreflightResult


class ApplicationIntakeService:
    def __init__(
        self,
        *,
        session: Session,
        blacklist_path: Path,
        applications_dir: Path,
    ) -> None:
        self._session = session
        self._blacklist_path = blacklist_path
        self._applications_dir = applications_dir

    def create_application_from_job_input(
        self,
        *,
        profile_name: str,
        selected_cv_variant: str,
        job_input: JobInput,
    ) -> ApplicationIntakeResult:
        applications = ApplicationRepository(self._session)
        artifacts = ArtifactRepository(self._session)
        events = ApplicationEventRepository(self._session)
        warnings = ApplicationWarningRepository(self._session)

        job_input_service = JobInputService(
            applications=applications,
            artifacts=artifacts,
            events=events,
            applications_dir=self._applications_dir,
        )

        application = job_input_service.create_from_input(
            profile_name=profile_name,
            selected_cv_variant=selected_cv_variant,
            job_input=job_input,
        )

        preflight_service = PreflightService(
            session=self._session,
            blacklist_path=self._blacklist_path,
        )

        preflight_result = preflight_service.check(
            profile_name=profile_name,
            job_text=job_input.manual_text or "",
            job_text_hash=application.job_text_hash,
            exclude_application_id=application.id,
        )

        persist_preflight_warnings(
            warnings=warnings,
            application_id=application.id,
            result=preflight_result,
        )

        return ApplicationIntakeResult(
            application=application,
            preflight=preflight_result,
        )
