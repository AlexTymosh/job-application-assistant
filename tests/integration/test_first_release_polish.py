from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import inspect, select, text

from app.applications.service import ApplicationService
from app.db.models import AppSetting, Resume, ResumeSection, ResumeUpload
from app.db.session import (
    create_session_factory,
    create_sqlite_engine,
    initialise_database,
)
from app.main import create_app
from app.people.service import PeopleService
from app.resumes.service import ResumeService
from app.settings.service import SettingsService
from tests.conftest import MemorySecretService


def _create_profile(client: TestClient, name: str = "Alex") -> int:
    response = client.post(
        "/profiles/new",
        data={"display_name": name, "full_name": f"{name} Example"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    return int(response.headers["location"].rstrip("/").split("/")[-1])


def _create_resume(
    client: TestClient, profile_id: int, name: str = "Backend CV"
) -> int:
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
    return int(response.headers["location"].rstrip("/").split("/")[-1])


def test_sqlite_schema_repair_adds_old_facts_columns_and_adapt_runs(tmp_path: Path):
    engine = create_sqlite_engine(tmp_path / "old.db")
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE facts ("
                "id INTEGER PRIMARY KEY, "
                "profile_id INTEGER NOT NULL, "
                "fact_key VARCHAR(120) NOT NULL)"
            )
        )
    initialise_database(engine)
    columns = {column["name"] for column in inspect(engine).get_columns("facts")}
    assert "claim" in columns
    assert "evidence" in columns
    assert "is_active" in columns

    factory = create_session_factory(engine)
    with factory() as session:
        profile = PeopleService(session).create_profile(
            "Alex", "Alex Example", "Remote"
        )
        resume = ResumeService(session).create_resume(
            profile.id, "Backend", "Backend Developer", create_standard_sections=True
        )
        app = ApplicationService(session).adapt_application(
            profile_id=profile.id,
            resume_id=resume.id,
            job_title="API Engineer",
            company_name="Acme",
            source_url="",
            raw_job_text="Python FastAPI SQL",
        )
        assert app.id is not None


def test_settings_split_forms_preserve_unrelated_values(
    app_client: TestClient, session
):
    service = SettingsService(session)
    service.set("exports", {"markdown": True, "html": True, "pdf": True, "docx": True})
    service.set(
        "ai_policy_defaults",
        {
            "fact_links_required": True,
            "allow_new_bullets": True,
            "allow_hide_bullets": True,
            "allow_title_edits": True,
        },
    )

    app_client.post("/settings", data={"locale": "ru"}, follow_redirects=False)
    assert service.get("exports")["pdf"] is True
    assert service.get("ai_policy_defaults")["allow_hide_bullets"] is True

    app_client.post(
        "/settings", data={"openai_api_key": "sk-test"}, follow_redirects=False
    )
    assert service.get("exports")["docx"] is True
    assert service.get("ai_policy_defaults")["allow_title_edits"] is True
    assert session.get(AppSetting, "openai_api_key") is None

    app_client.post("/settings", data={"export_pdf": "on"}, follow_redirects=False)
    assert service.get("exports") == {
        "markdown": False,
        "html": False,
        "pdf": True,
        "docx": False,
    }
    assert service.get("ai_policy_defaults")["fact_links_required"] is True

    app_client.post(
        "/settings", data={"allow_new_bullets": "on"}, follow_redirects=False
    )
    assert service.get("exports")["pdf"] is True
    assert service.get("ai_policy_defaults") == {
        "fact_links_required": False,
        "allow_new_bullets": True,
        "allow_hide_bullets": False,
        "allow_title_edits": False,
    }

    app_client.post(
        "/settings",
        data={
            "openai_model_default": "model-default",
            "openai_model_qa": "model-qa",
            "openai_model_extract": "model-extract",
            "openai_model_tailor": "model-tailor",
        },
        follow_redirects=False,
    )
    assert service.get("openai_model_tailor") == "model-tailor"
    assert service.get("exports")["pdf"] is True


def test_invalid_upload_does_not_create_ghost_resume(
    app_client: TestClient, session, tmp_path: Path
):
    profile_id = _create_profile(app_client)
    before = session.scalar(select(Resume).where(Resume.profile_id == profile_id))
    assert before is None
    response = app_client.post(
        f"/profiles/{profile_id}/resumes/new",
        data={"name": "Bad", "target_role": "Engineer", "language": "en"},
        files={"resume_upload": ("bad.exe", b"nope", "application/octet-stream")},
    )
    assert response.status_code == 400
    assert (
        list(session.scalars(select(Resume).where(Resume.profile_id == profile_id)))
        == []
    )
    assert list(session.scalars(select(ResumeUpload))) == []
    upload_root = app_client.app.state.app_data_paths.root / "artifacts" / "uploads"
    assert not upload_root.exists()


def test_dashboard_ranges_navigation_and_cv_builder(app_client: TestClient):
    assert (
        'href="https://github.com/AlexTymosh/job-application-assistant"'
        in app_client.get("/").text
    )
    assert 'href="/cv-builder"' in app_client.get("/").text
    profile_id = _create_profile(app_client)
    resume_id = _create_resume(app_client, profile_id)

    for days in (10, 20, 30):
        page = app_client.get(f"/?days={days}")
        assert page.text.count('data-activity-bar="') == days
        assert f"last {days} days" in page.text
        assert "application" in page.text
    fallback = app_client.get("/?days=999")
    assert fallback.text.count('data-activity-bar="') == 30

    no_profile_client = app_client
    builder = no_profile_client.get(f"/cv-builder?resume_id={resume_id}")
    assert builder.status_code == 200
    assert "Backend CV" in builder.text
    assert "CV Builder" in builder.text


def test_cv_builder_empty_states(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("APP_DATA_DIR", str(tmp_path / "data"))
    app = create_app(openai_secret_service=MemorySecretService())
    with TestClient(app) as client:
        assert "No active profile" in client.get("/cv-builder").text
        profile_id = _create_profile(client)
        page = client.get("/cv-builder")
        assert "Create resume first" in page.text
        assert f"/profiles/{profile_id}/resumes/new" in page.text


def test_resume_builder_controls_and_type_specific_forms(
    app_client: TestClient, session
):
    profile_id = _create_profile(app_client)
    resume_id = _create_resume(app_client, profile_id)
    resume = session.get(Resume, resume_id)
    sections = {section.section_type: section for section in resume.sections}
    work = ResumeService(session).add_block(
        sections["work_experience"].id,
        block_type="work_experience",
        role_title="Engineer",
        organisation="Acme",
    )
    language = ResumeService(session).add_block(
        sections["languages"].id,
        block_type="custom",
        title="English",
        subtitle="C1",
    )

    builder = app_client.get(f"/resumes/{resume_id}").text
    assert 'data-section-type="summary"' in builder
    summary_block_id = sections["summary"].blocks[0].id
    summary_card = builder.split('data-block-title="Professional Summary"', 1)[1].split(
        "</article>", 1
    )[0]
    assert "Move block up" not in summary_card
    skills_card = builder.split('data-section-type="skills"', 1)[1].split(
        'data-section-type="work_experience"', 1
    )[0]
    assert "Move block up" not in skills_card
    work_card = builder.split('data-section-type="work_experience"', 1)[1]
    assert "Move block up" in work_card
    assert "Edit block" in builder
    assert '<span class="badge">summary</span>' not in builder

    work_form = app_client.get(f"/resumes/{resume_id}/blocks/{work.id}/edit").text
    assert "Subtitle / degree / level / reference role" not in work_form
    assert 'type="month" name="start_date"' in work_form
    assert 'type="month" name="end_date"' in work_form
    assert "Optional location" not in work_form

    summary_form = app_client.get(
        f"/resumes/{resume_id}/blocks/{summary_block_id}/edit"
    ).text
    assert "Description" in summary_form
    assert "Company / organisation" not in summary_form

    skills_form = app_client.get(
        f"/resumes/{resume_id}/blocks/{sections['skills'].blocks[0].id}/edit"
    ).text
    assert "Hard Skills" in skills_form
    assert "Start date" not in skills_form

    language_form = app_client.get(
        f"/resumes/{resume_id}/blocks/{language.id}/edit"
    ).text
    assert "Language" in language_form
    assert "Level" in language_form

    response = app_client.post(
        f"/resumes/{resume_id}/blocks/{work.id}/edit",
        data={
            "block_type": "work_experience",
            "role_title": "Senior Engineer",
            "organisation": "Acme",
            "start_date": "2024-01",
            "end_date": "2025-02",
            "is_visible": "on",
            "ai_edit_enabled": "on",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    session.refresh(work)
    assert work.role_title == "Senior Engineer"
    assert work.start_date == "2024-01"


def test_prompt_template_selection_uses_named_scopes(app_client: TestClient, session):
    profile_id = _create_profile(app_client)
    resume_id = _create_resume(app_client, profile_id)
    section = session.scalar(
        select(ResumeSection).where(ResumeSection.resume_id == resume_id)
    )
    page = app_client.get("/settings/prompts")
    assert "AI prompt instructions" in page.text
    assert "Protected safety rules" not in page.text
    assert "Protected AI instructions" not in page.text
    assert "Profile: Alex" in page.text
    assert "Resume: Backend CV" in page.text
    assert f"Section: Backend CV / {section.title}" in page.text
    response = app_client.post(
        "/settings/prompts-scoped",
        data={
            "scope": "section",
            "block_type": "summary",
            "section_id": str(section.id),
            "user_prompt_template": "Keep it concise.",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert (
        SettingsService(session).get_prompt_instruction(
            "summary", section_id=section.id
        )
        == "Keep it concise."
    )
