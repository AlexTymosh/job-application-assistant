from __future__ import annotations

from pathlib import Path

from sqlalchemy import inspect

from app.applications.service import ApplicationService
from app.people.service import PeopleService
from app.resumes.renderer import render_resume_markdown
from app.resumes.service import ResumeService
from app.tailoring.service import DeterministicTailoringClient, TailoringService


def create_profile_resume(session):
    profile = PeopleService(session).create_profile(
        "Oleksii Tymoshenko", "Oleksii Tymoshenko"
    )
    resume = ResumeService(session).create_resume(
        profile.id,
        "Software Engineer",
        "Software Engineer",
        create_standard_sections=True,
        is_default=True,
    )
    service = ResumeService(session)
    service.save_section(
        resume.id,
        "header",
        {
            "first_name": "Oleksii",
            "surname": "Tymoshenko",
            "phone": "+44",
            "email": "abc@gmail.com",
            "linkedin_url": "LinkedIn",
            "github_url": "GitHub",
            "location": "Basingstoke",
            "extra_text": "Right to work in UK",
        },
    )
    service.save_section(
        resume.id,
        "summary",
        {"description": "Backend Developer with Python and FastAPI experience."},
    )
    service.save_section(
        resume.id,
        "skills",
        {"hard_skills_text": "Python, FastAPI", "soft_skills_text": "Team Player"},
    )
    service.save_section(
        resume.id,
        "work_experience",
        {
            "job_title": ["Software Developer"],
            "employer": ["Hydro UK"],
            "start_date": ["09/2024"],
            "end_date": [""],
            "is_current": ["on"],
            "optional_extra_enabled": [""],
            "optional_extra_text": [""],
            "key_bullets": ["Built REST APIs."],
        },
    )
    service.save_section(
        resume.id,
        "education",
        {
            "institution_name": ["Zaporizhzhia National University"],
            "specialisation": ["Master's Degree in Finance"],
            "start_date": ["09/2011"],
            "end_date": ["01/2018"],
            "is_current": [""],
            "key_bullets": ["Graduated with honours."],
        },
    )
    service.save_section(
        resume.id,
        "languages",
        {"language": ["English"], "level": ["Upper-Intermediate"]},
    )
    service.save_section(
        resume.id,
        "certificates",
        {
            "certificate_name": ["Python for Data Science"],
            "certificate_url": ["https://example.com"],
            "issue_year": ["2023"],
        },
    )
    service.save_section(
        resume.id,
        "references",
        {
            "name": ["John Money"],
            "role_title": ["Managing Director"],
            "company": ["Hydro UK Ltd"],
            "phone": ["+44 123"],
            "email": ["john@example.com"],
            "linkedin_url": [""],
        },
    )
    return profile, service.get_resume(resume.id)


def test_empty_database_initialises_clean_master_cv_schema(session):
    tables = set(inspect(session.bind).get_table_names())
    assert "master_cvs" in tables
    assert "master_cv_entries" in tables
    assert "tailored_resumes" in tables
    assert "facts" not in tables
    assert "resume_bullet_fact_links" not in tables


def test_cv_builder_sections_and_preview_hide_empty_sections(session):
    profile = PeopleService(session).create_profile("Alex", "Alex Example")
    resume = ResumeService(session).create_resume(
        profile.id,
        "Backend Developer",
        "Backend Developer",
        create_standard_sections=True,
    )
    service = ResumeService(session)
    service.save_section(
        resume.id,
        "header",
        {
            "first_name": "Alex",
            "surname": "Example",
            "email": "alex@example.com",
            "phone": "",
            "location": "Remote",
            "linkedin_url": "",
            "github_url": "",
            "extra_text": "",
        },
    )
    service.save_section(resume.id, "summary", {"description": "Builds reliable APIs."})
    service.save_section(
        resume.id,
        "skills",
        {"hard_skills_text": "Python", "soft_skills_text": "Detail-Oriented"},
    )
    markdown = render_resume_markdown(service.get_resume(resume.id))
    assert (
        "ALEX EXAMPLE" not in markdown
    )  # Markdown keeps source casing; visual template uppercases via CSS.
    assert "Alex Example" in markdown
    assert "## Certificates" not in markdown
    assert "## References" not in markdown
    header_section = service.section_for_type(resume.id, "header")
    assert header_section.ai_edit_enabled is False
    assert all(block.ai_edit_enabled is False for block in header_section.blocks)


def test_master_cv_entry_can_be_created_and_listed(session):
    profile = PeopleService(session).create_profile("Oleksii", "Oleksii Tymoshenko")
    entry = PeopleService(session).create_master_entry(
        profile.id,
        category="tool",
        title="Poetry",
        content="Used Poetry for Python dependency management.",
        keywords="Poetry, Python dependency management",
        allowed_wording="Python dependency management experience",
        forbidden_wording="uv experience",
        inference_notes="Do not claim uv unless explicitly present.",
        claim_strength="normal",
    )
    entries = PeopleService(session).list_master_entries(profile.id)
    assert entries == [entry]
    assert entries[0].allowed_wording == "Python dependency management experience"
    assert entries[0].forbidden_wording == "uv experience"


def test_tailoring_uses_master_cv_without_private_payload(session):
    profile, resume = create_profile_resume(session)
    PeopleService(session).create_master_entry(
        profile.id,
        category="tool",
        title="Poetry",
        content="Used Poetry for Python dependency management.",
        keywords="Poetry",
        allowed_wording="Python dependency management experience",
        forbidden_wording="uv experience",
        inference_notes="Related tools require cautious wording.",
    )
    application = ApplicationService(session).create_application(
        profile_id=profile.id,
        resume_id=resume.id,
        raw_job_text="We need Python dependency management and FastAPI.",
    )
    client = DeterministicTailoringClient()
    tailored = ApplicationService(session).adapt_application(
        application.id, client=client
    )
    assert tailored.id is not None
    assert client.last_payload is not None
    assert "header" not in client.last_payload.base_resume["sections"]
    assert "references" not in client.last_payload.base_resume["sections"]
    assert client.last_payload.master_cv_items[0]["title"] == "Poetry"
    assert "Python dependency management experience" in tailored.rendered_markdown
    assert "uv experience" not in tailored.rendered_markdown
    refreshed = ApplicationService(session).get_application(application.id)
    assert refreshed.tailored_resume_id == tailored.id


def test_prompt_payload_builder_excludes_contact_and_reference_data(session):
    profile, resume = create_profile_resume(session)
    PeopleService(session).create_master_entry(
        profile.id, category="skill", title="FastAPI", content="Built FastAPI services."
    )
    payload = TailoringService(session).build_payload(
        resume, PeopleService(session).list_master_entries(profile.id), "FastAPI role"
    )
    assert "header" not in payload.base_resume["sections"]
    assert "references" not in payload.base_resume["sections"]
    assert "+44" not in str(payload.base_resume)
    assert "john@example.com" not in str(payload.base_resume)


def test_exports_for_base_and_tailored_resume_work(session, tmp_path: Path):
    profile, resume = create_profile_resume(session)
    PeopleService(session).create_master_entry(
        profile.id,
        category="skill",
        title="FastAPI",
        content="Built FastAPI APIs.",
        allowed_wording="FastAPI APIs",
    )
    base_pdf = ResumeService(session).export_base_resume(resume.id, "pdf", tmp_path)
    base_docx = ResumeService(session).export_base_resume(resume.id, "docx", tmp_path)
    assert base_pdf.exists() and base_pdf.stat().st_size > 0
    assert base_docx.exists() and base_docx.stat().st_size > 0
    application = ApplicationService(session).create_application(
        profile_id=profile.id, resume_id=resume.id, raw_job_text="FastAPI APIs"
    )
    ApplicationService(session).adapt_application(application.id)
    tailored_pdf = ApplicationService(session).export_tailored_resume(
        application.id, "pdf", tmp_path
    )
    tailored_docx = ApplicationService(session).export_tailored_resume(
        application.id, "docx", tmp_path
    )
    assert tailored_pdf.exists() and tailored_pdf.stat().st_size > 0
    assert tailored_docx.exists() and tailored_docx.stat().st_size > 0
    assert (
        "## Professional Experience"
        in ApplicationService(session)
        .get_tailored_resume(application.id)
        .rendered_markdown
    )


def test_ui_routes_render_new_workflow(app_client):
    app_client.post(
        "/profiles/new",
        data={"display_name": "Oleksii", "full_name": "Oleksii Tymoshenko"},
    )
    response = app_client.get("/cv-builder")
    assert response.status_code == 200
    assert "Resume Variants" in response.text
    assert "Master CV" in response.text
    assert "Fact checking" not in response.text
    response = app_client.post(
        "/profiles/1/resumes/new",
        data={"name": "Software Engineer", "target_role": "Software Engineer"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    builder = app_client.get(response.headers["location"])
    assert builder.status_code == 200
    assert "builder-nav" in builder.text
    assert "Live preview" in builder.text
    assert "Header" in builder.text
    app_client.post(
        "/profiles/1/master-cv",
        data={
            "category": "skill",
            "title": "FastAPI",
            "content": "Built APIs",
            "allowed_wording": "FastAPI APIs",
        },
    )
    tailored = app_client.post(
        "/applications/adapt",
        data={"resume_id": "1", "raw_job_text": "FastAPI APIs"},
        follow_redirects=True,
    )
    assert tailored.status_code == 200
    assert "Tailored Resume" in tailored.text
    assert "Evidence matrix" not in tailored.text
