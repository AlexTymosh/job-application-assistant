from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.applications.service import ApplicationService
from app.core.errors import ValidationAppError
from app.main import create_app
from app.people.service import PeopleService
from app.resumes.renderer import render_resume_markdown
from app.resumes.service import ResumeService
from app.settings.service import SettingsService


def _create_profile(client, name="Alex") -> int:
    response = client.post(
        "/profiles/new",
        data={"display_name": name, "full_name": f"{name} Example"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    return int(response.headers["location"].rsplit("/", 1)[1])


def _create_resume(client, profile_id: int, name="Backend") -> int:
    response = client.post(
        f"/profiles/{profile_id}/resumes/new",
        data={
            "name": name,
            "target_role": "Backend Developer",
            "language": "en",
            "create_standard_sections": "on",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    return int(response.headers["location"].rsplit("/", 1)[1])


def test_facts_page_with_and_without_active_profile(app_client):
    empty = app_client.get("/settings/active-profile/facts")
    assert empty.status_code == 200
    assert "No active profile selected" in empty.text

    profile_id = _create_profile(app_client)
    page = app_client.get("/settings/active-profile/facts")
    assert page.status_code == 200
    assert f"/profiles/{profile_id}/facts/new" in page.text
    settings = app_client.get("/settings")
    assert "/settings/active-profile/facts" in settings.text
    assert "Manage active profile facts" in settings.text


def test_adapt_blocks_missing_profile_missing_resume_and_wrong_resume(app_client):
    no_profile = app_client.post(
        "/applications/adapt",
        data={"resume_id": "1", "raw_job_text": "Python"},
    )
    assert no_profile.status_code == 400
    assert "Active profile required" in no_profile.text

    profile_id = _create_profile(app_client)
    no_resume_page = app_client.get("/applications")
    assert "Create resume first" in no_resume_page.text
    no_resume = app_client.post("/applications/adapt", data={"raw_job_text": "Python"})
    assert no_resume.status_code == 400
    assert "Create a resume" in no_resume.text

    other_profile_id = _create_profile(app_client, "Other")
    other_resume_id = _create_resume(app_client, other_profile_id, "Other resume")
    app_client.post(
        "/settings/active-profile",
        data={"active_profile_id": profile_id, "next": "/applications"},
        follow_redirects=False,
    )
    wrong_resume = app_client.post(
        "/applications/adapt",
        data={"resume_id": other_resume_id, "raw_job_text": "Python FastAPI"},
    )
    assert wrong_resume.status_code == 404
    assert "Resume must belong to the active profile" in wrong_resume.text


def test_snapshot_without_tailoring_run_is_friendly(app_client, session):
    profile_id = _create_profile(app_client)
    resume_id = _create_resume(app_client, profile_id)
    application = ApplicationService(session).create_application(
        profile_id=profile_id,
        resume_id=resume_id,
        job_title="",
        company_name="",
        source_url="",
        raw_job_text="Python",
    )
    response = app_client.post(f"/applications/{application.id}/snapshot")
    assert response.status_code == 400
    assert "Run tailoring before creating" in response.text


def test_snapshot_errors_and_successful_export_flow(app_client, session):
    profile_id = _create_profile(app_client)
    resume_id = _create_resume(app_client, profile_id)
    service = ResumeService(session)
    resume = service.get_resume(resume_id)
    work_section = next(
        section
        for section in resume.sections
        if section.section_type == "work_experience"
    )
    block = service.add_block(
        work_section.id,
        block_type="work_experience",
        role_title="Engineer",
        organisation="Example",
        start_date="2023",
        is_current=True,
    )
    PeopleService(session).create_fact(
        profile_id,
        fact_key="python",
        category="backend",
        claim="Built Python services.",
        evidence="Review",
        source="self",
        allowed_claim_level="practical",
    )
    service.add_bullet(
        block.id,
        "Built Python services.",
        ai_edit_enabled=True,
        fact_link_required=False,
    )

    created = app_client.post(
        "/applications/adapt",
        data={"resume_id": resume_id, "raw_job_text": "Python FastAPI SQL"},
        follow_redirects=False,
    )
    assert created.status_code == 303
    application_id = int(created.headers["location"].rsplit("/", 1)[1])

    no_accept = app_client.post(f"/applications/{application_id}/snapshot")
    assert no_accept.status_code == 400
    assert "Accept at least one proposal" in no_accept.text

    detail = app_client.get(f"/applications/{application_id}")
    proposal_id = int(detail.text.split('name="decision_', 1)[1].split('"', 1)[0])
    reviewed = app_client.post(
        f"/applications/{application_id}/review",
        data={
            f"decision_{proposal_id}": "accepted_edited",
            f"after_text_{proposal_id}": "Delivered edited Python API impact.",
        },
        follow_redirects=False,
    )
    assert reviewed.status_code == 303
    snapshot = app_client.post(
        f"/applications/{application_id}/snapshot", follow_redirects=False
    )
    assert snapshot.status_code == 303
    exports = app_client.get(snapshot.headers["location"])
    assert exports.status_code == 200
    assert "Export" in exports.text
    run_exports = app_client.post(
        f"/applications/{application_id}/exports",
        data={"snapshot_id": snapshot.headers["location"].split("snapshot_id=")[1]},
        follow_redirects=False,
    )
    assert run_exports.status_code == 303
    assert "Download" in app_client.get(f"/applications/{application_id}").text


def test_renderer_hides_empty_sections_and_uppercases_titles(session):
    profile = PeopleService(session).create_profile("Alex", "Alex Example", "")
    resumes = ResumeService(session)
    resume = resumes.create_resume(
        profile.id, "Backend", "Backend", create_standard_sections=True
    )
    summary = next(
        section for section in resume.sections if section.section_type == "summary"
    )
    block = summary.blocks[0]
    resumes.update_block(
        block.id, block_type="summary", title="", content="Experienced engineer."
    )
    rendered = render_resume_markdown(resumes.get_resume(resume.id))
    assert "## SUMMARY" in rendered
    assert "WORK EXPERIENCE" not in rendered
    builder = TestClient(create_app()).get if False else None
    assert builder is None


def test_resume_metadata_edit_upload_and_prompt_scope(app_client, session):
    profile_id = _create_profile(app_client)
    response = app_client.post(
        f"/profiles/{profile_id}/resumes/new",
        data={
            "name": "Uploaded",
            "target_role": "Engineer",
            "language": "en",
            "create_standard_sections": "on",
        },
        files={"resume_file": ("../resume.pdf", b"%PDF", "application/pdf")},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert app_client.app.state.last_resume_upload_path.startswith("artifacts/uploads/")
    bad = app_client.post(
        f"/profiles/{profile_id}/resumes/new",
        data={"name": "Bad", "target_role": "Engineer", "language": "en"},
        files={"resume_file": ("bad.exe", b"x", "application/octet-stream")},
    )
    assert bad.status_code == 400

    resume_id = int(response.headers["location"].rsplit("/", 1)[1])
    edited = app_client.post(
        f"/resumes/{resume_id}/edit",
        data={"name": "Updated", "target_role": "API Engineer", "language": "en"},
        follow_redirects=False,
    )
    assert edited.status_code == 303
    assert "Updated" in app_client.get(f"/profiles/{profile_id}/resumes").text
    assert "Updated" in app_client.get("/applications").text

    settings = SettingsService(session)
    settings.upsert_prompt_instruction(
        block_type="summary",
        user_prompt_template="profile",
        scope=f"profile:{profile_id}",
    )
    settings.upsert_prompt_instruction(
        block_type="summary", user_prompt_template="resume", scope=f"resume:{resume_id}"
    )
    resume = ResumeService(session).get_resume(resume_id)
    section_id = resume.sections[0].id
    settings.upsert_prompt_instruction(
        block_type="summary",
        user_prompt_template="section",
        scope=f"section:{section_id}",
        section_type=resume.sections[0].section_type,
    )
    assert (
        settings.get_prompt_instruction("summary", profile_id=profile_id) == "profile"
    )
    assert (
        settings.get_prompt_instruction(
            "summary", profile_id=profile_id, resume_id=resume_id
        )
        == "resume"
    )
    assert (
        settings.get_prompt_instruction(
            "summary",
            profile_id=profile_id,
            resume_id=resume_id,
            section_id=section_id,
            section_type=resume.sections[0].section_type,
        )
        == "section"
    )
    assert "Protected safety rules" not in app_client.get("/settings/prompts").text


def test_error_handlers_render_navigation(monkeypatch, tmp_path):
    monkeypatch.setenv("APP_DATA_DIR", str(tmp_path / "data"))
    app: FastAPI = create_app()

    @app.get("/domain-error-test")
    def domain_error_test():
        raise ValidationAppError("Friendly failure.")

    @app.get("/unexpected-error-test")
    def unexpected_error_test():
        raise RuntimeError("boom")

    client = TestClient(app, raise_server_exceptions=False)
    domain = client.get("/domain-error-test")
    assert domain.status_code == 400
    assert "Friendly failure." in domain.text
    assert (
        "Dashboard" in domain.text
        and "Application" in domain.text
        and "Settings" in domain.text
    )
    unexpected = client.get("/unexpected-error-test")
    assert unexpected.status_code == 500
    assert "Something went wrong" in unexpected.text
