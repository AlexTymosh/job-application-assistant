from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

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
        return list(self.session.scalars(select(Application).order_by(Application.created_at.desc())))

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
        next_number = (self.session.scalar(select(func.max(Application.application_number))) or 0) + 1
        app = Application(
            profile_id=profile_id,
            resume_id=resume_id,
            application_number=next_number,
            job_title=job_title,
            company_name=company_name,
            source_url=source_url,
            raw_job_text=raw_job_text,
            status=ApplicationStatus.JOB_SAVED.value,
        )
        self.session.add(app)
        self.session.commit()
        return app

    def get_application(self, application_id: int) -> Application:
        app = self.session.scalar(
            select(Application)
            .where(Application.id == application_id)
            .options(
                selectinload(Application.requirements),
                selectinload(Application.resume),
                selectinload(Application.profile),
            )
        )
        if app is None:
            raise ValueError("Application not found.")
        return app

    def extract_requirements(self, application_id: int, client: FakeJobExtractionClient | None = None) -> list[ExtractedJobRequirement]:
        app = self.get_application(application_id)
        client = client or FakeJobExtractionClient()
        for existing in list(app.requirements):
            self.session.delete(existing)
        self.session.flush()
        requirements = []
        for item in client.extract(app.raw_job_text):
            requirement = ExtractedJobRequirement(
                application_id=app.id,
                requirement_type=str(item["requirement_type"]),
                text=str(item["text"]),
                keywords_json=item.get("keywords", []),
                priority=int(item.get("priority", 3)),
            )
            self.session.add(requirement)
            requirements.append(requirement)
        app.status = ApplicationStatus.REQUIREMENTS_EXTRACTED.value
        self.session.commit()
        return requirements

    def latest_tailoring_run(self, application_id: int) -> TailoringRun | None:
        return self.session.scalar(select(TailoringRun).where(TailoringRun.application_id == application_id).order_by(TailoringRun.created_at.desc()))

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
        app = self.get_application(application_id)
        run = self.latest_tailoring_run(application_id)
        if run is None:
            raise ValueError("Run tailoring before creating a snapshot.")
        accepted = {(proposal.target_type, proposal.target_id): proposal.after_text for proposal in run.proposals if proposal.status == ProposalStatus.ACCEPTED.value}
        resume = self.session.scalar(
            select(Resume)
            .where(Resume.id == app.resume_id)
            .options(
                selectinload(Resume.profile).selectinload(PersonProfile.contact),
                selectinload(Resume.sections).selectinload(ResumeSection.blocks).selectinload(ResumeBlock.bullets),
            )
        )
        if resume is None:
            raise ValueError("Resume not found.")
        markdown = render_resume_markdown(resume, accepted_changes=accepted, contact=resume.profile.contact)
        snapshot = TailoredResumeSnapshot(
            application_id=app.id,
            resume_id=resume.id,
            tailoring_run_id=run.id,
            content_json={"accepted_changes": {f"{key[0]}:{key[1]}": value for key, value in accepted.items()}},
            rendered_markdown=markdown,
        )
        app.status = ApplicationStatus.CHANGES_APPROVED.value
        self.session.add(snapshot)
        self.session.commit()
        return snapshot

    def export_snapshot(self, snapshot_id: int, app_data_root: Path) -> list[Artifact]:
        snapshot = self.session.get(TailoredResumeSnapshot, snapshot_id)
        if snapshot is None:
            raise ValueError("Snapshot not found.")
        app = self.get_application(snapshot.application_id)
        settings = SettingsService(self.session).effective()
        export_dir = Path("artifacts") / f"app-{app.application_number:06d}"
        absolute_dir = app_data_root / export_dir
        absolute_dir.mkdir(parents=True, exist_ok=True)
        formats = settings.exports
        outputs: dict[str, bytes | str] = {}
        if formats.get("markdown"):
            outputs["markdown"] = MarkdownExporter().export(snapshot.rendered_markdown)
        if formats.get("html"):
            outputs["html"] = HtmlExporter().export(snapshot.rendered_markdown)
        if formats.get("pdf"):
            outputs["pdf"] = PdfExporter().export(snapshot.rendered_markdown, title=app.job_title or "Tailored resume")
        if formats.get("docx"):
            outputs["docx"] = DocxExporter().export(snapshot.rendered_markdown)
        artifacts = []
        suffixes = {"markdown": "md", "html": "html", "pdf": "pdf", "docx": "docx"}
        for artifact_type, content in outputs.items():
            relative_path = export_dir / f"tailored-resume.{suffixes[artifact_type]}"
            absolute_path = app_data_root / relative_path
            if isinstance(content, bytes):
                absolute_path.write_bytes(content)
            else:
                absolute_path.write_text(content, encoding="utf-8")
            artifact = Artifact(
                application_id=app.id,
                artifact_type=artifact_type,
                relative_path=relative_path.as_posix(),
            )
            self.session.add(artifact)
            artifacts.append(artifact)
        app.status = ApplicationStatus.EXPORTED.value
        self.session.commit()
        return artifacts

    def tailoring_service(self) -> TailoringService:
        return TailoringService(self.session)
