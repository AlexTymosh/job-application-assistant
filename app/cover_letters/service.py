from __future__ import annotations

from sqlalchemy.orm import Session

from app.applications.service import ApplicationService
from app.db.models import CoverLetter
from app.llm.fake_client import FakeCoverLetterClient
from app.llm.prompts.cover_letter import build_cover_letter_payload


class CoverLetterService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def generate_cover_letter(
        self,
        application_id: int,
        client: FakeCoverLetterClient | None = None,
    ) -> CoverLetter:
        application = ApplicationService(self.session).get_application(application_id)
        tailored = ApplicationService(self.session).get_tailored_resume(application_id)
        payload = build_cover_letter_payload(
            tailored_resume=tailored.rendered_markdown,
            job_description=application.raw_job_text,
        )
        content = (client or FakeCoverLetterClient()).draft(payload)
        letter = CoverLetter(
            application_id=application.id,
            profile_id=application.profile_id,
            resume_id=application.base_resume_id,
            content=content,
            status="draft",
        )
        self.session.add(letter)
        self.session.commit()
        return letter
