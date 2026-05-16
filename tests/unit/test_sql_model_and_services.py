from __future__ import annotations

from sqlalchemy import select

from app.applications.service import ApplicationService
from app.db.models import AiChangeProposal, Artifact, ResumeBullet
from app.people.service import PeopleService
from app.resumes.service import ResumeService
from app.settings.service import SettingsService
from app.tailoring.service import TailoringService


def build_resume(session):
    profile = PeopleService(session).create_profile("Alex", "Alex Example", "Berlin")
    fact = PeopleService(session).create_fact(
        profile.id,
        fact_key="python-api",
        category="backend",
        claim="Built Python API services.",
        evidence="Project notes",
        source="self-review",
        allowed_claim_level="practical",
    )
    resume_service = ResumeService(session)
    resume = resume_service.create_resume(
        profile.id, "Backend Developer", "Backend Developer"
    )
    section = resume_service.add_section(
        resume.id, "work_experience", "Work Experience", True
    )
    block = resume_service.add_block(
        section.id,
        block_type="work_experience",
        title="Backend work",
        role_title="Developer",
        organisation="Example Ltd",
        content="Built services.",
        ai_edit_enabled=False,
    )
    bullet = resume_service.add_bullet(
        block.id,
        "Built Python services.",
        ai_edit_enabled=True,
        fact_link_required=True,
        fact_ids=[fact.id],
    )
    return profile, resume, bullet


def test_sql_first_resume_tailoring_and_export_flow(session, tmp_path):
    profile, resume, bullet = build_resume(session)
    app_service = ApplicationService(session)
    application = app_service.create_application(
        profile_id=profile.id,
        resume_id=resume.id,
        job_title="API Engineer",
        company_name="Acme",
        source_url="",
        raw_job_text="We need Python FastAPI SQL experience.",
    )
    requirements = app_service.extract_requirements(application.id)
    assert requirements

    run = TailoringService(session).run_tailoring(application.id)
    proposals = list(
        session.scalars(
            select(AiChangeProposal).where(AiChangeProposal.tailoring_run_id == run.id)
        )
    )
    assert proposals
    assert proposals[0].target_id == bullet.id
    assert proposals[0].status == "proposed"

    app_service.decide_proposals({proposals[0].id: "accepted"})
    snapshot = app_service.create_snapshot(application.id)
    assert "Alex Example" in snapshot.rendered_markdown

    SettingsService(session).set(
        "exports", {"markdown": False, "html": False, "pdf": True, "docx": True}
    )
    artifacts = app_service.export_snapshot(snapshot.id, tmp_path)
    assert {artifact.artifact_type for artifact in artifacts} == {"pdf", "docx"}
    assert all(not artifact.relative_path.startswith("/") for artifact in artifacts)
    assert len(list(session.scalars(select(Artifact)))) == 2


def test_fact_required_bullet_can_be_detected(session):
    _profile, _resume, bullet = build_resume(session)
    stored = session.get(ResumeBullet, bullet.id)
    assert stored is not None
    assert stored.fact_link_required is True
