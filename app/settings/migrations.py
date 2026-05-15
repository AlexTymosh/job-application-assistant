from __future__ import annotations

import sqlite3
from pathlib import Path

CURRENT_APP_SETTINGS_SCHEMA_VERSION = 3
_SCHEMA_TABLE = "app_settings_schema"


def migrate_app_settings_database(database_file: Path) -> None:
    """Apply deterministic app-settings migrations to the app data database."""
    database_file.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(database_file) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        _create_schema_table(connection)
        current_version = _read_schema_version(connection)
        if current_version < 1:
            _apply_version_1(connection)
            _write_schema_version(connection, 1)
            current_version = 1
        if current_version < 2:
            _apply_version_2(connection)
            _write_schema_version(connection, 2)
            current_version = 2
        if current_version < 3:
            _apply_version_3(connection)
            _write_schema_version(connection, 3)
        connection.commit()


def is_app_settings_schema_current(database_file: Path) -> tuple[bool, str]:
    if not database_file.is_file():
        return False, "App settings database file is missing."

    try:
        with sqlite3.connect(f"file:{database_file}?mode=ro", uri=True) as connection:
            table_names = _read_table_names(connection)
            missing_tables = sorted(_required_app_settings_tables() - table_names)
            if missing_tables:
                return (
                    False,
                    "App settings database is missing expected tables: "
                    + ", ".join(missing_tables),
                )
            version = _read_schema_version(connection)
    except sqlite3.DatabaseError as exc:
        return False, f"App settings database is unreadable: {exc}"
    except OSError as exc:
        return False, f"App settings database could not be opened: {exc}"

    if version != CURRENT_APP_SETTINGS_SCHEMA_VERSION:
        return (
            False,
            "App settings schema version is "
            f"{version}; expected {CURRENT_APP_SETTINGS_SCHEMA_VERSION}.",
        )

    return True, "App settings database file and schema are current."


def _create_schema_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {_SCHEMA_TABLE} (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def _apply_version_1(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value_json TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def _apply_version_2(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS profiles (
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
        )
        """
    )
    connection.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ix_profiles_single_active
        ON profiles (is_active)
        WHERE is_active = 1
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_profiles_name
        ON profiles (name)
        """
    )


def _apply_version_3(connection: sqlite3.Connection) -> None:
    fact_categories = _sql_string_values(
        "skill",
        "experience",
        "project",
        "education",
        "certification",
        "language",
        "domain",
        "other",
    )
    allowed_claim_levels = _sql_string_values(
        "mention_only",
        "practical",
        "strong",
        "do_not_claim",
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS cv_variants (
            id TEXT PRIMARY KEY,
            profile_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            display_name TEXT,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(profile_id, name),
            CHECK(is_active IN (0, 1))
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS cv_variant_aliases (
            id TEXT PRIMARY KEY,
            variant_id TEXT NOT NULL REFERENCES cv_variants(id) ON DELETE CASCADE,
            alias TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(variant_id, alias)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS cv_sections (
            id TEXT PRIMARY KEY,
            variant_id TEXT NOT NULL REFERENCES cv_variants(id) ON DELETE CASCADE,
            section_key TEXT NOT NULL,
            title TEXT NOT NULL,
            display_order INTEGER NOT NULL,
            is_required INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(variant_id, section_key),
            CHECK(is_required IN (0, 1))
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS cv_blocks (
            id TEXT PRIMARY KEY,
            section_id TEXT NOT NULL REFERENCES cv_sections(id) ON DELETE CASCADE,
            block_key TEXT NOT NULL,
            content_markdown TEXT NOT NULL,
            display_order INTEGER NOT NULL,
            is_enabled INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(section_id, block_key),
            CHECK(is_enabled IN (0, 1))
        )
        """
    )
    connection.execute(
        f"""
        CREATE TABLE IF NOT EXISTS facts (
            id TEXT PRIMARY KEY,
            profile_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
            fact_key TEXT NOT NULL,
            category TEXT NOT NULL,
            name TEXT NOT NULL,
            allowed_claim_level TEXT NOT NULL,
            evidence TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(profile_id, fact_key),
            CHECK(category IN ({fact_categories})),
            CHECK(allowed_claim_level IN ({allowed_claim_levels})),
            CHECK(is_active IN (0, 1))
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS cv_block_fact_links (
            block_id TEXT NOT NULL REFERENCES cv_blocks(id) ON DELETE CASCADE,
            fact_id TEXT NOT NULL REFERENCES facts(id) ON DELETE CASCADE,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY(block_id, fact_id)
        )
        """
    )
    for statement in (
        """
        CREATE INDEX IF NOT EXISTS ix_cv_variants_profile_id
        ON cv_variants (profile_id)
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_cv_sections_variant_id
        ON cv_sections (variant_id)
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_cv_blocks_section_id
        ON cv_blocks (section_id)
        """,
        "CREATE INDEX IF NOT EXISTS ix_facts_profile_id ON facts (profile_id)",
        """
        CREATE INDEX IF NOT EXISTS ix_cv_block_fact_links_fact_id
        ON cv_block_fact_links (fact_id)
        """,
    ):
        connection.execute(statement)


def _required_app_settings_tables() -> set[str]:
    return {
        _SCHEMA_TABLE,
        "app_settings",
        "profiles",
        "cv_variants",
        "cv_variant_aliases",
        "cv_sections",
        "cv_blocks",
        "facts",
        "cv_block_fact_links",
    }


def _sql_string_values(*values: str) -> str:
    return ", ".join(f"'{value}'" for value in values)


def _read_schema_version(connection: sqlite3.Connection) -> int:
    try:
        row = connection.execute(f"SELECT MAX(version) FROM {_SCHEMA_TABLE}").fetchone()
    except sqlite3.DatabaseError:
        return 0

    value = row[0] if row else None
    return int(value) if value is not None else 0


def _write_schema_version(connection: sqlite3.Connection, version: int) -> None:
    connection.execute(
        f"INSERT OR IGNORE INTO {_SCHEMA_TABLE} (version) VALUES (?)",
        (version,),
    )


def _read_table_names(connection: sqlite3.Connection) -> set[str]:
    rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
    ).fetchall()
    return {str(row[0]) for row in rows}
