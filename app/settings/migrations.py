from __future__ import annotations

import sqlite3
from pathlib import Path

CURRENT_APP_SETTINGS_SCHEMA_VERSION = 1
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
        connection.commit()


def is_app_settings_schema_current(database_file: Path) -> tuple[bool, str]:
    if not database_file.is_file():
        return False, "App settings database file is missing."

    try:
        with sqlite3.connect(f"file:{database_file}?mode=ro", uri=True) as connection:
            table_names = _read_table_names(connection)
            required_tables = {"app_settings", _SCHEMA_TABLE}
            missing_tables = sorted(required_tables - table_names)
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
