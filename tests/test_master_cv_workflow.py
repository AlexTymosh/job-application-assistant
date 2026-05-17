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


def test_application_adapt_rejects_resume_from_another_profile(app_client, session):
    profile_a = PeopleService(session).create_profile("Profile A", "Profile A")
    profile_b = PeopleService(session).create_profile("Profile B", "Profile B")
    other_resume = ResumeService(session).create_resume(
        profile_b.id, "Other Resume", "Other Role", create_standard_sections=True
    )
    from app.settings.service import SettingsService

    SettingsService(session).set_active_profile(profile_a.id)
    response = app_client.post(
        "/applications/adapt",
        data={"resume_id": str(other_resume.id), "raw_job_text": "Python role"},
    )
    assert response.status_code == 400
    assert "active profile" in response.text
    assert ApplicationService(session).list_applications(profile_a.id) == []
    assert ApplicationService(session).list_applications(profile_b.id) == []


def test_application_routes_are_active_profile_scoped(app_client, session):
    profile_a = PeopleService(session).create_profile("Profile A", "Profile A")
    profile_b, resume_b = create_profile_resume(session)
    from app.settings.service import SettingsService

    application = ApplicationService(session).create_application(
        profile_id=profile_b.id,
        resume_id=resume_b.id,
        raw_job_text="FastAPI role",
    )
    ApplicationService(session).adapt_application(application.id)
    SettingsService(session).set_active_profile(profile_a.id)
    guarded_paths = [
        f"/applications/{application.id}",
        f"/applications/{application.id}/tailored-resume",
        f"/applications/{application.id}/tailored-resume/exports/pdf/download",
    ]
    for path in guarded_paths:
        response = app_client.get(path, follow_redirects=False)
        assert response.status_code == 404
    post_response = app_client.post(
        f"/applications/{application.id}/tailored-resume/export/pdf",
        follow_redirects=False,
    )
    assert post_response.status_code == 404


def test_applications_page_does_not_list_all_without_active_profile(
    app_client, session
):
    profile_a, resume_a = create_profile_resume(session)
    profile_b = PeopleService(session).create_profile("Profile B", "Profile B")
    resume_b = ResumeService(session).create_resume(
        profile_b.id, "Profile B Resume", "Role B", create_standard_sections=True
    )
    ApplicationService(session).create_application(
        profile_id=profile_a.id,
        resume_id=resume_a.id,
        raw_job_text="Profile A job",
        job_title="Profile A job",
    )
    ApplicationService(session).create_application(
        profile_id=profile_b.id,
        resume_id=resume_b.id,
        raw_job_text="Profile B job",
        job_title="Profile B job",
    )
    from app.settings.service import SettingsService

    SettingsService(session).set_active_profile(None)
    response = app_client.get("/applications")
    assert response.status_code == 200
    assert "Select an active profile" in response.text
    assert "Profile A job" not in response.text
    assert "Profile B job" not in response.text


def test_dashboard_stats_contract_zero_one_and_ranges(session):
    profile, resume = create_profile_resume(session)
    service = ApplicationService(session)
    empty_stats = service.dashboard_stats(profile.id, days=10)
    assert empty_stats["profile_name"] == profile.display_name
    assert empty_stats["resume_count"] == 1
    assert empty_stats["application_count"] == 0
    assert len(empty_stats["activity_days"]) == 10
    assert empty_stats["activity_range_days"] == 10
    app = service.create_application(
        profile_id=profile.id,
        resume_id=resume.id,
        raw_job_text="Python role",
        job_title="Python Developer",
    )
    one_stats = service.dashboard_stats(profile.id, days=20)
    assert one_stats["application_count"] == 1
    assert one_stats["applications_last_30_days"] == 1
    assert len(one_stats["activity_days"]) == 20
    assert one_stats["recent_applications"][0].id == app.id
    assert service.dashboard_stats(profile.id, days=30)["activity_range_days"] == 30
    assert service.dashboard_stats(profile.id, days=99)["activity_range_days"] == 30


def test_indexed_repeating_checkboxes_preserve_row_state(session):
    profile = PeopleService(session).create_profile("Rows", "Rows Example")
    resume = ResumeService(session).create_resume(
        profile.id, "Rows Resume", "Rows", create_standard_sections=True
    )
    service = ResumeService(session)
    service.save_section(
        resume.id,
        "work_experience",
        {
            "rows[0][job_title]": "First",
            "rows[0][employer]": "One Ltd",
            "rows[0][key_bullets]": "First bullet",
            "rows[1][job_title]": "Second",
            "rows[1][employer]": "Two Ltd",
            "rows[1][is_current]": "on",
            "rows[1][optional_extra_enabled]": "on",
            "rows[1][optional_extra_text]": "Extra visible",
            "rows[1][key_bullets]": "Second bullet",
        },
    )
    work_blocks = service.section_for_type(resume.id, "work_experience").blocks
    assert [block.is_current for block in work_blocks] == [False, True]
    assert [block.optional_extra_enabled for block in work_blocks] == [False, True]
    service.save_section(
        resume.id,
        "education",
        {
            "rows[0][institution_name]": "First University",
            "rows[0][specialisation]": "First Degree",
            "rows[0][key_bullets]": "First achievement",
            "rows[1][institution_name]": "Second University",
            "rows[1][specialisation]": "Second Degree",
            "rows[1][is_current]": "on",
            "rows[1][key_bullets]": "Second achievement",
        },
    )
    education_blocks = service.section_for_type(resume.id, "education").blocks
    assert [block.is_current for block in education_blocks] == [False, True]


def test_prompt_resolution_order_is_in_tailoring_payload(session):
    profile, resume = create_profile_resume(session)
    from app.settings.service import SettingsService

    settings = SettingsService(session)
    settings.upsert_scoped_prompt_template(
        scope="global",
        block_type="summary",
        user_prompt_template="global summary",
    )
    payload = TailoringService(session).build_payload(resume, [], "job")
    assert payload.prompt_instructions["summary"] == "global summary"
    settings.upsert_scoped_prompt_template(
        scope="profile",
        block_type="summary",
        profile_id=profile.id,
        user_prompt_template="profile summary",
    )
    assert (
        TailoringService(session)
        .build_payload(resume, [], "job")
        .prompt_instructions["summary"]
        == "profile summary"
    )
    settings.upsert_scoped_prompt_template(
        scope="resume",
        block_type="summary",
        resume_id=resume.id,
        user_prompt_template="resume summary",
    )
    assert (
        TailoringService(session)
        .build_payload(resume, [], "job")
        .prompt_instructions["summary"]
        == "resume summary"
    )
    section_id = ResumeService(session).section_for_type(resume.id, "summary").id
    settings.upsert_scoped_prompt_template(
        scope="section",
        block_type="summary",
        section_id=section_id,
        user_prompt_template="section summary",
    )
    payload = TailoringService(session).build_payload(resume, [], "job")
    assert payload.prompt_instructions["summary"] == "section summary"
    client = DeterministicTailoringClient()
    ApplicationService(session).adapt_application(
        ApplicationService(session)
        .create_application(
            profile_id=profile.id, resume_id=resume.id, raw_job_text="Python role"
        )
        .id,
        client=client,
    )
    assert client.last_payload.prompt_instructions["summary"] == "section summary"


def test_cover_letter_generated_and_displayed(app_client, session):
    profile, resume = create_profile_resume(session)
    from app.settings.service import SettingsService

    SettingsService(session).set_active_profile(profile.id)
    response = app_client.post(
        "/applications/adapt",
        data={"resume_id": str(resume.id), "raw_job_text": "FastAPI role"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "Cover Letter" in response.text
    assert "Edit saved tailored resume" not in response.text
    assert "Download cover letter TXT" in response.text
    application = ApplicationService(session).list_applications(profile.id)[0]
    assert (
        ApplicationService(session).get_tailored_resume(application.id).id is not None
    )
    cover_letter = ApplicationService(session).latest_cover_letter(application.id)
    assert cover_letter is not None
    assert "Thank you for considering my application" in cover_letter.content


def test_master_cv_uses_builder_style(app_client, session):
    profile = PeopleService(session).create_profile("Master", "Master Example")
    response = app_client.get(f"/profiles/{profile.id}/master-cv/work_experience")
    assert response.status_code == 200
    assert "builder-shell" in response.text
    assert "builder-nav" in response.text
    assert "Extended Experience Preview" in response.text
    assert "Fact checking" not in response.text
    assert "Evidence matrix" not in response.text
    app_client.post(
        f"/profiles/{profile.id}/master-cv",
        data={
            "category": "tool",
            "title": "Poetry",
            "content": "Used Poetry for dependency management.",
        },
    )
    tool_page = app_client.get(f"/profiles/{profile.id}/master-cv/tool")
    assert "Poetry" in tool_page.text
    assert "Used Poetry" in tool_page.text


def test_docx_export_is_styled_without_markdown_markers(session, tmp_path: Path):
    from zipfile import ZipFile

    profile, resume = create_profile_resume(session)
    docx_path = ResumeService(session).export_base_resume(resume.id, "docx", tmp_path)
    with ZipFile(docx_path) as archive:
        document_xml = archive.read("word/document.xml").decode("utf-8")
    assert "PROFESSIONAL EXPERIENCE" in document_xml
    assert "##" not in document_xml
    assert "**" not in document_xml
    assert "w:pBdr" in document_xml


def test_pdf_export_supports_non_ascii_content(session, tmp_path: Path):
    profile = PeopleService(session).create_profile("Олексій", "Олексій Тимошенко")
    resume = ResumeService(session).create_resume(
        profile.id, "Unicode Resume", "Software Engineer", create_standard_sections=True
    )
    ResumeService(session).save_section(
        resume.id,
        "header",
        {"first_name": "Олексій", "surname": "Тимошенко", "email": "abc@example.com"},
    )
    pdf_path = ResumeService(session).export_base_resume(resume.id, "pdf", tmp_path)
    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 1000


def test_application_workflow_rejects_missing_active_profile_and_empty_job(
    app_client, session
):
    profile, resume = create_profile_resume(session)
    from app.settings.service import SettingsService

    SettingsService(session).set_active_profile(None)
    no_active = app_client.post(
        "/applications/adapt",
        data={"resume_id": str(resume.id), "raw_job_text": "Python role"},
    )
    assert no_active.status_code == 400
    assert "Select an active profile" in no_active.text
    SettingsService(session).set_active_profile(profile.id)
    empty_job = app_client.post(
        "/applications/adapt",
        data={"resume_id": str(resume.id), "raw_job_text": ""},
    )
    assert empty_job.status_code == 400
    assert "Paste a job description" in empty_job.text
