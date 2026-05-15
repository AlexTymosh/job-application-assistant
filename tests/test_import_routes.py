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
        raise AssertionError("import route tests must not write to keyring")

    def delete_password(self, service_name: str, username: str) -> None:
        raise AssertionError("import route tests must not delete from keyring")


def _patch_user_locations(monkeypatch, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
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


def _client() -> TestClient:
    return TestClient(
        create_app(
            openai_secret_service=OpenAISecretService(keyring_backend=FakeKeyring())
        )
    )


def _write_profile(path: Path, *, name: str = "alex") -> None:
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
    evidence: Built Python and FastAPI services in verified work.
""".lstrip(),
        encoding="utf-8",
    )
    (path / "cv" / "variants" / "backend_developer.md").write_text(
        _valid_cv_content("Imported"),
        encoding="utf-8",
    )
    engine = create_sqlite_engine(path / "applications.sqlite3")
    create_all_tables(engine)
    engine.dispose()


def _valid_cv_content(marker: str) -> str:
    return (
        f"# {marker} Backend CV\n\n"
        "<!-- SECTION: SUMMARY_START -->\n"
        "Backend-focused software developer.\n"
        "<!-- SECTION: SUMMARY_END -->\n\n"
        "<!-- SECTION: SKILLS_START -->\n"
        "- Python\n- FastAPI\n"
        "<!-- SECTION: SKILLS_END -->\n\n"
        "<!-- SECTION: EXPERIENCE_START -->\n"
        "## Example Company\n\n"
        "- Built internal tooling.\n"
        "<!-- SECTION: EXPERIENCE_END -->\n\n"
        "<!-- SECTION: PROJECTS_START -->\n"
        "## Local Tooling\n\n"
        "- Built a FastAPI project.\n"
        "<!-- SECTION: PROJECTS_END -->\n"
    )


def _connect_active_profile(client: TestClient, profile_dir: Path) -> None:
    response = client.post(
        "/profiles",
        data={"name": "alex", "data_dir": str(profile_dir), "make_active": "on"},
    )
    assert response.status_code == 200


def test_import_page_renders_for_active_managed_profile(
    monkeypatch, tmp_path: Path
) -> None:  # type: ignore[no-untyped-def]
    _patch_user_locations(monkeypatch, tmp_path)
    profile_dir = tmp_path / "private" / "alex"
    _write_profile(profile_dir)
    client = _client()
    _connect_active_profile(client, profile_dir)

    response = client.get("/profiles/import")

    assert response.status_code == 200
    assert "Import CV and Fact Bank" in response.text
    assert "Preview import" in response.text


def test_preview_route_returns_planned_records_without_private_absolute_path(
    monkeypatch, tmp_path: Path
) -> None:  # type: ignore[no-untyped-def]
    _patch_user_locations(monkeypatch, tmp_path)
    profile_dir = tmp_path / "private" / "alex"
    _write_profile(profile_dir)
    client = _client()
    _connect_active_profile(client, profile_dir)

    response = client.post("/profiles/import/preview")

    assert response.status_code == 200
    assert "backend_developer" in response.text
    assert "fact-1" in response.text
    assert "Variants to create: 1" in response.text
    assert str(profile_dir) not in response.text
    assert "sk-" not in response.text.lower()


def test_apply_route_writes_records_after_explicit_post(
    monkeypatch, tmp_path: Path
) -> None:  # type: ignore[no-untyped-def]
    _patch_user_locations(monkeypatch, tmp_path)
    profile_dir = tmp_path / "private" / "alex"
    _write_profile(profile_dir)
    client = _client()
    _connect_active_profile(client, profile_dir)

    response = client.post("/profiles/import/apply")
    preview = client.post("/profiles/import/preview")

    assert response.status_code == 200
    assert "Import applied" in response.text
    assert "Created 1 variants, 4 sections, 4 blocks, and 1 facts" in response.text
    assert "Variants to skip: 1" in preview.text
    assert "Facts to skip: 1" in preview.text


def test_import_route_reports_missing_active_profile_clearly(
    monkeypatch, tmp_path: Path
) -> None:  # type: ignore[no-untyped-def]
    _patch_user_locations(monkeypatch, tmp_path)
    client = _client()

    response = client.post("/profiles/import/preview")

    assert response.status_code == 200
    assert "No active managed profile is configured" in response.text
