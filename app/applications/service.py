from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import (
    ExportWorkflowError,
    NotFoundError,
    ProfileScopeError,
    TailoringWorkflowError,
)
from app.cover_letters.service import CoverLetterService
from app.db.models import (
    AiChangeProposal,
    Application,
    ApplicationEvent,
    ApplicationStatus,
    Artifact,
    ExtractedJobRequirement,
    PersonProfile,
    ProposalStatus,
    Resume,
    ResumeBlock,
    ResumeSection,
    TailoredResumeSnapshot,
    TailoringRun,
)
from app.exporters.docx_exporter import DocxExporter
from app.exporters.html_exporter import HtmlExporter
from app.exporters.markdown_exporter import MarkdownExporter
from app.exporters.pdf_exporter import PdfExporter
from app.llm.fake_client import FakeJobExtractionClient
from app.resumes.renderer import render_resume_markdown
from app.settings.service import SettingsService
from app.tailoring.service import TailoringService

LIKELY_APPLIED_STATUSES = {
    ApplicationStatus.COPIED_LIKELY_APPLIED.value,
    ApplicationStatus.DOWNLOADED_LIKELY_APPLIED.value,
    ApplicationStatus.LIKELY_APPLIED.value,
    ApplicationStatus.MANUALLY_MARKED_APPLIED.value,
}


@dataclass(frozen=True)
class DashboardStats:
    profile_id: int
    profile_name: str
    resume_count: int
    application_count: int
    applications_last_30_days: int
    likely_applied_count: int
    manually_marked_applied_count: int
    recent_applications: list[Application]
    activity_days: list[dict[str, object]]


class ApplicationService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_applications(self, profile_id: int | None = None) -> list[Application]:
        stmt = select(Application).order_by(Application.created_at.desc())
        if profile_id is not None:
            stmt = stmt.where(Application.profile_id == profile_id)
        return list(self.session.scalars(stmt))

    def create_application(
        self,
        *,
        profile_id: int,
        resume_id: int,
        job_title: str,
        company_name: str,
        source_url: str,
        raw_job_text: str,
    ) -> Application:
        next_number = (
            self.session.scalar(select(func.max(Application.application_number))) or 0
        ) + 1

        application = Application(
            profile_id=profile_id,
            resume_id=resume_id,
            application_number=next_number,
            job_title=job_title,
            company_name=company_name,
            source_url=source_url,
            raw_job_text=raw_job_text,
            status=ApplicationStatus.JOB_SAVED.value,
        )
        self.session.add(application)
        self.session.flush()
        self.record_event(
            application.id,
            "application_created",
            "Application record created from pasted job text.",
            commit=False,
        )
        self.session.commit()
        return application

    def get_application(self, application_id: int) -> Application:
        application = self.session.scalar(
            select(Application)
            .where(Application.id == application_id)
            .options(
                selectinload(Application.requirements),
                selectinload(Application.resume),
                selectinload(Application.profile),
            )
        )
        if application is None:
            raise NotFoundError("Application not found.")
        return application

    def extract_requirements(
        self,
        application_id: int,
        client: FakeJobExtractionClient | None = None,
    ) -> list[ExtractedJobRequirement]:
        application = self.get_application(application_id)
        client = client or FakeJobExtractionClient()

        for existing in list(application.requirements):
            self.session.delete(existing)

        self.session.flush()

        requirements: list[ExtractedJobRequirement] = []
        for item in client.extract(application.raw_job_text):
            requirement = ExtractedJobRequirement(
                application_id=application.id,
                requirement_type=str(item["requirement_type"]),
                text=str(item["text"]),
                keywords_json=item.get("keywords", []),
                priority=int(item.get("priority", 3)),
            )
            self.session.add(requirement)
            requirements.append(requirement)

        application.status = ApplicationStatus.REQUIREMENTS_EXTRACTED.value
        self.record_event(
            application.id,
            "requirements_extracted",
            "Job requirements extracted from the pasted job text.",
            {"requirement_count": len(requirements)},
            commit=False,
        )
        self.session.commit()
        return requirements

    def latest_tailoring_run(self, application_id: int) -> TailoringRun | None:
        return self.session.scalar(
            select(TailoringRun)
            .where(TailoringRun.application_id == application_id)
            .order_by(TailoringRun.created_at.desc())
        )

    def latest_snapshot(self, application_id: int) -> TailoredResumeSnapshot | None:
        return self.session.scalar(
            select(TailoredResumeSnapshot)
            .where(TailoredResumeSnapshot.application_id == application_id)
            .order_by(TailoredResumeSnapshot.created_at.desc())
        )

    def decide_proposals(self, decisions: dict[int, str]) -> None:
        now = datetime.now(UTC)

        for proposal_id, decision in decisions.items():
            proposal = self.session.get(AiChangeProposal, proposal_id)
            if proposal is None:
                continue

            if decision not in {
                ProposalStatus.ACCEPTED.value,
                ProposalStatus.ACCEPTED_EDITED.value,
                ProposalStatus.REJECTED.value,
            }:
                continue

            proposal.status = decision
            proposal.decided_at = now

        self.session.commit()

    def create_snapshot(self, application_id: int) -> TailoredResumeSnapshot:
        application = self.get_application(application_id)
        run = self.latest_tailoring_run(application_id)

        if run is None:
            raise TailoringWorkflowError(
                "Run tailoring before creating an approved snapshot."
            )

        accepted_changes = {
            (proposal.target_type, proposal.target_id): proposal.after_text
            for proposal in run.proposals
            if proposal.status
            in {
                ProposalStatus.ACCEPTED.value,
                ProposalStatus.ACCEPTED_EDITED.value,
            }
        }

        if not accepted_changes:
            raise TailoringWorkflowError(
                "Accept at least one proposal before creating an approved snapshot."
            )

        existing_snapshot = self.latest_snapshot(application_id)
        if (
            existing_snapshot is not None
            and existing_snapshot.tailoring_run_id == run.id
        ):
            return existing_snapshot

        resume = self._load_resume_for_snapshot(application.resume_id)

        markdown_without_contact = render_resume_markdown(
            resume,
            accepted_changes=accepted_changes,
            contact=None,
        )

        snapshot = TailoredResumeSnapshot(
            application_id=application.id,
            resume_id=resume.id,
            tailoring_run_id=run.id,
            content_json={
                "accepted_changes": _serialise_accepted_changes(accepted_changes),
                "contact_layer_included": False,
            },
            rendered_markdown=markdown_without_contact,
        )

        application.status = ApplicationStatus.CHANGES_APPROVED.value
        self.session.add(snapshot)
        self.session.flush()
        self.record_event(
            application.id,
            "snapshot_created",
            "Approved tailored resume snapshot created.",
            {"snapshot_id": snapshot.id},
            commit=False,
        )
        self.session.commit()
        return snapshot

    def export_snapshot(
        self,
        snapshot_id: int,
        app_data_root: Path,
    ) -> list[Artifact]:
        snapshot = self.session.get(TailoredResumeSnapshot, snapshot_id)
        if snapshot is None:
            raise ExportWorkflowError("Snapshot not found.")

        application = self.get_application(snapshot.application_id)
        resume = self._load_resume_for_final_export(snapshot.resume_id)
        accepted_changes = _deserialise_accepted_changes(snapshot.content_json)

        final_markdown = render_resume_markdown(
            resume,
            accepted_changes=accepted_changes,
            contact=resume.profile.contact,
        )

        settings = SettingsService(self.session).effective()
        formats = settings.exports

        export_dir = Path("artifacts") / f"app-{application.application_number:06d}"
        absolute_dir = app_data_root / export_dir
        absolute_dir.mkdir(parents=True, exist_ok=True)

        outputs: dict[str, bytes | str] = {}

        if formats.get("markdown"):
            outputs["markdown"] = MarkdownExporter().export(final_markdown)

        if formats.get("html"):
            outputs["html"] = HtmlExporter().export(final_markdown)

        if formats.get("pdf"):
            outputs["pdf"] = PdfExporter().export(
                final_markdown,
                title=application.job_title or "Tailored resume",
            )

        if formats.get("docx"):
            outputs["docx"] = DocxExporter().export(final_markdown)

        suffixes = {
            "markdown": "md",
            "html": "html",
            "pdf": "pdf",
            "docx": "docx",
        }

        artifacts: list[Artifact] = []

        for artifact_type, content in outputs.items():
            relative_path = export_dir / f"tailored-resume.{suffixes[artifact_type]}"
            absolute_path = app_data_root / relative_path

            if isinstance(content, bytes):
                absolute_path.write_bytes(content)
            else:
                absolute_path.write_text(content, encoding="utf-8")

            artifact = self._upsert_artifact(
                application_id=application.id,
                artifact_type=artifact_type,
                relative_path=relative_path.as_posix(),
            )
            artifacts.append(artifact)

        application.status = ApplicationStatus.EXPORTED.value
        self.record_event(
            application.id,
            "artifact_exported",
            "Resume artifacts exported for download.",
            {"artifact_types": [artifact.artifact_type for artifact in artifacts]},
            commit=False,
        )
        self.session.commit()
        return artifacts

    def adapt_application(
        self,
        *,
        profile_id: int,
        resume_id: int,
        job_title: str,
        company_name: str,
        source_url: str,
        raw_job_text: str,
    ) -> Application:
        resume = self.session.get(Resume, resume_id)
        if resume is None or resume.profile_id != profile_id:
            raise ProfileScopeError("Resume must belong to the active profile.")
        application = self.create_application(
            profile_id=profile_id,
            resume_id=resume_id,
            job_title=job_title,
            company_name=company_name,
            source_url=source_url,
            raw_job_text=raw_job_text,
        )
        self.extract_requirements(application.id)
        TailoringService(self.session).run_tailoring(application.id)
        CoverLetterService(self.session).generate(application.id)
        self.record_event(
            application.id,
            "adaptation_completed",
            "Requirements, tailoring proposals, and cover letter generated.",
        )
        self.session.expire_all()
        return self.get_application(application.id)

    def save_review_edits(
        self, application_id: int, edited_after_text: dict[int, str]
    ) -> None:
        run = self.latest_tailoring_run(application_id)
        if run is None:
            raise TailoringWorkflowError("Run tailoring before saving review edits.")
        for proposal in run.proposals:
            if proposal.id in edited_after_text:
                proposal.after_text = edited_after_text[proposal.id]
                self.record_event(
                    application_id,
                    "proposal_edited_before_acceptance",
                    "A tailored proposal was edited before acceptance.",
                    {"proposal_id": proposal.id},
                    commit=False,
                )
        self.session.commit()

    def save_review_decisions(
        self,
        application_id: int,
        decisions: dict[int, str],
        edited_after_text: dict[int, str] | None = None,
    ) -> None:
        edited_after_text = edited_after_text or {}
        run = self.latest_tailoring_run(application_id)
        if run is None:
            raise TailoringWorkflowError("Run tailoring before saving decisions.")
        now = datetime.now(UTC)
        for proposal in run.proposals:
            decision = decisions.get(proposal.id)
            if proposal.id in edited_after_text:
                proposal.after_text = edited_after_text[proposal.id]
            if decision in {
                ProposalStatus.ACCEPTED.value,
                ProposalStatus.ACCEPTED_EDITED.value,
                ProposalStatus.REJECTED.value,
            }:
                proposal.status = decision
                proposal.decided_at = now
        self.record_event(
            application_id,
            "proposal_decision_saved",
            "Proposal review decisions saved.",
            commit=False,
        )
        self.session.commit()

    def record_event(
        self,
        application_id: int,
        event_type: str,
        message: str = "",
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

    def record_copy_event(
        self, application_id: int, target_type: str, target_id: str, label: str
    ) -> ApplicationEvent:
        app = self.get_application(application_id)
        app.status = ApplicationStatus.COPIED_LIKELY_APPLIED.value
        event = self.record_event(
            application_id,
            f"{target_type}_copied",
            f"Copied {label}; this marks the application as likely applied.",
            {"target_type": target_type, "target_id": target_id, "label": label},
            commit=False,
        )
        self.record_event(
            application_id,
            "likely_applied",
            "Copy activity indicates the application is likely applied, not confirmed.",
            commit=False,
        )
        self.session.commit()
        return event

    def record_download_event(
        self, application_id: int, artifact_id: int, label: str
    ) -> ApplicationEvent:
        app = self.get_application(application_id)
        app.status = ApplicationStatus.DOWNLOADED_LIKELY_APPLIED.value
        event = self.record_event(
            application_id,
            "artifact_downloaded",
            f"Downloaded {label}; this marks the application as likely applied.",
            {"artifact_id": artifact_id, "label": label},
            commit=False,
        )
        self.record_event(
            application_id,
            "likely_applied",
            (
                "Download activity indicates the application is likely applied, "
                "not confirmed."
            ),
            commit=False,
        )
        self.session.commit()
        return event

    def mark_manually_applied(self, application_id: int) -> ApplicationEvent:
        app = self.get_application(application_id)
        app.status = ApplicationStatus.MANUALLY_MARKED_APPLIED.value
        event = self.record_event(
            application_id,
            "manually_marked_applied",
            "User manually marked this application as applied.",
            commit=False,
        )
        self.session.commit()
        return event

    def dashboard_stats(self, profile_id: int) -> DashboardStats:
        profile = self.session.get(PersonProfile, profile_id)
        if profile is None:
            raise NotFoundError("Profile not found.")
        applications = self.list_applications(profile_id)
        resume_count = (
            self.session.scalar(
                select(func.count(Resume.id)).where(Resume.profile_id == profile_id)
            )
            or 0
        )
        cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=30)
        last_30 = [app for app in applications if app.created_at >= cutoff]
        likely = [app for app in applications if app.status in LIKELY_APPLIED_STATUSES]
        manual = [
            app
            for app in applications
            if app.status == ApplicationStatus.MANUALLY_MARKED_APPLIED.value
        ]
        counts_by_day: dict[str, int] = {}
        today = datetime.now(UTC).date()
        for offset in range(29, -1, -1):
            key = (today - timedelta(days=offset)).isoformat()
            counts_by_day[key] = 0
        for app in applications:
            key = app.created_at.date().isoformat()
            if key in counts_by_day:
                counts_by_day[key] += 1
        max_count = max(counts_by_day.values(), default=0) or 1
        activity_days = [
            {
                "date": date,
                "count": count,
                "height": max(8, int(count / max_count * 72)),
            }
            for date, count in counts_by_day.items()
        ]
        return DashboardStats(
            profile_id=profile.id,
            profile_name=profile.display_name,
            resume_count=int(resume_count),
            application_count=len(applications),
            applications_last_30_days=len(last_30),
            likely_applied_count=len(likely),
            manually_marked_applied_count=len(manual),
            recent_applications=applications[:8],
            activity_days=activity_days,
        )

    def tailoring_service(self) -> TailoringService:
        return TailoringService(self.session)

    def _load_resume_for_snapshot(self, resume_id: int) -> Resume:
        resume = self.session.scalar(
            select(Resume)
            .where(Resume.id == resume_id)
            .options(
                selectinload(Resume.profile),
                selectinload(Resume.sections)
                .selectinload(ResumeSection.blocks)
                .selectinload(ResumeBlock.bullets),
            )
        )
        if resume is None:
            raise NotFoundError("Resume not found.")
        return resume

    def _load_resume_for_final_export(self, resume_id: int) -> Resume:
        resume = self.session.scalar(
            select(Resume)
            .where(Resume.id == resume_id)
            .options(
                selectinload(Resume.profile).selectinload(PersonProfile.contact),
                selectinload(Resume.sections)
                .selectinload(ResumeSection.blocks)
                .selectinload(ResumeBlock.bullets),
            )
        )
        if resume is None:
            raise NotFoundError("Resume not found.")
        return resume

    def _upsert_artifact(
        self,
        *,
        application_id: int,
        artifact_type: str,
        relative_path: str,
    ) -> Artifact:
        artifact = self.session.scalar(
            select(Artifact).where(
                Artifact.application_id == application_id,
                Artifact.artifact_type == artifact_type,
            )
        )

        if artifact is None:
            artifact = Artifact(
                application_id=application_id,
                artifact_type=artifact_type,
                relative_path=relative_path,
            )
            self.session.add(artifact)
        else:
            artifact.relative_path = relative_path

        return artifact


def _serialise_accepted_changes(
    accepted_changes: dict[tuple[str, int], str],
) -> dict[str, str]:
    return {
        f"{target_type}:{target_id}": after_text
        for (target_type, target_id), after_text in accepted_changes.items()
    }


def _deserialise_accepted_changes(
    content_json: Any,
) -> dict[tuple[str, int], str]:
    if not isinstance(content_json, dict):
        return {}

    raw_changes = content_json.get("accepted_changes", {})
    accepted_changes: dict[tuple[str, int], str] = {}

    if isinstance(raw_changes, dict):
        for raw_key, raw_value in raw_changes.items():
            if not isinstance(raw_key, str):
                continue

            target_type, separator, target_id_text = raw_key.rpartition(":")
            if not separator:
                continue

            try:
                target_id = int(target_id_text)
            except ValueError:
                continue

            accepted_changes[(target_type, target_id)] = str(raw_value)

        return accepted_changes

    if isinstance(raw_changes, list):
        for item in raw_changes:
            if not isinstance(item, dict):
                continue

            target_type = item.get("target_type")
            target_id = item.get("target_id")
            after_text = item.get("after_text")

            if not isinstance(target_type, str):
                continue

            try:
                parsed_target_id = int(target_id)
            except (TypeError, ValueError):
                continue

            accepted_changes[(target_type, parsed_target_id)] = str(after_text or "")

    return accepted_changes
