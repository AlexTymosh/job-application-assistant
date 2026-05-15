from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.artifacts.resolution import resolve_artifact_path_under_applications_dir
from app.db.repositories import ApplicationRepository
from app.db.session import create_all_tables, create_sqlite_engine
from app.main import create_app
from app.managed_cv.repository import ManagedCvRepository
from app.profiles.repository import ManagedProfileRepository
from app.secrets.openai_key import OpenAISecretService
from app.storage import app_dirs, location


class FakeKeyring:
    def get_password(self, service_name: str, username: str) -> str | None:
        return None

    def set_password(self, service_name: str, username: str, password: str) -> None:
        raise AssertionError("release smoke tests must not write to keyring")

    def delete_password(self, service_name: str, username: str) -> None:
        raise AssertionError("release smoke tests must not delete from keyring")


def _patch_user_locations(monkeypatch, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    documents_dir = tmp_path / "Documents"
    config_dir = tmp_path / "config"

    monkeypatch.setattr(
        app_dirs.platformdirs,
        "user_documents_dir",
        lambda: str(documents_dir),
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
workflow:
  require_human_approval_before_export: true
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
        _valid_cv_content(),
        encoding="utf-8",
    )

    engine = create_sqlite_engine(path / "applications.sqlite3")
    create_all_tables(engine)
    engine.dispose()


def _valid_cv_content() -> str:
    return (
        "# Backend Developer CV\n\n"
        "<!-- SECTION: SUMMARY_START -->\n"
        "Backend-focused software developer.\n"
        "<!-- SECTION: SUMMARY_END -->\n\n"
        "<!-- SECTION: SKILLS_START -->\n"
        "- Python\n"
        "- FastAPI\n"
        "<!-- SECTION: SKILLS_END -->\n\n"
        "<!-- SECTION: EXPERIENCE_START -->\n"
        "## Example Company\n\n"
        "- Built internal tooling.\n"
        "<!-- SECTION: EXPERIENCE_END -->\n\n"
        "<!-- SECTION: PROJECTS_START -->\n"
        "## Original File-Based Project\n\n"
        "- Built a FastAPI project.\n"
        "<!-- SECTION: PROJECTS_END -->\n"
    )


def _connect_active_profile(client: TestClient, profile_dir: Path) -> None:
    response = client.post(
        "/profiles",
        data={
            "name": "alex",
            "display_name": "Alex Smoke Profile",
            "data_dir": str(profile_dir),
            "make_active": "on",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/profiles"
    assert client.app.state.config.app.profile_name == "alex"


def _create_application(client: TestClient) -> None:
    response = client.post(
        "/applications",
        data={
            "manual_text": (
                "We need a backend developer to build reliable FastAPI services, "
                "write tests, work with SQL databases, document decisions, and "
                "collaborate with product stakeholders. The role values Python, "
                "FastAPI, maintainable services, and careful delivery. " * 2
            ),
            "source_url": "https://example.invalid/jobs/backend-developer",
            "selected_cv_variant": "backend_developer",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/applications/1"


def _edit_imported_projects_block(client: TestClient) -> str:
    session_factory = client.app.state.app_settings_service.session_factory
    profile_repository = ManagedProfileRepository(session_factory)
    cv_repository = ManagedCvRepository(session_factory)

    active_profile = profile_repository.get_active_profile()
    assert active_profile is not None

    variants = cv_repository.list_cv_variants(active_profile.id)
    variant = next(
        variant for variant in variants if variant.name == "backend_developer"
    )

    sections = cv_repository.list_cv_sections(variant.id)
    projects_section = next(
        section for section in sections if section.section_key == "projects"
    )

    blocks = cv_repository.list_cv_blocks(projects_section.id)
    block = blocks[0]

    facts = cv_repository.list_facts(active_profile.id)
    fact = next(fact for fact in facts if fact.fact_key == "fact-1")

    edited_markdown = (
        "## Smoke Managed Project\n\n"
        "- This marker proves the release smoke path used managed CV storage."
    )

    response = client.post(
        f"/profiles/cv/blocks/{block.id}",
        data={
            "content_markdown": edited_markdown,
            "display_order": "10",
            "is_enabled": "on",
            "selected_fact_ids": fact.id,
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert (
        response.headers["location"] == f"/profiles/cv/blocks/{block.id}/edit?success=1"
    )

    return "Smoke Managed Project"


def test_release_smoke_managed_profile_import_editor_and_pipeline_path(
    monkeypatch,
    tmp_path: Path,
) -> None:  # type: ignore[no-untyped-def]
    _patch_user_locations(monkeypatch, tmp_path)
    profile_dir = tmp_path / "private" / "alex"
    _write_profile(profile_dir)

    client = _client()

    setup_response = client.get("/setup")
    assert setup_response.status_code == 200

    profiles_response = client.get("/profiles")
    assert profiles_response.status_code == 200
    assert "Managed Profiles" in profiles_response.text

    _connect_active_profile(client, profile_dir)

    import_page = client.get("/profiles/import")
    assert import_page.status_code == 200
    assert "Import CV and Fact Bank" in import_page.text

    preview_response = client.post("/profiles/import/preview")
    assert preview_response.status_code == 200
    assert "Variants to create: 1" in preview_response.text
    assert "fact-1" in preview_response.text
    assert str(profile_dir) not in preview_response.text

    apply_response = client.post("/profiles/import/apply")
    assert apply_response.status_code == 200
    assert "Import applied" in apply_response.text

    cv_index = client.get("/profiles/cv")
    assert cv_index.status_code == 200
    assert "Managed CV variants" in cv_index.text
    assert "Backend Developer" in cv_index.text
    assert "/profiles/cv/variants/" in cv_index.text
    assert str(profile_dir) not in cv_index.text

    facts_page = client.get("/profiles/facts")
    assert facts_page.status_code == 200
    assert "fact-1" in facts_page.text
    assert str(profile_dir) not in facts_page.text

    managed_marker = _edit_imported_projects_block(client)

    _create_application(client)

    pipeline_response = client.post(
        "/applications/1/run-local-pipeline",
        follow_redirects=False,
    )
    assert pipeline_response.status_code == 303
    assert pipeline_response.headers["location"] == "/applications/1/review"

    review_response = client.get("/applications/1/review")
    assert review_response.status_code == 200
    assert "pipeline_cv_source_loaded" in review_response.text
    assert str(profile_dir) not in review_response.text

    with client.app.state.session_factory() as session:
        application = ApplicationRepository(session).get_by_number_with_related(
            profile_name="alex",
            application_number=1,
        )
        assert application is not None

        source_event = next(
            event
            for event in application.events
            if event.event_type == "pipeline_cv_source_loaded"
        )
        assert "Managed CV/fact storage" in source_event.message

        markdown_artifact = next(
            artifact
            for artifact in application.artifacts
            if artifact.artifact_type == "tailored_cv_markdown"
        )

    tailored_path = resolve_artifact_path_under_applications_dir(
        applications_dir=client.app.state.profile_paths.applications_dir,
        stored_relative_path=markdown_artifact.path,
    )
    tailored_markdown = tailored_path.read_text(encoding="utf-8")

    assert managed_marker in tailored_markdown
    assert str(profile_dir) not in review_response.text
    assert "sk-" not in review_response.text.lower()
