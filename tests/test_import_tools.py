from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from app.cv.models import AllowedClaimLevel, FactCategory
from app.db.session import create_all_tables, create_sqlite_engine
from app.import_tools.service import (
    ImportApplyBlockedError,
    ImportToolsError,
    ManagedCvImportService,
)
from app.managed_cv.repository import ManagedCvRepository
from app.profiles.repository import ManagedProfileRepository
from app.profiles.schema import ManagedProfileType
from app.settings.migrations import migrate_app_settings_database
from app.settings.session import create_settings_engine, create_settings_session_factory


def _session_factory(tmp_path: Path):  # type: ignore[no-untyped-def]
    database_file = tmp_path / "app_data" / "app.sqlite3"
    migrate_app_settings_database(database_file)
    engine = create_settings_engine(database_file)
    return create_settings_session_factory(engine), database_file


def _write_profile(
    path: Path,
    *,
    name: str = "alex",
    cv_content: str | None = None,
    fact_bank_content: str | None = None,
) -> Path:
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
        fact_bank_content
        or """
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
        cv_content or _valid_cv_content("Imported"),
        encoding="utf-8",
    )
    engine = create_sqlite_engine(path / "applications.sqlite3")
    create_all_tables(engine)
    engine.dispose()
    return path


def _create_active_profile(
    repository: ManagedProfileRepository,
    profile_dir: Path,
    *,
    profile_id: str = "profile-1",
) -> None:
    repository.create_profile(
        profile_id=profile_id,
        name="alex",
        display_name="Alex",
        profile_type=ManagedProfileType.FILE_BASED,
        data_dir=profile_dir,
        is_active=True,
    )


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


def _table_count(database_file: Path, table_name: str) -> int:
    with sqlite3.connect(database_file) as connection:
        return int(
            connection.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        )


def _table_names(database_file: Path) -> set[str]:
    with sqlite3.connect(database_file) as connection:
        rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    return {str(row[0]) for row in rows}


def test_preview_does_not_write_records(tmp_path: Path) -> None:
    session_factory, database_file = _session_factory(tmp_path)
    profile_dir = _write_profile(tmp_path / "private" / "alex")
    _create_active_profile(ManagedProfileRepository(session_factory), profile_dir)

    preview = ManagedCvImportService(session_factory).preview_import()

    assert preview.apply_allowed is True
    assert preview.totals.variants_create == 1
    assert _table_count(database_file, "cv_variants") == 0
    assert _table_count(database_file, "facts") == 0


def test_apply_imports_markdown_cv_and_yaml_facts(tmp_path: Path) -> None:
    session_factory, database_file = _session_factory(tmp_path)
    profile_dir = _write_profile(tmp_path / "private" / "alex")
    _create_active_profile(ManagedProfileRepository(session_factory), profile_dir)

    result = ManagedCvImportService(session_factory).apply_import()

    repository = ManagedCvRepository(session_factory)
    variants = repository.list_cv_variants("profile-1")
    facts = repository.list_facts("profile-1")
    sections = repository.list_cv_sections(variants[0].id)
    blocks = repository.list_cv_blocks(sections[0].id)
    assert result.created_variants == 1
    assert result.created_sections == 4
    assert result.created_blocks == 4
    assert result.created_facts == 1
    assert variants[0].name == "backend_developer"
    assert [section.section_key for section in sections] == [
        "summary",
        "skills",
        "experience",
        "projects",
    ]
    assert blocks[0].block_key == "imported_content"
    assert facts[0].fact_key == "fact-1"
    assert _table_count(database_file, "cv_block_fact_links") == 0


def test_repeated_apply_is_idempotent_and_skips_existing_records(
    tmp_path: Path,
) -> None:
    session_factory, _database_file = _session_factory(tmp_path)
    profile_dir = _write_profile(tmp_path / "private" / "alex")
    _create_active_profile(ManagedProfileRepository(session_factory), profile_dir)
    service = ManagedCvImportService(session_factory)

    first = service.apply_import()
    second = service.apply_import()
    preview = service.preview_import()

    assert first.created_variants == 1
    assert second.created_variants == 0
    assert second.created_sections == 0
    assert second.created_blocks == 0
    assert second.created_facts == 0
    assert preview.totals.variants_skip == 1
    assert preview.totals.sections_skip == 4
    assert preview.totals.blocks_skip == 4
    assert preview.totals.facts_skip == 1


def test_existing_conflicting_record_is_reported_and_blocks_apply(
    tmp_path: Path,
) -> None:
    session_factory, _database_file = _session_factory(tmp_path)
    profile_dir = _write_profile(tmp_path / "private" / "alex")
    _create_active_profile(ManagedProfileRepository(session_factory), profile_dir)
    repository = ManagedCvRepository(session_factory)
    repository.create_fact(
        profile_id="profile-1",
        fact_key="fact-1",
        category=FactCategory.SKILL,
        name="Different fact",
        allowed_claim_level=AllowedClaimLevel.PRACTICAL,
        evidence="Different evidence.",
    )
    service = ManagedCvImportService(session_factory)

    preview = service.preview_import()

    assert preview.apply_allowed is False
    assert any("Fact fact-1" in conflict for conflict in preview.conflicts)
    with pytest.raises(ImportApplyBlockedError):
        service.apply_import()


def test_invalid_markdown_markers_raise_clear_error_without_partial_writes(
    tmp_path: Path,
) -> None:
    session_factory, database_file = _session_factory(tmp_path)
    profile_dir = _write_profile(
        tmp_path / "private" / "alex",
        cv_content="<!-- SECTION: SUMMARY_START -->\nMissing required markers.\n",
    )
    _create_active_profile(ManagedProfileRepository(session_factory), profile_dir)

    with pytest.raises(ImportToolsError, match="Missing end marker"):
        ManagedCvImportService(session_factory).apply_import()

    assert _table_count(database_file, "cv_variants") == 0
    assert _table_count(database_file, "facts") == 0


def test_invalid_fact_bank_raises_clear_error_without_partial_writes(
    tmp_path: Path,
) -> None:
    session_factory, database_file = _session_factory(tmp_path)
    profile_dir = _write_profile(
        tmp_path / "private" / "alex",
        fact_bank_content="facts: invalid\n",
    )
    _create_active_profile(ManagedProfileRepository(session_factory), profile_dir)

    with pytest.raises(ImportToolsError, match="Fact bank facts value must be a list"):
        ManagedCvImportService(session_factory).apply_import()

    assert _table_count(database_file, "cv_variants") == 0
    assert _table_count(database_file, "facts") == 0


def test_malformed_fact_bank_yaml_raises_clear_error_without_partial_writes(
    tmp_path: Path,
) -> None:
    session_factory, database_file = _session_factory(tmp_path)
    profile_dir = _write_profile(
        tmp_path / "private" / "alex",
        fact_bank_content="facts:\n  - id: [unterminated\n",
    )
    _create_active_profile(ManagedProfileRepository(session_factory), profile_dir)

    with pytest.raises(ImportToolsError, match="Import source could not be loaded"):
        ManagedCvImportService(session_factory).apply_import()

    assert _table_count(database_file, "cv_variants") == 0
    assert _table_count(database_file, "cv_sections") == 0
    assert _table_count(database_file, "cv_blocks") == 0
    assert _table_count(database_file, "facts") == 0


def test_apply_does_not_mutate_source_files_or_profile_application_database(
    tmp_path: Path,
) -> None:
    session_factory, app_database_file = _session_factory(tmp_path)
    profile_dir = _write_profile(tmp_path / "private" / "alex")
    _create_active_profile(ManagedProfileRepository(session_factory), profile_dir)
    cv_file = profile_dir / "cv" / "variants" / "backend_developer.md"
    fact_file = profile_dir / "cv" / "fact_bank.yaml"
    application_database = profile_dir / "applications.sqlite3"
    before_cv = cv_file.read_bytes()
    before_fact = fact_file.read_bytes()
    before_application_tables = _table_names(application_database)

    ManagedCvImportService(session_factory).apply_import()

    assert cv_file.read_bytes() == before_cv
    assert fact_file.read_bytes() == before_fact
    assert _table_names(application_database) == before_application_tables
    assert "cv_variants" not in _table_names(application_database)
    assert _table_count(app_database_file, "cv_variants") == 1
