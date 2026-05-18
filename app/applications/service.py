from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import ApplicationWorkflowError, NotFoundError, ProfileScopeError
from app.db.models import (
    Application,
    ApplicationEvent,
    ApplicationStatus,
    CoverLetter,
    Resume,
    TailoredResume,
)
from app.exporters.docx_exporter import DocxExporter
from app.exporters.pdf_exporter import PdfExporter
from app.llm.fake_client import FakeCoverLetterClient
from app.people.service import PeopleService
from app.resumes.renderer import render_resume_markdown_from_content
from app.resumes.service import ResumeService
from app.settings.service import SettingsService
from app.tailoring.service import DeterministicTailoringClient, TailoringService

AI_SAFE_MASTER_CV_CATEGORIES = {"summary", "skills", "work_experience", "education"}
PRIVATE_AI_SOURCE_CATEGORIES = {
    "header",
    "reference",  # legacy singular category used before the Master CV reset
    "references",
    "languages",
    "certificates",
}


class ApplicationService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_applications(self, profile_id: int) -> list[Application]:
        return list(
            self.session.scalars(
                select(Application)
                .where(Application.profile_id == profile_id)
                .order_by(Application.created_at.desc())
            )
        )

    def dashboard_stats(self, profile_id: int, days: int = 30) -> dict[str, object]:
        days = days if days in {10, 20, 30} else 30
        profile = PeopleService(self.session).get_profile(profile_id)
        applications = self.list_applications(profile_id)
        resume_count = (
            self.session.scalar(
                select(func.count(Resume.id)).where(Resume.profile_id == profile_id)
            )
            or 0
        )
        today = datetime.now(UTC).date()
        range_start = today - timedelta(days=days - 1)
        last_30_start = today - timedelta(days=29)
        counts_by_day = {
            range_start + timedelta(days=offset): 0 for offset in range(days)
        }
        applications_last_30_days = 0
        for application in applications:
            created_date = application.created_at.date()
            if created_date >= last_30_start:
                applications_last_30_days += 1
            if created_date in counts_by_day:
                counts_by_day[created_date] += 1
        max_count = max(counts_by_day.values(), default=0)
        chart_max_height = 116
        label_interval = 1 if days == 10 else 2 if days == 20 else 3
        activity_days = []
        for index, (date_value, count) in enumerate(counts_by_day.items()):
            height = (
                4
                if count == 0
                else max(8, round((count / max_count) * chart_max_height))
            )
            activity_days.append(
                {
                    "date": date_value,
                    "label": f"{date_value.isoformat()}: {count} applications",
                    "count": count,
                    "height": height,
                    "x_label": date_value.strftime("%d %b"),
                    "show_x_label": index % label_interval == 0 or index == days - 1,
                }
            )
        y_axis_labels = (
            [str(max_count), str(max_count // 2), "0"] if max_count else ["1", "0", "0"]
        )
        return {
            "profile_name": profile.display_name,
            "resume_count": int(resume_count),
            "application_count": len(applications),
            "applications_last_30_days": applications_last_30_days,
            "activity_range_days": days,
            "activity_days": activity_days,
            "y_axis_labels": y_axis_labels,
            "recent_applications": applications[:5],
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
        resume = ResumeService(self.session).get_resume(resume_id)
        if resume.profile_id != profile_id:
            raise ApplicationWorkflowError(
                "Choose a Resume Variant that belongs to the active profile."
            )
        if not raw_job_text.strip():
            raise ApplicationWorkflowError(
                "Paste a job description before adapting a resume."
            )
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
        self._create_cover_letter(application, tailored, master_items)
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

    def get_profile_application(
        self, application_id: int, profile_id: int
    ) -> Application:
        application = self.get_application(application_id)
        if application.profile_id != profile_id:
            raise ProfileScopeError(
                "Application not found in the active profile workspace."
            )
        return application

    def get_tailored_resume(self, application_id: int) -> TailoredResume:
        application = self.get_application(application_id)
        if application.tailored_resume_id is None:
            raise ApplicationWorkflowError("Adapt the resume before exporting it.")
        tailored = self.session.get(TailoredResume, application.tailored_resume_id)
        if tailored is None:
            raise ApplicationWorkflowError("Tailored resume is missing.")
        return tailored

    def latest_cover_letter(self, application_id: int) -> CoverLetter | None:
        return self.session.scalar(
            select(CoverLetter)
            .where(CoverLetter.application_id == application_id)
            .order_by(CoverLetter.created_at.desc())
        )

    def _create_cover_letter(
        self,
        application: Application,
        tailored: TailoredResume,
        master_items: list,
    ) -> CoverLetter:
        existing = self.latest_cover_letter(application.id)
        if existing is not None:
            self.session.delete(existing)
            self.session.flush()
        safe_tailored_content = deepcopy(tailored.content_json or {})
        for private_key in ["header", "references"]:
            safe_tailored_content.get("sections", {}).pop(private_key, None)
        instruction = SettingsService(self.session).get_prompt_instruction(
            "cover_letter",
            profile_id=application.profile_id,
            resume_id=application.base_resume_id,
        )
        payload = {
            "tailored_resume": render_resume_markdown_from_content(
                safe_tailored_content
            ),
            "job_description": application.raw_job_text,
            "master_cv_items": [
                {"id": item.id, "title": item.title, "content": item.content}
                for item in master_items
                if _is_ai_safe_master_item(item)
            ],
            "user_prompt_instruction": instruction,
        }
        content = FakeCoverLetterClient().draft(payload)
        cover_letter = CoverLetter(
            application_id=application.id,
            profile_id=application.profile_id,
            resume_id=application.base_resume_id,
            content=content,
            status="draft",
        )
        self.session.add(cover_letter)
        self.session.flush()
        return cover_letter

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
        if suffix == "pdf":
            path.write_bytes(
                PdfExporter().export_content(tailored.content_json, title=title)
            )
        else:
            path.write_bytes(
                DocxExporter().export_content(tailored.content_json, title=title)
            )
        return path

    def export_cover_letter_text(
        self, application_id: int, app_data_root: Path
    ) -> Path:
        cover_letter = self.latest_cover_letter(application_id)
        if cover_letter is None:
            raise ApplicationWorkflowError(
                "Generate a cover letter before downloading it."
            )
        directory = (
            app_data_root
            / "artifacts"
            / "applications"
            / f"application-{application_id}"
        )
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"cover-letter-{application_id}.txt"
        path.write_text(cover_letter.content.strip() + "\n", encoding="utf-8")
        return path

    def cover_letter_text_path(self, application_id: int, app_data_root: Path) -> Path:
        return (
            app_data_root
            / "artifacts"
            / "applications"
            / f"application-{application_id}"
            / f"cover-letter-{application_id}.txt"
        )

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


def _is_ai_safe_master_item(item: object) -> bool:
    return (
        getattr(item, "is_active", False)
        and getattr(item, "category", "") in AI_SAFE_MASTER_CV_CATEGORIES
    )


def _normalise_export_format(export_format: str) -> str:
    if export_format not in {"pdf", "docx"}:
        raise ApplicationWorkflowError("Choose PDF or DOCX export.")
    return export_format
