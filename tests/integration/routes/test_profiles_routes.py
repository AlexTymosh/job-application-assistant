from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.db.session import create_all_tables, create_sqlite_engine
from app.main import create_app
from app.secrets.openai_key import OpenAISecretService
from app.storage import app_dirs, location


class FakeKeyring:
    def get_password(self, service_name: str, username: str) -> str | None:
        return None

    def set_password(self, service_name: str, username: str, password: str) -> None:
        raise AssertionError("profiles tests must not write to keyring")

    def delete_password(self, service_name: str, username: str) -> None:
        raise AssertionError("profiles tests must not delete from keyring")


def _patch_user_locations(monkeypatch, tmp_path: Path) -> Path:  # type: ignore[no-untyped-def]
    documents_dir = tmp_path / "Documents"
    config_dir = tmp_path / "config"
    monkeypatch.setattr(
        app_dirs.platformdirs, "user_documents_dir", lambda: str(documents_dir)
    )
    monkeypatch.setattr(
        location.platformdirs,
        "user_config_dir",
        lambda appname: str(config_dir / appname),
    )
    monkeypatch.delenv("APP_DATA_DIR", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("PROFILE_NAME", raising=False)
    monkeypatch.delenv("PROFILE_DATA_DIR", raising=False)
    return documents_dir


def _client() -> TestClient:
    return TestClient(
        create_app(
            openai_secret_service=OpenAISecretService(keyring_backend=FakeKeyring())
        )
    )


def _write_profile(
    path: Path, *, name: str = "alex", with_database: bool = False
) -> None:
    (path / "cv" / "variants").mkdir(parents=True)
    (path / "config.yaml").write_text(
        f"""
app:
  profile_name: {name}
  data_dir: {path.as_posix()}
workflow: {{}}
llm:
  extraction_mode: fake
cv:
  default_variant: backend_developer
  variants:
    - backend_developer
exports: {{}}
guardrails: {{}}
job_reader: {{}}
future_integrations: {{}}
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (path / "cv" / "fact_bank.yaml").write_text(
        """
facts:
  - id: fact-1
    category: skill
    name: Backend services
    allowed_claim_level: practical
    evidence: Example evidence.
""".lstrip(),
        encoding="utf-8",
    )
    (path / "cv" / "variants" / "backend_developer.md").write_text(
        _valid_cv_content("Private CV"),
        encoding="utf-8",
    )
    if with_database:
        engine = create_sqlite_engine(path / "applications.sqlite3")
        create_all_tables(engine)
        engine.dispose()


def _valid_cv_content(marker: str) -> str:
    return (
        f"# {marker} — Backend Developer CV Variant\n\n"
        "<!-- SECTION: SUMMARY_START -->\n"
        "Backend-focused software developer with practical experience in Python.\n"
        "<!-- SECTION: SUMMARY_END -->\n\n"
        "<!-- SECTION: SKILLS_START -->\n"
        "- Python\n- FastAPI\n"
        "<!-- SECTION: SKILLS_END -->\n\n"
        "<!-- SECTION: EXPERIENCE_START -->\n"
        "## Example Company — Operations Analyst\n\n"
        "- Built small Python automation scripts.\n"
        "<!-- SECTION: EXPERIENCE_END -->\n\n"
        "<!-- SECTION: PROJECTS_START -->\n"
        "## Local FastAPI Portfolio Project\n\n"
        "- Built a local backend application using FastAPI.\n"
        "<!-- SECTION: PROJECTS_END -->\n"
    )


def test_profiles_page_available_when_setup_is_incomplete(
    monkeypatch, tmp_path: Path
) -> None:  # type: ignore[no-untyped-def]
    _patch_user_locations(monkeypatch, tmp_path)
    monkeypatch.setenv("PROFILE_NAME", "missing")
    monkeypatch.setenv("PROFILE_DATA_DIR", str(tmp_path / "missing-profile"))
    client = _client()

    response = client.get("/profiles")

    assert response.status_code == 200
    assert "Managed Profiles" in response.text
    assert "Setup is incomplete" in response.text


def test_profiles_can_connect_existing_file_based_profile(
    monkeypatch, tmp_path: Path
) -> None:  # type: ignore[no-untyped-def]
    _patch_user_locations(monkeypatch, tmp_path)
    profile_dir = tmp_path / "private" / "alex"
    _write_profile(profile_dir, with_database=True)
    client = _client()

    response = client.post(
        "/profiles",
        data={
            "name": "alex",
            "display_name": "Alex Profile",
            "data_dir": str(profile_dir),
            "make_active": "on",
        },
        follow_redirects=False,
    )
    page = client.get("/profiles")

    assert response.status_code == 303
    assert "alex" in page.text
    assert "Alex Profile" in page.text
    assert "Active" in page.text
    assert client.app.state.config.app.profile_name == "alex"


def test_profiles_can_make_profile_active_and_refresh_runtime_state(
    monkeypatch, tmp_path: Path
) -> None:  # type: ignore[no-untyped-def]
    _patch_user_locations(monkeypatch, tmp_path)
    alex_dir = tmp_path / "private" / "alex"
    sam_dir = tmp_path / "private" / "sam"
    _write_profile(alex_dir, name="alex", with_database=True)
    _write_profile(sam_dir, name="sam", with_database=True)
    client = _client()
    client.post(
        "/profiles",
        data={"name": "alex", "data_dir": str(alex_dir), "make_active": "on"},
    )
    client.post("/profiles", data={"name": "sam", "data_dir": str(sam_dir)})
    page = client.get("/profiles")
    marker = 'data-profile-name="sam"'
    sam_section = page.text[page.text.index(marker) :]
    action_start = sam_section.index("/profiles/")
    action_end = sam_section.index("/activate", action_start) + len("/activate")
    activate_url = sam_section[action_start:action_end]

    response = client.post(activate_url, follow_redirects=False)

    assert response.status_code == 303
    assert client.app.state.config.app.profile_name == "sam"


def test_profile_activation_repair_post_bypasses_setup_gate(
    monkeypatch, tmp_path: Path
) -> None:  # type: ignore[no-untyped-def]
    _patch_user_locations(monkeypatch, tmp_path)
    broken_dir = tmp_path / "private" / "broken"
    valid_dir = tmp_path / "private" / "valid"
    _write_profile(broken_dir, name="broken", with_database=True)
    _write_profile(valid_dir, name="valid", with_database=True)
    client = _client()
    client.post(
        "/profiles",
        data={"name": "broken", "data_dir": str(broken_dir), "make_active": "on"},
    )
    client.post("/profiles", data={"name": "valid", "data_dir": str(valid_dir)})
    (broken_dir / "config.yaml").unlink()

    dashboard_response = client.get("/dashboard", follow_redirects=False)
    profiles_page = client.get("/profiles")
    marker = 'data-profile-name="valid"'
    valid_section = profiles_page.text[profiles_page.text.index(marker) :]
    action_start = valid_section.index("/profiles/")
    action_end = valid_section.index("/activate", action_start) + len("/activate")
    activate_url = valid_section[action_start:action_end]

    response = client.post(activate_url, follow_redirects=False)

    assert dashboard_response.status_code == 303
    assert dashboard_response.headers["location"] == "/setup"
    assert profiles_page.status_code == 200
    assert "Setup is incomplete" in profiles_page.text
    assert response.status_code == 303
    assert response.headers["location"] == "/profiles"
    assert client.app.state.config.app.profile_name == "valid"
    setup_response = client.get("/setup")
    assert "Default CV variant is configured and readable" in setup_response.text


def test_setup_status_uses_active_managed_profile(monkeypatch, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    _patch_user_locations(monkeypatch, tmp_path)
    profile_dir = tmp_path / "private" / "alex"
    _write_profile(profile_dir, with_database=True)
    client = _client()

    client.post(
        "/profiles",
        data={"name": "alex", "data_dir": str(profile_dir), "make_active": "on"},
    )
    response = client.get("/setup")

    assert response.status_code == 200
    assert "Profile config" in response.text
    assert "Default CV variant is configured and readable" in response.text
