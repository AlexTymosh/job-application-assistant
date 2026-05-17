from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, select, text

from app.db.models import AppSetting, Resume, ResumeUpload
from app.db.session import initialise_database
from app.main import create_app


class MemorySecretService:
    def __init__(self) -> None:
        self.value: str | None = None

    def get_api_key(self) -> str | None:
        return self.value

    def set_api_key(self, value: str) -> None:
        self.value = value

    def delete_api_key(self) -> None:
        self.value = None


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


def test_schema_repair_adds_old_facts_columns_and_adapt_works(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    database_file = data_dir / "app.sqlite3"
    engine = create_engine(f"sqlite:///{database_file}", future=True)
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE facts ("
                "id INTEGER PRIMARY KEY, "
                "profile_id INTEGER, "
                "fact_key VARCHAR(120), "
                "category VARCHAR(120))"
            )
        )
    initialise_database(engine)
    assert "claim" in {
        column["name"] for column in inspect(engine).get_columns("facts")
    }

    monkeypatch.setenv("APP_DATA_DIR", str(data_dir))
    app = create_app(openai_secret_service=MemorySecretService())
    with TestClient(app) as client:
        profile_id = _create_profile(client)
        resume_id = _create_resume(client, profile_id)
        response = client.post(
            "/applications/adapt",
            data={
                "resume_id": str(resume_id),
                "raw_job_text": "Python FastAPI SQL testing role",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303


def test_settings_split_forms_preserve_exports_policy_and_models(
    app_client: TestClient, session
):
    app_client.post(
        "/settings",
        data={"settings_section": "exports", "export_pdf": "on", "export_docx": "on"},
    )
    app_client.post(
        "/settings",
        data={
            "settings_section": "ai-policy",
            "fact_links_required": "on",
            "allow_new_bullets": "on",
        },
    )
    assert (
        app_client.post(
            "/settings", data={"settings_section": "app", "locale": "ru"}
        ).status_code
        == 200
    )
    assert session.get(AppSetting, "exports").value_json == {
        "markdown": False,
        "html": False,
        "pdf": True,
        "docx": True,
    }
    assert (
        session.get(AppSetting, "ai_policy_defaults").value_json["fact_links_required"]
        is True
    )

    assert (
        app_client.post(
            "/settings",
            data={
                "settings_section": "openai",
                "openai_api_key": "sk-test",
                "openai_model_default": "custom-default",
                "openai_model_qa": "custom-qa",
                "openai_model_extract": "custom-extract",
                "openai_model_tailor": "custom-tailor",
            },
        ).status_code
        == 200
    )
    session.expire_all()
    assert (
        session.get(AppSetting, "openai_model_default").value_json == "custom-default"
    )
    assert session.get(AppSetting, "exports").value_json["pdf"] is True
    assert session.get(AppSetting, "openai_api_key") is None


def test_invalid_upload_does_not_persist_resume_or_file(
    app_client: TestClient, session, tmp_path: Path
):
    profile_id = _create_profile(app_client)
    before = len(list(session.scalars(select(Resume))))
    response = app_client.post(
        f"/profiles/{profile_id}/resumes/new",
        data={
            "name": "Bad",
            "target_role": "Engineer",
            "language": "en",
            "create_standard_sections": "on",
        },
        files={"resume_upload": ("bad.exe", b"no", "application/octet-stream")},
    )
    assert response.status_code == 400
    session.expire_all()
    assert len(list(session.scalars(select(Resume)))) == before
    assert not list(session.scalars(select(ResumeUpload)))
    assert "bad.exe" not in "\n".join(str(path) for path in tmp_path.rglob("*"))


def test_dashboard_ranges_header_and_cv_builder(app_client: TestClient):
    dashboard = app_client.get("/")
    assert 'href="/cv-builder"' in dashboard.text
    assert (
        'href="https://github.com/AlexTymosh/job-application-assistant"'
        in dashboard.text
    )
    assert ">Active profile<" not in dashboard.text
    assert 'aria-label="Active profile"' in dashboard.text

    assert app_client.get("/cv-builder").status_code == 200
    assert "No active profile" in app_client.get("/cv-builder").text
    profile_id = _create_profile(app_client)
    assert "Create resume first" in app_client.get("/cv-builder").text
    resume_id = _create_resume(app_client, profile_id)
    assert "Backend CV" in app_client.get(f"/cv-builder?resume_id={resume_id}").text
    for days in [10, 20, 30]:
        page = app_client.get(f"/?days={days}")
        assert f'data-chart-days="{days}"' in page.text
        assert page.text.count('data-chart-bar="1"') == days
        assert "X axis: date" in page.text
        assert "Y axis: application count" in page.text
        assert 'class="x-axis"' in page.text
        assert 'class="y-axis"' in page.text
        assert "title=" in page.text
    fallback = app_client.get("/?days=999")
    assert 'data-chart-days="30"' in fallback.text
    assert "application" in fallback.text


def test_block_forms_and_builder_controls_are_type_specific(
    app_client: TestClient, session
):
    profile_id = _create_profile(app_client)
    resume_id = _create_resume(app_client, profile_id)
    builder = app_client.get(f"/resumes/{resume_id}")
    assert (
        "Move block up"
        not in builder.text.split("Professional Summary", 1)[1].split("Skills", 1)[0]
    )
    assert "Edit block" in builder.text
    resume = session.get(Resume, resume_id)
    sections = {section.section_type: section for section in resume.sections}
    summary_block = sections["summary"].blocks[0]
    summary_form = app_client.get(
        f"/resumes/{resume_id}/blocks/{summary_block.id}/edit"
    )
    assert "Description" in summary_form.text
    assert "Start date" not in summary_form.text

    skills_block = sections["skills"].blocks[0]
    skills_form = app_client.get(f"/resumes/{resume_id}/blocks/{skills_block.id}/edit")
    assert "Skills" in skills_form.text
    assert "Company / organisation" not in skills_form.text

    work_section = sections["work_experience"]
    create = app_client.post(
        f"/resumes/{resume_id}/blocks/new",
        data={
            "section_id": str(work_section.id),
            "block_type": "work_experience",
            "role_title": "Engineer",
            "organisation": "Acme",
        },
        follow_redirects=False,
    )
    assert create.status_code == 303
    session.expire_all()
    work_block = session.get(Resume, resume_id).sections[2].blocks[0]
    work_form = app_client.get(f"/resumes/{resume_id}/blocks/{work_block.id}/edit")
    assert "Subtitle / degree / level / reference role" not in work_form.text
    assert 'type="month" name="start_date"' in work_form.text
    assert 'type="month" name="end_date"' in work_form.text


def test_prompt_page_uses_named_scope_selectors(app_client: TestClient):
    profile_id = _create_profile(app_client)
    resume_id = _create_resume(app_client, profile_id)
    page = app_client.get("/settings/prompts")
    assert "AI prompt instructions" in page.text
    assert "Protected AI instructions" not in page.text
    assert "Profile: Alex" in page.text
    assert "Resume: Backend CV" in page.text
    assert "Section: Backend CV / Summary" in page.text
    response = app_client.post(
        "/settings/prompts-scoped",
        data={
            "scope": "resume",
            "block_type": "summary",
            "resume_id": str(resume_id),
            "user_prompt_template": "Prefer concise summaries.",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "Prefer concise summaries." in app_client.get("/settings/prompts").text


def test_repaired_application_timestamps_and_dashboard_activity(tmp_path: Path):
    database_file = tmp_path / "legacy.sqlite3"
    engine = create_engine(f"sqlite:///{database_file}", future=True)
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE applications ("
                "id INTEGER PRIMARY KEY, "
                "profile_id INTEGER NOT NULL, "
                "resume_id INTEGER NOT NULL, "
                "application_number INTEGER NOT NULL UNIQUE, "
                "job_title VARCHAR(200) NOT NULL DEFAULT '', "
                "company_name VARCHAR(200) NOT NULL DEFAULT '', "
                "source_url VARCHAR(500) NOT NULL DEFAULT '', "
                "raw_job_text TEXT NOT NULL, "
                "status VARCHAR(60) NOT NULL DEFAULT 'job_saved')"
            )
        )
    initialise_database(engine)
    from datetime import UTC, datetime, timedelta

    from app.applications.service import ApplicationService
    from app.db.session import create_session_factory
    from app.people.service import PeopleService
    from app.resumes.service import ResumeService

    factory = create_session_factory(engine)
    with factory() as session:
        profile = PeopleService(session).create_profile("Alex", "Alex Example")
        resume = ResumeService(session).create_resume(profile.id, "Base", "Engineer")
        before = datetime.now(UTC).replace(tzinfo=None) - timedelta(seconds=5)
        application = ApplicationService(session).create_application(
            profile_id=profile.id,
            resume_id=resume.id,
            job_title="Engineer",
            company_name="Acme",
            source_url="",
            raw_job_text="Python SQL",
        )
        after = datetime.now(UTC).replace(tzinfo=None) + timedelta(seconds=5)
        assert before <= application.created_at <= after
        assert application.created_at.year != 1970
        stats = ApplicationService(session).dashboard_stats(profile.id, days=10)
        assert any(day["count"] == 1 for day in stats.activity_days)
        assert stats.recent_applications[0].id == application.id
        assert application.events[0].created_at.year != 1970


def test_settings_can_uncheck_all_split_form_flags(app_client: TestClient, session):
    from app.settings.service import SettingsService

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
    assert (
        app_client.post("/settings", data={"settings_section": "exports"}).status_code
        == 200
    )
    session.expire_all()
    assert session.get(AppSetting, "exports").value_json == {
        "markdown": False,
        "html": False,
        "pdf": False,
        "docx": False,
    }
    assert (
        app_client.post("/settings", data={"settings_section": "ai-policy"}).status_code
        == 200
    )
    session.expire_all()
    assert session.get(AppSetting, "ai_policy_defaults").value_json == {
        "fact_links_required": False,
        "allow_new_bullets": False,
        "allow_hide_bullets": False,
        "allow_title_edits": False,
    }


def test_openai_links_and_data_folder_settings(app_client: TestClient, tmp_path: Path):
    openai = app_client.get("/settings?section=openai")
    assert "OpenAI API keys" in openai.text
    assert "OpenAI Models documentation" in openai.text
    assert openai.text.count('target="_blank"') >= 2
    assert openai.text.count('rel="noopener noreferrer"') >= 2

    page = app_client.get("/settings?section=data-folder")
    assert "Current folder" in page.text
    assert 'name="root"' in page.text
    assert 'href="/data-folder"' not in page.text
    assert app_client.get("/data-folder", follow_redirects=False).status_code == 303
    new_root = tmp_path / "selected-data"
    response = app_client.post(
        "/settings",
        data={"settings_section": "data-folder", "root": str(new_root)},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert new_root.exists()
    invalid = app_client.post(
        "/settings",
        data={"settings_section": "data-folder", "root": ""},
        follow_redirects=False,
    )
    assert "data_folder_error" in invalid.headers["location"]


def test_application_profile_deletion_and_base_resume_exports(
    app_client: TestClient, session
):
    profile_id = _create_profile(app_client)
    resume_id = _create_resume(app_client, profile_id)
    response = app_client.post(
        "/applications/adapt",
        data={"resume_id": resume_id, "raw_job_text": "Python SQL"},
        follow_redirects=False,
    )
    application_id = int(response.headers["location"].rsplit("/", 1)[1])
    assert app_client.get("/").text.count('data-chart-bar="1"') == 30
    delete_response = app_client.post(
        f"/profiles/{profile_id}/applications/{application_id}/delete",
        data={"confirm_delete_application": "on"},
        follow_redirects=False,
    )
    assert delete_response.status_code == 303
    session.expire_all()
    from app.db.models import Application, PersonProfile

    assert session.get(Application, application_id) is None
    assert session.get(Resume, resume_id) is not None
    assert session.get(PersonProfile, profile_id) is not None

    pdf = app_client.post(
        f"/resumes/{resume_id}/exports", data={"format": "pdf"}, follow_redirects=False
    )
    assert pdf.status_code == 303
    assert pdf.headers["location"].endswith("/exports/pdf/download")
    assert app_client.get(pdf.headers["location"]).status_code == 200
    docx = app_client.post(
        f"/resumes/{resume_id}/exports", data={"format": "docx"}, follow_redirects=False
    )
    assert docx.status_code == 303
    assert app_client.get(docx.headers["location"]).status_code == 200
    assert app_client.get(f"/resumes/{resume_id}/exports/../download").status_code in {
        400,
        404,
    }

    delete_profile = app_client.post(
        f"/profiles/{profile_id}/delete",
        data={"confirm_profile_name": "Alex"},
        follow_redirects=False,
    )
    assert delete_profile.status_code == 303
    session.expire_all()
    assert session.get(PersonProfile, profile_id) is None


def test_delete_old_applications_scoped_and_prompt_templates_cleanup(
    app_client: TestClient, session
):
    from datetime import UTC, datetime, timedelta

    from app.applications.service import ApplicationService
    from app.db.models import Application, PersonProfile, PromptTemplate
    from app.settings.service import SettingsService

    first_profile_id = _create_profile(app_client, "Alex")
    first_resume_id = _create_resume(app_client, first_profile_id, "Alex CV")
    second_profile_id = _create_profile(app_client, "Blake")
    second_resume_id = _create_resume(app_client, second_profile_id, "Blake CV")
    service = ApplicationService(session)
    old_app = service.create_application(
        profile_id=first_profile_id,
        resume_id=first_resume_id,
        job_title="Old role",
        company_name="Acme",
        source_url="",
        raw_job_text="Python",
    )
    fresh_app = service.create_application(
        profile_id=first_profile_id,
        resume_id=first_resume_id,
        job_title="Fresh role",
        company_name="Acme",
        source_url="",
        raw_job_text="Python",
    )
    other_app = service.create_application(
        profile_id=second_profile_id,
        resume_id=second_resume_id,
        job_title="Other role",
        company_name="Acme",
        source_url="",
        raw_job_text="Python",
    )
    old_app.created_at = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=120)
    session.commit()

    deleted = service.delete_profile_applications(first_profile_id, older_than_days=90)
    assert deleted == 1
    assert session.get(Application, old_app.id) is None
    assert session.get(Application, fresh_app.id) is not None
    assert session.get(Application, other_app.id) is not None

    SettingsService(session).upsert_scoped_prompt_template(
        scope="profile",
        block_type="summary",
        profile_id=first_profile_id,
        user_prompt_template="Profile scoped text.",
    )
    assert list(
        session.scalars(
            select(PromptTemplate).where(PromptTemplate.profile_id == first_profile_id)
        )
    )
    delete_profile = app_client.post(
        f"/profiles/{first_profile_id}/delete",
        data={"confirm_profile_name": "Alex"},
        follow_redirects=False,
    )
    assert delete_profile.status_code == 303
    session.expire_all()
    assert session.get(PersonProfile, first_profile_id) is None
    assert session.get(PersonProfile, second_profile_id) is not None
    assert not list(
        session.scalars(
            select(PromptTemplate).where(PromptTemplate.profile_id == first_profile_id)
        )
    )
