from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.db.models import (
    AiChangeProposal,
    Application,
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


class ApplicationService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_applications(self) -> list[Application]:
        return list(
            self.session.scalars(
                select(Application).order_by(Application.created_at.desc())
            )
        )

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
            raise ValueError("Application not found.")
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
        self.session.commit()
        return requirements

    def latest_tailoring_run(self, application_id: int) -> TailoringRun | None:
        return self.session.scalar(
            select(TailoringRun)
            .where(TailoringRun.application_id == application_id)
            .order_by(TailoringRun.created_at.desc())
        )

    def decide_proposals(self, decisions: dict[int, str]) -> None:
        now = datetime.now(UTC)

        for proposal_id, decision in decisions.items():
            proposal = self.session.get(AiChangeProposal, proposal_id)
            if proposal is None:
                continue

            if decision not in {
                ProposalStatus.ACCEPTED.value,
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
            raise ValueError("Run tailoring before creating a snapshot.")

        accepted_changes = {
            (proposal.target_type, proposal.target_id): proposal.after_text
            for proposal in run.proposals
            if proposal.status == ProposalStatus.ACCEPTED.value
        }

        resume = self._load_resume_for_snapshot(application.resume_id)

        # Important privacy boundary:
        # The approved snapshot must contain only resume content and accepted changes.
        # Private contact details are intentionally excluded here and added only during
        # final export/rendering.
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
        self.session.commit()
        return snapshot

    def export_snapshot(
        self,
        snapshot_id: int,
        app_data_root: Path,
    ) -> list[Artifact]:
        snapshot = self.session.get(TailoredResumeSnapshot, snapshot_id)
        if snapshot is None:
            raise ValueError("Snapshot not found.")

        application = self.get_application(snapshot.application_id)
        resume = self._load_resume_for_final_export(snapshot.resume_id)
        accepted_changes = _deserialise_accepted_changes(snapshot.content_json)

        # Contact details are added only at final export time.
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
        self.session.commit()
        return artifacts

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
            raise ValueError("Resume not found.")
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
            raise ValueError("Resume not found.")
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
