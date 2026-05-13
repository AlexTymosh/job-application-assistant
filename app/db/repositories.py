from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import (
    Application,
    ApplicationEvent,
    ApplicationStatus,
    ApplicationWarning,
    Artifact,
    WarningLevel,
)


class ApplicationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        profile_name: str,
        job_title: str | None = None,
        company_name: str | None = None,
        source_url: str | None = None,
        selected_cv_variant: str | None = None,
    ) -> Application:
        application = Application(
            profile_name=profile_name,
            status=ApplicationStatus.DRAFT.value,
            job_title=job_title,
            company_name=company_name,
            source_url=source_url,
            selected_cv_variant=selected_cv_variant,
        )

        self._session.add(application)
        self._session.flush()

        return application

    def get(self, application_id: UUID) -> Application | None:
        return self._session.get(Application, application_id)

    def get_with_related(self, application_id: UUID) -> Application | None:
        statement = (
            select(Application)
            .where(Application.id == application_id)
            .options(
                selectinload(Application.artifacts),
                selectinload(Application.events),
                selectinload(Application.warnings),
            )
        )

        return self._session.scalars(statement).one_or_none()

    def list_dashboard_by_profile(self, profile_name: str) -> list[Application]:
        statement = (
            select(Application)
            .where(Application.profile_name == profile_name)
            .options(
                selectinload(Application.artifacts),
                selectinload(Application.warnings),
            )
            .order_by(Application.created_at.desc())
        )

        return list(self._session.scalars(statement).all())

    def list_by_profile(self, profile_name: str) -> list[Application]:
        statement = (
            select(Application)
            .where(Application.profile_name == profile_name)
            .order_by(Application.created_at.desc())
        )

        return list(self._session.scalars(statement).all())

    def update_status(
        self,
        *,
        application_id: UUID,
        status: ApplicationStatus,
    ) -> Application:
        application = self._session.get(Application, application_id)

        if application is None:
            raise ValueError(f"Application not found: {application_id}")

        application.status = status.value
        self._session.flush()

        return application


class ArtifactRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        application_id: UUID,
        artifact_type: str,
        path: str,
    ) -> Artifact:
        artifact = Artifact(
            application_id=application_id,
            artifact_type=artifact_type,
            path=path,
        )

        self._session.add(artifact)
        self._session.flush()

        return artifact


class ApplicationEventRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        application_id: UUID,
        event_type: str,
        message: str | None = None,
    ) -> ApplicationEvent:
        event = ApplicationEvent(
            application_id=application_id,
            event_type=event_type,
            message=message,
            occurred_at=datetime.now(UTC),
        )

        self._session.add(event)
        self._session.flush()

        return event


class ApplicationWarningRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        application_id: UUID,
        code: str,
        message: str,
        level: WarningLevel = WarningLevel.WARNING,
    ) -> ApplicationWarning:
        warning = ApplicationWarning(
            application_id=application_id,
            code=code,
            message=message,
            level=level.value,
        )

        self._session.add(warning)
        self._session.flush()

        return warning
