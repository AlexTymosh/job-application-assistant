from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import delete

from app.cv.models import AllowedClaimLevel, FactCategory
from app.db.base import Base
from app.db.session import create_all_tables, create_sqlite_engine
from app.managed_cv import models as managed_cv_models
from app.managed_cv.repository import (
    CrossProfileFactLinkError,
    DuplicateBlockFactLinkError,
    DuplicateCvVariantAliasError,
    DuplicateCvVariantNameError,
    DuplicateManagedFactKeyError,
    ManagedCvRepository,
)
from app.profiles.models import ManagedProfile
from app.profiles.repository import ManagedProfileRepository
from app.profiles.schema import ManagedProfileType
from app.settings.base import SettingsBase
from app.settings.migrations import (
    CURRENT_APP_SETTINGS_SCHEMA_VERSION,
    is_app_settings_schema_current,
    migrate_app_settings_database,
)
from app.settings.session import create_settings_engine, create_settings_session_factory

MANAGED_CV_TABLES = {
    "cv_variants",
    "cv_variant_aliases",
    "cv_sections",
    "cv_blocks",
    "facts",
    "cv_block_fact_links",
}


def table_names(database_file: Path) -> set[str]:
    with sqlite3.connect(database_file) as connection:
        rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    return {str(row[0]) for row in rows}


@pytest.fixture
def repository(tmp_path: Path) -> tuple[ManagedCvRepository, ManagedProfileRepository]:
    database_file = tmp_path / "app.sqlite3"
    migrate_app_settings_database(database_file)
    engine = create_settings_engine(database_file)
    session_factory = create_settings_session_factory(engine)
    return ManagedCvRepository(session_factory), ManagedProfileRepository(
        session_factory
    )


def create_profile(
    profile_repository: ManagedProfileRepository,
    profile_id: str,
    *,
    name: str | None = None,
) -> str:
    profile_repository.create_profile(
        profile_id=profile_id,
        name=name or profile_id,
        display_name=None,
        profile_type=ManagedProfileType.FILE_BASED,
        data_dir=Path(f"/tmp/{profile_id}"),
        is_active=False,
    )
    return profile_id


def test_app_settings_migration_creates_managed_cv_tables(tmp_path: Path) -> None:
    database_file = tmp_path / "app.sqlite3"

    migrate_app_settings_database(database_file)

    assert table_names(database_file) >= MANAGED_CV_TABLES
    assert is_app_settings_schema_current(database_file) == (
        True,
        "App settings database file and schema are current.",
    )


def test_app_settings_migration_to_v3_is_idempotent(tmp_path: Path) -> None:
    database_file = tmp_path / "app.sqlite3"

    migrate_app_settings_database(database_file)
    first_tables = table_names(database_file)
    migrate_app_settings_database(database_file)

    assert table_names(database_file) == first_tables


def test_migration_from_v2_to_v3_preserves_settings_and_profiles(
    tmp_path: Path,
) -> None:
    database_file = tmp_path / "app.sqlite3"
    database_file.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(database_file) as connection:
        connection.executescript(
            """
            CREATE TABLE app_settings_schema (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            INSERT INTO app_settings_schema (version) VALUES (1), (2);
            CREATE TABLE app_settings (
                key TEXT PRIMARY KEY,
                value_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            INSERT INTO app_settings (key, value_json) VALUES ('exports.html', 'true');
            CREATE TABLE profiles (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                display_name TEXT,
                profile_type TEXT NOT NULL,
                data_dir TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                CHECK (profile_type IN ('file_based')),
                CHECK (is_active IN (0, 1))
            );
            INSERT INTO profiles (id, name, profile_type, data_dir, is_active)
            VALUES ('profile-1', 'example', 'file_based', '/tmp/example', 1);
            """
        )

    migrate_app_settings_database(database_file)

    assert table_names(database_file) >= MANAGED_CV_TABLES
    with sqlite3.connect(database_file) as connection:
        setting = connection.execute(
            "SELECT value_json FROM app_settings WHERE key = 'exports.html'"
        ).fetchone()
        profile = connection.execute(
            "SELECT name FROM profiles WHERE id = 'profile-1'"
        ).fetchone()
        version = connection.execute(
            "SELECT MAX(version) FROM app_settings_schema"
        ).fetchone()[0]
    assert setting == ("true",)
    assert profile == ("example",)
    assert version == CURRENT_APP_SETTINGS_SCHEMA_VERSION


def test_migration_from_v1_to_v3_creates_profiles_and_managed_cv_tables(
    tmp_path: Path,
) -> None:
    database_file = tmp_path / "app.sqlite3"
    database_file.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(database_file) as connection:
        connection.executescript(
            """
            CREATE TABLE app_settings_schema (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            INSERT INTO app_settings_schema (version) VALUES (1);
            CREATE TABLE app_settings (
                key TEXT PRIMARY KEY,
                value_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            INSERT INTO app_settings (key, value_json) VALUES ('exports.pdf', 'false');
            """
        )

    migrate_app_settings_database(database_file)

    assert table_names(database_file) >= {"profiles"} | MANAGED_CV_TABLES
    assert is_app_settings_schema_current(database_file)[0] is True


def test_managed_cv_tables_are_app_level_not_profile_level(tmp_path: Path) -> None:
    app_database = tmp_path / "app.sqlite3"
    profile_database = tmp_path / "applications.sqlite3"

    migrate_app_settings_database(app_database)
    profile_engine = create_sqlite_engine(profile_database)
    create_all_tables(profile_engine)
    profile_engine.dispose()

    assert table_names(app_database) >= MANAGED_CV_TABLES
    assert MANAGED_CV_TABLES.isdisjoint(table_names(profile_database))


def test_managed_cv_models_use_settings_base_and_not_profile_base_metadata() -> None:
    assert issubclass(managed_cv_models.ManagedCvVariant, SettingsBase)
    assert issubclass(managed_cv_models.ManagedFact, SettingsBase)
    assert set(SettingsBase.metadata.tables) >= MANAGED_CV_TABLES
    assert MANAGED_CV_TABLES.isdisjoint(set(Base.metadata.tables))


def test_create_and_list_cv_variants_for_managed_profile(
    repository: tuple[ManagedCvRepository, ManagedProfileRepository],
) -> None:
    cv_repository, profile_repository = repository
    profile_id = create_profile(profile_repository, "profile-1")

    cv_repository.create_cv_variant(profile_id=profile_id, name="web")
    cv_repository.create_cv_variant(profile_id=profile_id, name="backend")

    assert [variant.name for variant in cv_repository.list_cv_variants(profile_id)] == [
        "backend",
        "web",
    ]


def test_duplicate_variant_name_for_same_profile_is_rejected(
    repository: tuple[ManagedCvRepository, ManagedProfileRepository],
) -> None:
    cv_repository, profile_repository = repository
    profile_id = create_profile(profile_repository, "profile-1")
    cv_repository.create_cv_variant(profile_id=profile_id, name="backend")

    with pytest.raises(DuplicateCvVariantNameError):
        cv_repository.create_cv_variant(profile_id=profile_id, name="backend")


def test_same_variant_name_for_different_profiles_is_allowed(
    repository: tuple[ManagedCvRepository, ManagedProfileRepository],
) -> None:
    cv_repository, profile_repository = repository
    first_profile_id = create_profile(profile_repository, "profile-1")
    second_profile_id = create_profile(profile_repository, "profile-2")

    first = cv_repository.create_cv_variant(profile_id=first_profile_id, name="backend")
    second = cv_repository.create_cv_variant(
        profile_id=second_profile_id, name="backend"
    )

    assert first.name == second.name == "backend"
    assert first.profile_id != second.profile_id


def test_create_list_aliases_sections_and_blocks_with_deterministic_order(
    repository: tuple[ManagedCvRepository, ManagedProfileRepository],
) -> None:
    cv_repository, profile_repository = repository
    profile_id = create_profile(profile_repository, "profile-1")
    variant = cv_repository.create_cv_variant(profile_id=profile_id, name="backend")

    cv_repository.add_variant_alias(variant_id=variant.id, alias="zeta")
    cv_repository.add_variant_alias(variant_id=variant.id, alias="api")
    with pytest.raises(DuplicateCvVariantAliasError):
        cv_repository.add_variant_alias(variant_id=variant.id, alias="api")

    later_section = cv_repository.create_cv_section(
        variant_id=variant.id,
        section_key="projects",
        title="Projects",
        display_order=20,
    )
    earlier_section = cv_repository.create_cv_section(
        variant_id=variant.id,
        section_key="summary",
        title="Summary",
        display_order=10,
        is_required=True,
    )
    cv_repository.create_cv_block(
        section_id=earlier_section.id,
        block_key="second",
        content_markdown="Second block",
        display_order=20,
    )
    cv_repository.create_cv_block(
        section_id=earlier_section.id,
        block_key="first",
        content_markdown="First block",
        display_order=10,
    )
    cv_repository.create_cv_block(
        section_id=later_section.id,
        block_key="project",
        content_markdown="Project block",
        display_order=10,
    )

    assert [
        alias.alias for alias in cv_repository.list_variant_aliases(variant.id)
    ] == [
        "api",
        "zeta",
    ]
    assert [
        section.section_key for section in cv_repository.list_cv_sections(variant.id)
    ] == [
        "summary",
        "projects",
    ]
    assert [
        block.block_key for block in cv_repository.list_cv_blocks(earlier_section.id)
    ] == ["first", "second"]


def test_create_and_list_facts_with_existing_cv_enums(
    repository: tuple[ManagedCvRepository, ManagedProfileRepository],
) -> None:
    cv_repository, profile_repository = repository
    profile_id = create_profile(profile_repository, "profile-1")

    cv_repository.create_fact(
        profile_id=profile_id,
        fact_key="python",
        category=FactCategory.SKILL,
        name="Python",
        allowed_claim_level=AllowedClaimLevel.STRONG,
        evidence="Used Python in fake example projects.",
    )
    cv_repository.create_fact(
        profile_id=profile_id,
        fact_key="api",
        category=FactCategory.PROJECT,
        name="API project",
        allowed_claim_level=AllowedClaimLevel.PRACTICAL,
        evidence="Built a fake REST API example.",
    )

    assert [fact.fact_key for fact in cv_repository.list_facts(profile_id)] == [
        "api",
        "python",
    ]


def test_duplicate_fact_key_for_same_profile_is_rejected(
    repository: tuple[ManagedCvRepository, ManagedProfileRepository],
) -> None:
    cv_repository, profile_repository = repository
    profile_id = create_profile(profile_repository, "profile-1")
    cv_repository.create_fact(
        profile_id=profile_id,
        fact_key="python",
        category=FactCategory.SKILL,
        name="Python",
        allowed_claim_level=AllowedClaimLevel.STRONG,
        evidence="Used Python in fake example projects.",
    )

    with pytest.raises(DuplicateManagedFactKeyError):
        cv_repository.create_fact(
            profile_id=profile_id,
            fact_key="python",
            category=FactCategory.SKILL,
            name="Python",
            allowed_claim_level=AllowedClaimLevel.STRONG,
            evidence="Used Python in fake example projects.",
        )


def test_link_block_to_fact_and_reject_duplicate_link(
    repository: tuple[ManagedCvRepository, ManagedProfileRepository],
) -> None:
    cv_repository, profile_repository = repository
    profile_id = create_profile(profile_repository, "profile-1")
    variant = cv_repository.create_cv_variant(profile_id=profile_id, name="backend")
    section = cv_repository.create_cv_section(
        variant_id=variant.id, section_key="summary", title="Summary", display_order=0
    )
    block = cv_repository.create_cv_block(
        section_id=section.id,
        block_key="intro",
        content_markdown="Intro block",
        display_order=0,
    )
    fact = cv_repository.create_fact(
        profile_id=profile_id,
        fact_key="python",
        category=FactCategory.SKILL,
        name="Python",
        allowed_claim_level=AllowedClaimLevel.STRONG,
        evidence="Used Python in fake example projects.",
    )

    cv_repository.link_block_to_fact(block_id=block.id, fact_id=fact.id)

    assert cv_repository.list_block_fact_links(block.id)[0].fact_id == fact.id
    with pytest.raises(DuplicateBlockFactLinkError):
        cv_repository.link_block_to_fact(block_id=block.id, fact_id=fact.id)


def test_cross_profile_block_fact_link_is_rejected(
    repository: tuple[ManagedCvRepository, ManagedProfileRepository],
) -> None:
    cv_repository, profile_repository = repository
    profile_a_id = create_profile(profile_repository, "profile-a")
    profile_b_id = create_profile(profile_repository, "profile-b")
    variant = cv_repository.create_cv_variant(profile_id=profile_a_id, name="backend")
    section = cv_repository.create_cv_section(
        variant_id=variant.id, section_key="summary", title="Summary", display_order=0
    )
    block = cv_repository.create_cv_block(
        section_id=section.id,
        block_key="intro",
        content_markdown="Intro block",
        display_order=0,
    )
    fact = cv_repository.create_fact(
        profile_id=profile_b_id,
        fact_key="python",
        category=FactCategory.SKILL,
        name="Python",
        allowed_claim_level=AllowedClaimLevel.STRONG,
        evidence="Used Python in fake example projects.",
    )

    with pytest.raises(CrossProfileFactLinkError):
        cv_repository.link_block_to_fact(block_id=block.id, fact_id=fact.id)

    assert cv_repository.list_block_fact_links(block.id) == []


def test_deleting_managed_profile_cascades_managed_cv_records(
    tmp_path: Path,
) -> None:
    database_file = tmp_path / "app.sqlite3"
    migrate_app_settings_database(database_file)
    engine = create_settings_engine(database_file)
    session_factory = create_settings_session_factory(engine)
    cv_repository = ManagedCvRepository(session_factory)
    profile_repository = ManagedProfileRepository(session_factory)
    profile_id = create_profile(profile_repository, "profile-1")
    variant = cv_repository.create_cv_variant(profile_id=profile_id, name="backend")
    section = cv_repository.create_cv_section(
        variant_id=variant.id, section_key="summary", title="Summary", display_order=0
    )
    cv_repository.create_cv_block(
        section_id=section.id,
        block_key="intro",
        content_markdown="Intro block",
        display_order=0,
    )
    cv_repository.create_fact(
        profile_id=profile_id,
        fact_key="python",
        category=FactCategory.SKILL,
        name="Python",
        allowed_claim_level=AllowedClaimLevel.STRONG,
        evidence="Used Python in fake example projects.",
    )

    with session_factory() as session:
        session.execute(delete(ManagedProfile).where(ManagedProfile.id == profile_id))
        session.commit()

    with sqlite3.connect(database_file) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        counts = {
            table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ["cv_variants", "cv_sections", "cv_blocks", "facts"]
        }
    assert counts == {
        "cv_variants": 0,
        "cv_sections": 0,
        "cv_blocks": 0,
        "facts": 0,
    }
