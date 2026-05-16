from __future__ import annotations

from sqlalchemy import select

from app.applications.service import ApplicationService
from app.cover_letters.service import CoverLetterService
from app.db.models import ApplicationEvent, PromptTemplate
from app.llm.prompts.tailoring import build_summary_prompt
from app.people.service import PeopleService
from app.resumes.service import ResumeService
from app.settings.service import PROTECTED_SAFETY_PROMPT, SettingsService


def _profile_resume(session, name: str = "Alex"):
    profile = PeopleService(session).create_profile(name, f"{name} Example", "Remote")
    resume = ResumeService(session).create_resume(
        profile.id,
        "Backend Developer",
        "Backend Developer",
        create_standard_sections=True,
    )
    return profile, resume


def test_active_profile_can_be_set_read_and_cleared_when_missing(session):
    profile, _resume = _profile_resume(session)
    service = SettingsService(session)

    service.set_active_profile(profile.id)
    assert service.get_active_profile_id() == profile.id
    assert service.require_active_profile().display_name == profile.display_name

    session.delete(profile)
    session.commit()
    assert service.get_active_profile() is None


def test_default_prompt_templates_are_sql_backed_and_safety_is_protected(session):
    service = SettingsService(session)
    templates = service.list_prompt_templates()
    assert {template.block_type for template in templates} >= {
        "summary",
        "skills",
        "work_experience_bullet",
        "job_title",
        "description_custom_block",
        "cover_letter",
    }
    template = templates[0]
    service.update_prompt_template(template.id, "Use concise user wording only.")
    stored = session.get(PromptTemplate, template.id)
    assert stored is not None
    assert stored.user_prompt_template == "Use concise user wording only."
    assert stored.system_prompt == PROTECTED_SAFETY_PROMPT


def test_prompt_payload_keeps_safety_and_excludes_private_contact_fields():
    payload = build_summary_prompt(
        block={
            "id": 1,
            "target_type": "resume_block",
            "text": "Builder",
            "email": "private@example.test",
            "phone": "+1",
        },
        requirements=[],
        facts=[],
        policy={},
    )
    assert "private contact" in payload.system_prompt.lower()
    assert "private@example.test" not in str(payload.user_payload)
    assert "+1" not in str(payload.user_payload)


def test_standard_resume_skeleton_and_reference_policy(session):
    profile, resume = _profile_resume(session)
    resume = ResumeService(session).get_resume(resume.id)
    section_titles = [section.title for section in resume.sections]
    assert section_titles == [
        "Summary",
        "Skills",
        "Work Experience",
        "Education",
        "Languages",
        "Certifications",
        "References",
    ]
    skills = next(
        section for section in resume.sections if section.section_type == "skills"
    )
    assert [block.title for block in skills.blocks] == ["Hard Skills", "Soft Skills"]
    references = next(
        section for section in resume.sections if section.section_type == "references"
    )
    assert references.blocks[0].ai_edit_enabled is False
    assert resume.profile_id == profile.id


def test_application_events_update_likely_applied_dashboard_metrics(session):
    profile, resume = _profile_resume(session)
    service = ApplicationService(session)
    application = service.create_application(
        profile_id=profile.id,
        resume_id=resume.id,
        job_title="Engineer",
        company_name="Acme",
        source_url="",
        raw_job_text="Python SQL",
    )
    service.record_copy_event(application.id, "resume_text", "full", "resume")
    stats = service.dashboard_stats(profile.id)
    assert stats.application_count == 1
    assert stats.likely_applied_count == 1
    assert any(day["count"] == 1 for day in stats.activity_days)
    service.mark_manually_applied(application.id)
    assert service.dashboard_stats(profile.id).manually_marked_applied_count == 1
    event_types = [
        event.event_type for event in session.scalars(select(ApplicationEvent))
    ]
    assert "likely_applied" in event_types
    assert "manually_marked_applied" in event_types


def test_adapt_flow_generates_requirements_proposals_and_cover_letter(session):
    profile = PeopleService(session).create_profile("Alex", "Alex Example", "Remote")
    fact = PeopleService(session).create_fact(
        profile.id,
        fact_key="python",
        category="backend",
        claim="Built Python services.",
        evidence="Local notes",
        source="self-review",
        allowed_claim_level="practical",
    )
    resumes = ResumeService(session)
    resume = resumes.create_resume(profile.id, "Backend", "Backend Developer")
    section = resumes.add_section(resume.id, "work_experience", "Work Experience", True)
    block = resumes.add_block(section.id, block_type="work_experience", title="Backend")
    bullet = resumes.add_bullet(
        block.id,
        "Built Python services.",
        ai_edit_enabled=True,
        fact_link_required=True,
        fact_ids=[fact.id],
    )
    app = ApplicationService(session).adapt_application(
        profile_id=profile.id,
        resume_id=resume.id,
        job_title="API Engineer",
        company_name="Acme",
        source_url="",
        raw_job_text="Python FastAPI SQL",
    )
    run = ApplicationService(session).latest_tailoring_run(app.id)
    assert app.requirements
    assert run is not None
    assert run.proposals
    assert run.proposals[0].target_id == bullet.id
    assert CoverLetterService(session).latest(app.id) is not None

    proposal = run.proposals[0]
    ApplicationService(session).save_review_decisions(
        app.id,
        {proposal.id: "accepted_edited"},
        {proposal.id: "Edited tailored text."},
    )
    snapshot = ApplicationService(session).create_snapshot(app.id)
    assert "Edited tailored text." in snapshot.rendered_markdown
