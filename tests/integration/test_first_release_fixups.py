from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text

from app.applications.service import ApplicationService
from app.db.models import (
    Application,
    ApplicationEvent,
    AppSetting,
    Fact,
    PersonProfile,
    PromptTemplate,
    Resume,
)
from app.db.session import create_session_factory, initialise_database
from app.people.service import PeopleService
from app.resumes.service import ResumeService
from app.settings.service import SettingsService


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


def _adapt(client: TestClient, resume_id: int) -> int:
    response = client.post(
        "/applications/adapt",
        data={"resume_id": str(resume_id), "raw_job_text": "Python FastAPI SQL"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    return int(response.headers["location"].rstrip("/").split("/")[-1])


def test_repaired_application_timestamps_feed_dashboard(tmp_path: Path):
    database_file = tmp_path / "old.sqlite3"
    engine = create_engine(f"sqlite:///{database_file}", future=True)
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE applications ("
                "id INTEGER PRIMARY KEY, "
                "profile_id INTEGER NOT NULL, "
                "resume_id INTEGER NOT NULL, "
                "application_number INTEGER NOT NULL UNIQUE, "
                "raw_job_text TEXT NOT NULL)"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE application_events ("
                "id INTEGER PRIMARY KEY, "
                "application_id INTEGER NOT NULL, "
                "event_type VARCHAR(80) NOT NULL)"
            )
        )
    before = datetime.now(UTC).replace(tzinfo=None) - timedelta(seconds=3)
    initialise_database(engine)
    factory = create_session_factory(engine)
    with factory() as session:
        profile = PeopleService(session).create_profile("Alex", "Alex Example")
        resume = ResumeService(session).create_resume(profile.id, "Backend", "Backend")
        app = ApplicationService(session).create_application(
            profile_id=profile.id,
            resume_id=resume.id,
            job_title="Engineer",
            company_name="Acme",
            source_url="",
            raw_job_text="Python SQL",
        )
        session.refresh(app)
        after = datetime.now(UTC).replace(tzinfo=None) + timedelta(seconds=3)
        assert before <= app.created_at <= after
        assert app.created_at.year != 1970
        event = session.scalar(
            select(ApplicationEvent).where(ApplicationEvent.application_id == app.id)
        )
        assert event is not None
        assert before <= event.created_at <= after
        stats = ApplicationService(session).dashboard_stats(profile.id, days=10)
        assert any(day["count"] == 1 for day in stats.activity_days)
        assert stats.recent_applications[0].id == app.id


def test_settings_split_forms_can_uncheck_all_and_preserve_unrelated(
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
    app_client.post("/settings", data={"settings_section": "exports"})
    session.expire_all()
    assert session.get(AppSetting, "exports").value_json == {
        "markdown": False,
        "html": False,
        "pdf": False,
        "docx": False,
    }
    app_client.post("/settings", data={"settings_section": "ai-policy"})
    session.expire_all()
    assert session.get(AppSetting, "ai_policy_defaults").value_json == {
        "fact_links_required": False,
        "allow_new_bullets": False,
        "allow_hide_bullets": False,
        "allow_title_edits": False,
    }
    app_client.post("/settings", data={"settings_section": "app", "locale": "en"})
    app_client.post(
        "/settings",
        data={"settings_section": "openai", "openai_model_default": "model-a"},
    )
    session.expire_all()
    assert session.get(AppSetting, "exports").value_json["pdf"] is False
    assert (
        session.get(AppSetting, "ai_policy_defaults").value_json["allow_new_bullets"]
        is False
    )


def test_dashboard_axes_header_links_and_data_folder(
    app_client: TestClient, tmp_path: Path
):
    page = app_client.get("/")
    assert "Active profile" not in page.text.replace('aria-label="Active profile"', "")
    assert 'aria-label="Active profile"' in page.text
    settings = app_client.get("/settings?section=openai")
    assert "OpenAI API keys" in settings.text
    assert 'target="_blank"' in settings.text
    assert 'rel="noopener noreferrer"' in settings.text
    profile_id = _create_profile(app_client)
    _create_resume(app_client, profile_id)
    page = app_client.get("/")
    assert 'name="active_profile_id"' in page.text
    for days in [10, 20, 30]:
        dashboard = app_client.get(f"/?days={days}")
        assert f'data-chart-days="{days}"' in dashboard.text
        assert dashboard.text.count('data-chart-bar="1"') == days
        assert 'aria-label="X axis dates"' in dashboard.text
        assert 'aria-label="Y axis application count"' in dashboard.text
        assert "Likely applied" not in dashboard.text
        assert "Manually marked applied" not in dashboard.text
    assert 'data-chart-days="30"' in app_client.get("/?days=999").text
    data_folder = app_client.get("/settings?section=data-folder")
    assert "App data folder path" in data_folder.text
    custom_root = tmp_path / "custom-data"
    response = app_client.post(
        "/settings",
        data={"settings_section": "data-folder", "root": str(custom_root)},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert custom_root.exists()
    assert (
        app_client.post(
            "/settings",
            data={"settings_section": "data-folder", "root": ""},
            follow_redirects=False,
        ).status_code
        == 303
    )
    redirect = app_client.get("/data-folder", follow_redirects=False)
    assert redirect.status_code == 303
    assert redirect.headers["location"] == "/settings?section=data-folder"


def test_application_and_profile_deletion_and_base_exports(
    app_client: TestClient, session
):
    profile_id = _create_profile(app_client)
    resume_id = _create_resume(app_client, profile_id)
    other_profile_id = _create_profile(app_client, "Bea")
    other_resume_id = _create_resume(app_client, other_profile_id, "Other CV")
    app_id = _adapt(app_client, resume_id)
    SettingsService(session).set_active_profile(other_profile_id)
    other_app_id = _adapt(app_client, other_resume_id)
    SettingsService(session).set_active_profile(profile_id)
    session.expire_all()
    SettingsService(session).set_active_profile(profile_id)
    delete_wrong = app_client.post(
        f"/applications/{other_app_id}/delete",
        data={"confirm_delete_application": "on"},
    )
    assert delete_wrong.status_code == 404
    delete_one = app_client.post(
        f"/applications/{app_id}/delete",
        data={"confirm_delete_application": "on"},
        follow_redirects=False,
    )
    assert delete_one.status_code == 303
    session.expire_all()
    assert session.get(Application, app_id) is None
    assert session.get(Resume, resume_id) is not None
    assert session.get(PersonProfile, profile_id) is not None
    assert (
        ApplicationService(session).dashboard_stats(profile_id).application_count == 0
    )

    old_app = ApplicationService(session).create_application(
        profile_id=profile_id,
        resume_id=resume_id,
        job_title="Old",
        company_name="Acme",
        source_url="",
        raw_job_text="Python",
    )
    old_app.created_at = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=60)
    session.commit()
    deleted = ApplicationService(session).delete_profile_applications(
        profile_id,
        older_than_days=30,
        app_data_root=app_client.app.state.app_data_paths.root,
    )
    assert deleted == 1
    assert session.get(Application, old_app.id) is None

    pdf = app_client.post(
        f"/resumes/{resume_id}/exports", data={"format": "pdf"}, follow_redirects=False
    )
    assert pdf.status_code == 303
    pdf_download = app_client.get(pdf.headers["location"])
    assert pdf_download.status_code == 200
    docx = app_client.post(
        f"/resumes/{resume_id}/exports", data={"format": "docx"}, follow_redirects=False
    )
    assert docx.status_code == 303
    assert app_client.get(docx.headers["location"]).status_code == 200
    assert "Download PDF" in app_client.get(f"/resumes/{resume_id}").text
    assert "Download DOCX" in app_client.get(f"/cv-builder?resume_id={resume_id}").text
    assert (
        app_client.post(
            f"/resumes/{resume_id}/exports", data={"format": "../pdf"}
        ).status_code
        == 400
    )

    PeopleService(session).create_fact(
        profile_id,
        fact_key="python",
        category="skill",
        claim="Built Python services.",
        evidence="Notes",
        source="self",
        allowed_claim_level="practical",
    )
    SettingsService(session).upsert_scoped_prompt_template(
        scope="profile",
        block_type="summary",
        user_prompt_template="Profile prompt",
        profile_id=profile_id,
    )
    response = app_client.post(
        f"/profiles/{profile_id}/delete",
        data={"confirm_profile_name": "Alex"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    session.expire_all()
    assert session.get(PersonProfile, profile_id) is None
    assert session.get(Resume, resume_id) is None
    assert not list(session.scalars(select(Fact).where(Fact.profile_id == profile_id)))
    assert not list(
        session.scalars(
            select(PromptTemplate).where(PromptTemplate.profile_id == profile_id)
        )
    )
    assert SettingsService(session).get_active_profile_id() is None
    assert session.get(PersonProfile, other_profile_id) is not None
    assert session.get(Application, other_app_id) is not None
