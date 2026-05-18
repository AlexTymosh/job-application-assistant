from __future__ import annotations

from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import ApplicationWorkflowError, NotFoundError
from app.db.models import (
    Application,
    ApplicationEvent,
    ApplicationStatus,
    TailoredResume,
)
from app.exporters.docx_exporter import DocxExporter
from app.exporters.pdf_exporter import PdfExporter
from app.people.service import PeopleService
from app.resumes.renderer import render_resume_markdown_from_content
from app.resumes.service import ResumeService
from app.tailoring.service import DeterministicTailoringClient, TailoringService


class ApplicationService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_applications(self, profile_id: int | None = None) -> list[Application]:
        stmt = select(Application).order_by(Application.created_at.desc())
        if profile_id is not None:
            stmt = stmt.where(Application.profile_id == profile_id)
        return list(self.session.scalars(stmt))

    def dashboard_stats(self, profile_id: int, days: int = 30) -> dict[str, object]:
        applications = self.list_applications(profile_id)
        return {
            "total": len(applications),
            "tailored": sum(1 for item in applications if item.tailored_resume_id),
            "days": days,
            "daily_counts": [],
        }

    def create_application(
        self,
        *,
        profile_id: int,
        resume_id: int,
        raw_job_text: str,
        source_url: str = "",
        job_title: str = "",
        company_name: str = "",
    ) -> Application:
        next_number = (
            self.session.scalar(select(func.max(Application.application_number))) or 0
        ) + 1
        application = Application(
            profile_id=profile_id,
            base_resume_id=resume_id,
            application_number=next_number,
            raw_job_text=raw_job_text.strip(),
            source_url=source_url.strip(),
            job_title=job_title.strip(),
            company_name=company_name.strip(),
            status=ApplicationStatus.JOB_SAVED.value,
        )
        self.session.add(application)
        self.session.flush()
        self.record_event(
            application.id,
            "application_created",
            "Application created from pasted job text.",
            commit=False,
        )
        self.session.commit()
        return application

    def adapt_application(
        self, application_id: int, client: DeterministicTailoringClient | None = None
    ) -> TailoredResume:
        application = self.get_application(application_id)
        resume = ResumeService(self.session).get_resume(application.base_resume_id)
        master_items = PeopleService(self.session).list_master_entries(
            application.profile_id
        )
        tailored = TailoringService(self.session, client=client).tailor(
            application_id=application.id,
            profile_id=application.profile_id,
            resume=resume,
            master_items=master_items,
            job_description=application.raw_job_text,
        )
        application.tailored_resume_id = tailored.id
        application.status = ApplicationStatus.TAILORED.value
        self.record_event(
            application.id,
            "resume_tailored",
            "Tailored resume saved automatically.",
            {"tailored_resume_id": tailored.id},
            commit=False,
        )
        self.session.commit()
        return tailored

    def get_application(self, application_id: int) -> Application:
        application = self.session.scalar(
            select(Application)
            .where(Application.id == application_id)
            .options(
                selectinload(Application.base_resume),
                selectinload(Application.profile),
                selectinload(Application.events),
            )
        )
        if application is None:
            raise NotFoundError("Application not found.")
        return application

    def get_tailored_resume(self, application_id: int) -> TailoredResume:
        application = self.get_application(application_id)
        if application.tailored_resume_id is None:
            raise ApplicationWorkflowError("Adapt the resume before exporting it.")
        tailored = self.session.get(TailoredResume, application.tailored_resume_id)
        if tailored is None:
            raise ApplicationWorkflowError("Tailored resume is missing.")
        return tailored

    def update_tailored_resume(
        self, application_id: int, markdown: str
    ) -> TailoredResume:
        tailored = self.get_tailored_resume(application_id)
        tailored.rendered_markdown = markdown.strip() + "\n"
        tailored.content_json = {
            **dict(tailored.content_json or {}),
            "manual_markdown": tailored.rendered_markdown,
        }
        self.session.commit()
        return tailored

    def export_tailored_resume(
        self, application_id: int, export_format: str, app_data_root: Path
    ) -> Path:
        tailored = self.get_tailored_resume(application_id)
        title = f"tailored-resume-{application_id}"
        directory = (
            app_data_root
            / "artifacts"
            / "applications"
            / f"application-{application_id}"
        )
        directory.mkdir(parents=True, exist_ok=True)
        suffix = _normalise_export_format(export_format)
        path = directory / f"{title}.{suffix}"
        markdown = tailored.rendered_markdown or render_resume_markdown_from_content(
            tailored.content_json
        )
        if suffix == "pdf":
            path.write_bytes(PdfExporter().export(markdown, title=title))
        else:
            path.write_bytes(DocxExporter().export(markdown, title=title))
        return path

    def tailored_resume_export_path(
        self, application_id: int, export_format: str, app_data_root: Path
    ) -> Path:
        suffix = _normalise_export_format(export_format)
        return (
            app_data_root
            / "artifacts"
            / "applications"
            / f"application-{application_id}"
            / f"tailored-resume-{application_id}.{suffix}"
        )

    def record_event(
        self,
        application_id: int,
        event_type: str,
        message: str,
        metadata: dict[str, object] | None = None,
        *,
        commit: bool = True,
    ) -> ApplicationEvent:
        event = ApplicationEvent(
            application_id=application_id,
            event_type=event_type,
            message=message,
            metadata_json=metadata or {},
        )
        self.session.add(event)
        if commit:
            self.session.commit()
        return event

    def delete_profile_applications(
        self,
        profile_id: int,
        *,
        older_than_days: int | None = None,
        app_data_root: Path | None = None,
    ) -> None:
        for application in self.list_applications(profile_id):
            self.session.delete(application)
        self.session.commit()


def _normalise_export_format(export_format: str) -> str:
    if export_format not in {"pdf", "docx"}:
        raise ApplicationWorkflowError("Choose PDF or DOCX export.")
    return export_format
