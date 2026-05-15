from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import (
    Application,
    ApplicationStatus,
    CoverLetter,
    ExtractedJobRequirement,
    Resume,
    ResumeBlock,
    ResumeSection,
)
from app.llm.fake_client import FakeCoverLetterClient
from app.resumes.renderer import render_resume_markdown


class CoverLetterService:
    def __init__(self, session: Session, client: FakeCoverLetterClient | None = None) -> None:
        self.session = session
        self.client = client or FakeCoverLetterClient()

    def generate(self, application_id: int) -> CoverLetter:
        app = self.session.get(Application, application_id)
        if app is None:
            raise ValueError("Application not found.")
        resume = self.session.scalar(
            select(Resume)
            .where(Resume.id == app.resume_id)
            .options(
                selectinload(Resume.profile),
                selectinload(Resume.sections).selectinload(ResumeSection.blocks).selectinload(ResumeBlock.bullets),
            )
        )
        if resume is None:
            raise ValueError("Resume not found.")
        requirements = list(self.session.scalars(select(ExtractedJobRequirement).where(ExtractedJobRequirement.application_id == app.id)))
        markdown_without_contact = render_resume_markdown(resume, contact=None)
        content = self.client.generate(
            profile_name=resume.profile.display_name,
            resume_markdown=markdown_without_contact,
            job_requirements=[{"id": req.id, "text": req.text} for req in requirements],
        )
        letter = CoverLetter(
            application_id=app.id,
            profile_id=app.profile_id,
            resume_id=app.resume_id,
            content=content,
            status="draft",
        )
        app.status = ApplicationStatus.COVER_LETTER_GENERATED.value
        self.session.add(letter)
        self.session.commit()
        return letter

    def latest(self, application_id: int) -> CoverLetter | None:
        return self.session.scalar(select(CoverLetter).where(CoverLetter.application_id == application_id).order_by(CoverLetter.created_at.desc()))
