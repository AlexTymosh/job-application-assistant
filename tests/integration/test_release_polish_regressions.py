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
    assert dashboard.text.count("Active profile") == 1

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
