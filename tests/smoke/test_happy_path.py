from __future__ import annotations

from sqlalchemy import select

from app.applications.service import ApplicationService
from app.cover_letters.service import CoverLetterService
from app.db.models import Artifact
from app.people.service import PeopleService
from app.resumes.service import ResumeService
from app.settings.service import SettingsService
from app.tailoring.service import TailoringService


def test_full_happy_path_without_real_ai(session, tmp_path):
    settings = SettingsService(session)
    settings.set(
        "exports",
        {"markdown": True, "html": False, "pdf": True, "docx": True},
    )
    profile = PeopleService(session).create_profile("Alex", "Alex Example", "Remote")
    PeopleService(session).update_profile(
        profile.id,
        display_name="Alex",
        full_name="Alex Example",
        preferred_name="Alex",
        location="Remote",
        email="alex@example.com",
        phone="+1 555 0100",
        address_line="Private Street",
        city="Remote",
        country="US",
    )
    fact = PeopleService(session).create_fact(
        profile.id,
        fact_key="fastapi",
        category="backend",
        claim="Built FastAPI services.",
        evidence="Portfolio project",
        source="local notes",
        allowed_claim_level="practical",
    )
    resumes = ResumeService(session)
    resume = resumes.create_resume(profile.id, "Backend Developer", "Backend Developer")
    section = resumes.add_section(resume.id, "work_experience", "Work Experience", True)
    block = resumes.add_block(
        section.id,
        block_type="work_experience",
        title="API work",
        organisation="Example",
        content="Backend delivery",
    )
    resumes.add_bullet(
        block.id,
        "Built FastAPI services.",
        ai_edit_enabled=True,
        fact_link_required=True,
        fact_ids=[fact.id],
    )
    app_service = ApplicationService(session)
    application = app_service.create_application(
        profile_id=profile.id,
        resume_id=resume.id,
        job_title="Backend Engineer",
        company_name="Acme",
        source_url="https://example.invalid/job",
        raw_job_text="Backend role needing Python FastAPI SQL testing.",
    )
    app_service.extract_requirements(application.id)
    run = TailoringService(session).run_tailoring(application.id)
    assert run.proposals
    app_service.decide_proposals({run.proposals[0].id: "accepted"})
    snapshot = app_service.create_snapshot(application.id)
    assert "alex@example.com" not in snapshot.rendered_markdown
    assert "+1 555 0100" not in snapshot.rendered_markdown
    assert "Private Street" not in snapshot.rendered_markdown
    artifacts = app_service.export_snapshot(snapshot.id, tmp_path)
    markdown_artifact = next(
        artifact for artifact in artifacts if artifact.artifact_type == "markdown"
    )
    exported_markdown = (tmp_path / markdown_artifact.relative_path).read_text(
        encoding="utf-8"
    )

    assert "alex@example.com" in exported_markdown
    assert "+1 555 0100" in exported_markdown
    assert {artifact.artifact_type for artifact in artifacts} == {
        "markdown",
        "pdf",
        "docx",
    }
    letter = CoverLetterService(session).generate(application.id)
    assert "Dear hiring team" in letter.content
    assert all(
        not artifact.relative_path.startswith("/")
        for artifact in session.scalars(select(Artifact))
    )
