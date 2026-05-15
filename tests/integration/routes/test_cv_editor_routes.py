from __future__ import annotations

import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from app.cv.models import AllowedClaimLevel, FactCategory
from app.db.session import create_all_tables, create_sqlite_engine
from app.main import create_app
from app.managed_cv.repository import ManagedCvRepository
from app.profiles.repository import ManagedProfileRepository
from app.profiles.schema import ManagedProfileType
from app.secrets.openai_key import OpenAISecretService
from app.storage import app_dirs, location


class FakeKeyring:
    def get_password(self, service_name: str, username: str) -> str | None:
        return None

    def set_password(self, service_name: str, username: str, password: str) -> None:
        raise AssertionError("CV editor route tests must not write to keyring")

    def delete_password(self, service_name: str, username: str) -> None:
        raise AssertionError("CV editor route tests must not delete from keyring")


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
        (
            "# Backend CV\n\n"
            "<!-- SECTION: SUMMARY_START -->\n"
            "Original CV source.\n"
            "<!-- SECTION: SUMMARY_END -->\n"
        ),
        encoding="utf-8",
    )
    engine = create_sqlite_engine(path / "applications.sqlite3")
    create_all_tables(engine)
    engine.dispose()


def _connect_active_profile(client: TestClient, profile_dir: Path) -> None:
    response = client.post(
        "/profiles",
        data={"name": "alex", "data_dir": str(profile_dir), "make_active": "on"},
    )
    assert response.status_code == 200


def _create_active_profile_and_managed_cv(client: TestClient, profile_dir: Path):  # type: ignore[no-untyped-def]
    _connect_active_profile(client, profile_dir)
    session_factory = client.app.state.app_settings_service.session_factory
    cv_repository = ManagedCvRepository(session_factory)
    profile_repository = ManagedProfileRepository(session_factory)
    active_profile = profile_repository.get_active_profile()
    assert active_profile is not None
    variant = cv_repository.create_cv_variant(
        profile_id=active_profile.id,
        name="backend_developer",
        display_name="Backend Developer",
    )
    later = cv_repository.create_cv_section(
        variant_id=variant.id,
        section_key="projects",
        title="Projects",
        display_order=20,
    )
    earlier = cv_repository.create_cv_section(
        variant_id=variant.id, section_key="summary", title="Summary", display_order=10
    )
    block = cv_repository.create_cv_block(
        section_id=earlier.id,
        block_key="summary_imported_content",
        content_markdown="Original managed block",
        display_order=10,
    )
    cv_repository.create_cv_block(
        section_id=later.id,
        block_key="project_imported_content",
        content_markdown="Project managed block",
        display_order=10,
    )
    fact = cv_repository.create_fact(
        profile_id=active_profile.id,
        fact_key="fact-1",
        category=FactCategory.SKILL,
        name="Backend services",
        allowed_claim_level=AllowedClaimLevel.PRACTICAL,
        evidence="Built verified fake services.",
    )
    return cv_repository, profile_repository, active_profile, variant, block, fact


def test_editor_index_shows_no_active_profile_message(
    monkeypatch, tmp_path: Path
) -> None:  # type: ignore[no-untyped-def]
    _patch_user_locations(monkeypatch, tmp_path)
    client = _client()

    response = client.get("/profiles/cv")

    assert response.status_code == 200
    assert "No active managed profile" in response.text
    assert "/profiles" in response.text


def test_create_fact_requires_active_profile(monkeypatch, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    _patch_user_locations(monkeypatch, tmp_path)
    client = _client()

    response = client.post(
        "/profiles/facts",
        data={
            "fact_key": "new-fact",
            "category": "skill",
            "name": "New fact",
            "allowed_claim_level": "practical",
            "evidence": "Verified evidence.",
            "is_active": "on",
        },
    )

    assert response.status_code == 400
    assert "No active managed profile" in response.text
    assert "/profiles" in response.text
    assert "Fact key" not in response.text
    assert "Save fact" not in response.text


def test_new_fact_form_reports_missing_app_settings_storage(
    monkeypatch, tmp_path: Path
) -> None:  # type: ignore[no-untyped-def]
    _patch_user_locations(monkeypatch, tmp_path)
    client = _client()
    client.app.state.app_settings_service = None

    response = client.get("/profiles/facts/new")

    assert response.status_code == 400
    assert "App settings storage is not available" in response.text
    assert "Traceback" not in response.text


def test_new_fact_form_requires_active_profile(monkeypatch, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    _patch_user_locations(monkeypatch, tmp_path)
    client = _client()

    response = client.get("/profiles/facts/new")

    assert response.status_code == 400
    assert "No active managed profile" in response.text
    assert "/profiles" in response.text
    assert "Fact key" not in response.text
    assert "Save fact" not in response.text


def test_editor_index_shows_no_imported_cv_message_without_private_path(
    monkeypatch, tmp_path: Path
) -> None:  # type: ignore[no-untyped-def]
    _patch_user_locations(monkeypatch, tmp_path)
    profile_dir = tmp_path / "private" / "alex"
    _write_profile(profile_dir)
    client = _client()
    _connect_active_profile(client, profile_dir)

    response = client.get("/profiles/cv")

    assert response.status_code == 200
    assert "No managed CV variants have been imported yet" in response.text
    assert "/profiles/import" in response.text
    assert str(profile_dir) not in response.text


def test_variant_detail_lists_sections_and_blocks_in_order(
    monkeypatch, tmp_path: Path
) -> None:  # type: ignore[no-untyped-def]
    _patch_user_locations(monkeypatch, tmp_path)
    profile_dir = tmp_path / "private" / "alex"
    _write_profile(profile_dir)
    client = _client()
    _repo, _profiles, _active, variant, _block, _fact = (
        _create_active_profile_and_managed_cv(client, profile_dir)
    )

    response = client.get(f"/profiles/cv/variants/{variant.id}")

    assert response.status_code == 200
    assert response.text.index("Summary") < response.text.index("Projects")
    assert "summary_imported_content" in response.text
    assert "project_imported_content" in response.text


def test_block_edit_form_renders_current_markdown_and_facts(
    monkeypatch, tmp_path: Path
) -> None:  # type: ignore[no-untyped-def]
    _patch_user_locations(monkeypatch, tmp_path)
    profile_dir = tmp_path / "private" / "alex"
    _write_profile(profile_dir)
    client = _client()
    _repo, _profiles, _active, _variant, block, _fact = (
        _create_active_profile_and_managed_cv(client, profile_dir)
    )

    response = client.get(f"/profiles/cv/blocks/{block.id}/edit")

    assert response.status_code == 200
    assert "Original managed block" in response.text
    assert "fact-1" in response.text


def test_block_update_changes_fields_links_fact_and_preserves_source_files(
    monkeypatch, tmp_path: Path
) -> None:  # type: ignore[no-untyped-def]
    _patch_user_locations(monkeypatch, tmp_path)
    profile_dir = tmp_path / "private" / "alex"
    _write_profile(profile_dir)
    source_cv = profile_dir / "cv" / "variants" / "backend_developer.md"
    source_fact_bank = profile_dir / "cv" / "fact_bank.yaml"
    original_cv = source_cv.read_text(encoding="utf-8")
    original_fact_bank = source_fact_bank.read_text(encoding="utf-8")
    client = _client()
    cv_repository, _profiles, _active, _variant, block, fact = (
        _create_active_profile_and_managed_cv(client, profile_dir)
    )

    response = client.post(
        f"/profiles/cv/blocks/{block.id}",
        data={
            "content_markdown": "Updated managed markdown",
            "display_order": "3",
            "selected_fact_ids": fact.id,
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    updated = cv_repository.get_cv_block(block.id)
    assert updated is not None
    assert updated.content_markdown == "Updated managed markdown"
    assert updated.display_order == 3
    assert updated.is_enabled is False
    assert [link.fact_id for link in cv_repository.list_block_fact_links(block.id)] == [
        fact.id
    ]
    assert source_cv.read_text(encoding="utf-8") == original_cv
    assert source_fact_bank.read_text(encoding="utf-8") == original_fact_bank


def test_block_update_rejects_cross_profile_fact(monkeypatch, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    _patch_user_locations(monkeypatch, tmp_path)
    profile_dir = tmp_path / "private" / "alex"
    _write_profile(profile_dir)
    client = _client()
    cv_repository, profile_repository, _active, _variant, block, _fact = (
        _create_active_profile_and_managed_cv(client, profile_dir)
    )
    other = profile_repository.create_profile(
        profile_id="other-profile",
        name="other-profile",
        display_name=None,
        profile_type=ManagedProfileType.FILE_BASED,
        data_dir=tmp_path / "private" / "other",
        is_active=False,
    )
    other_fact = cv_repository.create_fact(
        profile_id=other.id,
        fact_key="other-fact",
        category=FactCategory.SKILL,
        name="Other fact",
        allowed_claim_level=AllowedClaimLevel.PRACTICAL,
        evidence="Verified other evidence.",
    )

    response = client.post(
        f"/profiles/cv/blocks/{block.id}",
        data={
            "content_markdown": "Updated managed markdown",
            "display_order": "3",
            "is_enabled": "on",
            "selected_fact_ids": other_fact.id,
        },
    )

    assert response.status_code == 400
    assert "Selected facts must belong to the active managed profile" in response.text


def test_block_update_rejects_blank_markdown(monkeypatch, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    _patch_user_locations(monkeypatch, tmp_path)
    profile_dir = tmp_path / "private" / "alex"
    _write_profile(profile_dir)
    client = _client()
    _repo, _profiles, _active, _variant, block, _fact = (
        _create_active_profile_and_managed_cv(client, profile_dir)
    )

    response = client.post(
        f"/profiles/cv/blocks/{block.id}",
        data={"content_markdown": "   ", "display_order": "0", "is_enabled": "on"},
    )

    assert response.status_code == 400
    assert "CV block markdown must not be empty" in response.text


def test_facts_list_renders_active_profile_facts_only(
    monkeypatch, tmp_path: Path
) -> None:  # type: ignore[no-untyped-def]
    _patch_user_locations(monkeypatch, tmp_path)
    profile_dir = tmp_path / "private" / "alex"
    _write_profile(profile_dir)
    client = _client()
    cv_repository, profile_repository, _active, _variant, _block, _fact = (
        _create_active_profile_and_managed_cv(client, profile_dir)
    )
    other = profile_repository.create_profile(
        profile_id="other-profile",
        name="other-profile",
        display_name=None,
        profile_type=ManagedProfileType.FILE_BASED,
        data_dir=tmp_path / "private" / "other",
        is_active=False,
    )
    cv_repository.create_fact(
        profile_id=other.id,
        fact_key="hidden-fact",
        category=FactCategory.SKILL,
        name="Hidden fact",
        allowed_claim_level=AllowedClaimLevel.PRACTICAL,
        evidence="Verified hidden evidence.",
    )

    response = client.get("/profiles/facts")

    assert response.status_code == 200
    assert "fact-1" in response.text
    assert "hidden-fact" not in response.text
    assert str(profile_dir) not in response.text


def test_create_fact_validates_enum_and_rejects_duplicate(
    monkeypatch, tmp_path: Path
) -> None:  # type: ignore[no-untyped-def]
    _patch_user_locations(monkeypatch, tmp_path)
    profile_dir = tmp_path / "private" / "alex"
    _write_profile(profile_dir)
    client = _client()
    _repo, _profiles, _active, _variant, _block, _fact = (
        _create_active_profile_and_managed_cv(client, profile_dir)
    )

    invalid = client.post(
        "/profiles/facts",
        data={
            "fact_key": "new-fact",
            "category": "invalid",
            "name": "New fact",
            "allowed_claim_level": "practical",
            "evidence": "Verified evidence.",
            "is_active": "on",
        },
    )
    duplicate = client.post(
        "/profiles/facts",
        data={
            "fact_key": "fact-1",
            "category": "skill",
            "name": "Duplicate fact",
            "allowed_claim_level": "practical",
            "evidence": "Verified evidence.",
            "is_active": "on",
        },
    )

    assert invalid.status_code == 400
    assert "invalid" in invalid.text
    assert duplicate.status_code == 400
    assert "already exists" in duplicate.text


def test_edit_fact_updates_fields_and_rejects_blank_values(
    monkeypatch, tmp_path: Path
) -> None:  # type: ignore[no-untyped-def]
    _patch_user_locations(monkeypatch, tmp_path)
    profile_dir = tmp_path / "private" / "alex"
    _write_profile(profile_dir)
    client = _client()
    cv_repository, _profiles, _active, _variant, _block, fact = (
        _create_active_profile_and_managed_cv(client, profile_dir)
    )

    ok = client.post(
        f"/profiles/facts/{fact.id}",
        data={
            "category": "project",
            "name": "API platform",
            "allowed_claim_level": "strong",
            "evidence": "Verified project evidence.",
        },
        follow_redirects=False,
    )
    blank = client.post(
        f"/profiles/facts/{fact.id}",
        data={
            "category": "project",
            "name": "   ",
            "allowed_claim_level": "strong",
            "evidence": "Verified project evidence.",
            "is_active": "on",
        },
    )

    updated = cv_repository.get_fact(fact.id)
    assert ok.status_code == 303
    assert updated is not None
    assert updated.name == "API platform"
    assert updated.category == FactCategory.PROJECT
    assert updated.allowed_claim_level == AllowedClaimLevel.STRONG
    assert updated.is_active is False
    assert blank.status_code == 400
    assert "empty" in blank.text


def test_routes_do_not_write_managed_cv_data_to_profile_applications_database(
    monkeypatch, tmp_path: Path
) -> None:  # type: ignore[no-untyped-def]
    _patch_user_locations(monkeypatch, tmp_path)
    profile_dir = tmp_path / "private" / "alex"
    _write_profile(profile_dir)
    client = _client()
    _repo, _profiles, _active, _variant, _block, _fact = (
        _create_active_profile_and_managed_cv(client, profile_dir)
    )

    with sqlite3.connect(profile_dir / "applications.sqlite3") as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }

    assert "cv_variants" not in tables
    assert "facts" not in tables
