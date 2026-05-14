from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from app.db.base import Base
from app.db.session import create_all_tables, create_sqlite_engine
from app.settings.init import initialise_app_settings_storage
from app.settings.migrations import (
    is_app_settings_schema_current,
    migrate_app_settings_database,
)
from app.settings.schema import (
    SETTING_EXPORT_HTML,
    SETTING_LLM_EXTRACTION_MODE,
    SETTING_OPENAI_API_KEY_CONFIGURED,
)
from app.storage.app_dirs import build_app_data_paths


def table_names(database_file: Path) -> set[str]:
    with sqlite3.connect(database_file) as connection:
        rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    return {str(row[0]) for row in rows}


def test_app_settings_database_is_created_under_app_data_dir(tmp_path: Path) -> None:
    paths = build_app_data_paths(tmp_path / "app-data")

    service = initialise_app_settings_storage(paths)

    assert paths.database_file == tmp_path / "app-data" / "app.sqlite3"
    assert paths.database_file.is_file()
    assert service.list_settings() == []
    assert "app_settings" in table_names(paths.database_file)


def test_app_settings_migration_is_idempotent(tmp_path: Path) -> None:
    database_file = tmp_path / "app-data" / "app.sqlite3"

    migrate_app_settings_database(database_file)
    first_tables = table_names(database_file)
    migrate_app_settings_database(database_file)

    assert table_names(database_file) == first_tables
    assert is_app_settings_schema_current(database_file) == (
        True,
        "App settings database file and schema are current.",
    )


def test_app_settings_database_is_separate_from_profile_database(
    tmp_path: Path,
) -> None:
    paths = build_app_data_paths(tmp_path / "app-data")
    profile_database = tmp_path / "profile" / "applications.sqlite3"

    initialise_app_settings_storage(paths)
    engine = create_sqlite_engine(profile_database)
    create_all_tables(engine)
    engine.dispose()

    assert paths.database_file != profile_database
    assert "app_settings" in table_names(paths.database_file)
    assert "applications" not in table_names(paths.database_file)
    assert "applications" in table_names(profile_database)
    assert "app_settings" not in table_names(profile_database)


def test_app_settings_storage_does_not_create_profile_database(
    tmp_path: Path,
) -> None:
    paths = build_app_data_paths(tmp_path / "app-data")
    profile_database = tmp_path / "profile" / "applications.sqlite3"

    initialise_app_settings_storage(paths)

    assert paths.database_file.is_file()
    assert not profile_database.exists()


def test_repository_can_set_get_delete_and_list_json_values(tmp_path: Path) -> None:
    service = initialise_app_settings_storage(build_app_data_paths(tmp_path / "app"))

    service.set_setting(SETTING_EXPORT_HTML, False)
    service.set_setting(SETTING_LLM_EXTRACTION_MODE, "openai")

    assert service.get_setting(SETTING_EXPORT_HTML) is False
    assert service.get_setting(SETTING_LLM_EXTRACTION_MODE).value == "openai"
    assert [(setting.key, setting.value) for setting in service.list_settings()] == [
        (SETTING_EXPORT_HTML, False),
        (SETTING_LLM_EXTRACTION_MODE, service.get_setting(SETTING_LLM_EXTRACTION_MODE)),
    ]

    service.delete_setting(SETTING_EXPORT_HTML)

    assert service.get_setting(SETTING_EXPORT_HTML) is None


@pytest.mark.parametrize(
    "key",
    ["openai_api_key", "OPENAI_API_KEY", "api_key", "token", "secret"],
)
def test_secret_looking_setting_keys_are_rejected(tmp_path: Path, key: str) -> None:
    service = initialise_app_settings_storage(build_app_data_paths(tmp_path / "app"))

    with pytest.raises(ValueError):
        service.set_setting(key, "sk-not-a-real-key")

    assert "sk-not-a-real-key" not in (
        tmp_path / "app" / "app.sqlite3"
    ).read_bytes().decode(
        "utf-8",
        errors="ignore",
    )


def test_openai_api_key_configured_boolean_metadata_can_be_stored(
    tmp_path: Path,
) -> None:
    service = initialise_app_settings_storage(build_app_data_paths(tmp_path / "app"))

    service.set_setting(SETTING_OPENAI_API_KEY_CONFIGURED, True)

    assert service.get_setting(SETTING_OPENAI_API_KEY_CONFIGURED) is True


def test_openai_api_key_configured_rejects_raw_secret_value(tmp_path: Path) -> None:
    service = initialise_app_settings_storage(build_app_data_paths(tmp_path / "app"))

    with pytest.raises(ValueError):
        service.set_setting(SETTING_OPENAI_API_KEY_CONFIGURED, "sk-not-a-real-key")


def test_app_settings_do_not_affect_profile_base_metadata() -> None:
    assert "app_settings" not in Base.metadata.tables
