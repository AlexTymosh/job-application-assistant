from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import Engine, create_engine, event, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from app.db import models  # noqa: F401
from app.db.base import Base


def create_sqlite_engine(database_file: Path | str) -> Engine:
    database_path = Path(database_file)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{database_path}", future=True)

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _connection_record) -> None:  # type: ignore[no-untyped-def]
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(
        bind=engine, expire_on_commit=False, autoflush=False, future=True
    )


def initialise_database(engine: Engine) -> None:
    Base.metadata.create_all(engine)
    _apply_idempotent_sqlite_updates(engine)


# Local-first MVP compatibility bridge.  Older development databases may have
# tables created before the SQL-first reset; SQLite CREATE TABLE IF NOT EXISTS
# does not add newly modelled columns to those existing tables.  Keep the repair
# list explicit and idempotent until a full migration system is adopted.
_SQLITE_COLUMN_REPAIRS: dict[str, dict[str, str]] = {
    "app_settings": {
        "created_at": "DATETIME NOT NULL DEFAULT '1970-01-01 00:00:00'",
        "updated_at": "DATETIME NOT NULL DEFAULT '1970-01-01 00:00:00'",
    },
    "person_profiles": {
        "full_name": "VARCHAR(200) NOT NULL DEFAULT ''",
        "preferred_name": "VARCHAR(120) NOT NULL DEFAULT ''",
        "location": "VARCHAR(200) NOT NULL DEFAULT ''",
        "is_active": "BOOLEAN NOT NULL DEFAULT 1",
        "created_at": "DATETIME NOT NULL DEFAULT '1970-01-01 00:00:00'",
        "updated_at": "DATETIME NOT NULL DEFAULT '1970-01-01 00:00:00'",
    },
    "profile_contacts": {
        "email": "VARCHAR(254) NOT NULL DEFAULT ''",
        "phone": "VARCHAR(80) NOT NULL DEFAULT ''",
        "address_line": "VARCHAR(240) NOT NULL DEFAULT ''",
        "city": "VARCHAR(120) NOT NULL DEFAULT ''",
        "country": "VARCHAR(120) NOT NULL DEFAULT ''",
        "links_json": "JSON NOT NULL DEFAULT '[]'",
        "visibility_json": "JSON NOT NULL DEFAULT '{}'",
        "created_at": "DATETIME NOT NULL DEFAULT '1970-01-01 00:00:00'",
        "updated_at": "DATETIME NOT NULL DEFAULT '1970-01-01 00:00:00'",
    },
    "resumes": {
        "target_role": "VARCHAR(160) NOT NULL DEFAULT ''",
        "language": "VARCHAR(32) NOT NULL DEFAULT 'en'",
        "is_default": "BOOLEAN NOT NULL DEFAULT 0",
        "created_at": "DATETIME NOT NULL DEFAULT '1970-01-01 00:00:00'",
        "updated_at": "DATETIME NOT NULL DEFAULT '1970-01-01 00:00:00'",
    },
    "resume_sections": {
        "title": "VARCHAR(160) NOT NULL DEFAULT ''",
        "display_order": "INTEGER NOT NULL DEFAULT 0",
        "is_visible": "BOOLEAN NOT NULL DEFAULT 1",
        "ai_edit_enabled": "BOOLEAN NOT NULL DEFAULT 0",
        "ai_prompt_key": "VARCHAR(120) NOT NULL DEFAULT ''",
        "policy_json": "JSON NOT NULL DEFAULT '{}'",
        "created_at": "DATETIME NOT NULL DEFAULT '1970-01-01 00:00:00'",
        "updated_at": "DATETIME NOT NULL DEFAULT '1970-01-01 00:00:00'",
    },
    "resume_blocks": {
        "title": "VARCHAR(200) NOT NULL DEFAULT ''",
        "subtitle": "VARCHAR(200) NOT NULL DEFAULT ''",
        "organisation": "VARCHAR(200) NOT NULL DEFAULT ''",
        "role_title": "VARCHAR(200) NOT NULL DEFAULT ''",
        "location": "VARCHAR(200) NOT NULL DEFAULT ''",
        "start_date": "VARCHAR(40) NOT NULL DEFAULT ''",
        "end_date": "VARCHAR(40) NOT NULL DEFAULT ''",
        "is_current": "BOOLEAN NOT NULL DEFAULT 0",
        "content": "TEXT NOT NULL DEFAULT ''",
        "display_order": "INTEGER NOT NULL DEFAULT 0",
        "is_visible": "BOOLEAN NOT NULL DEFAULT 1",
        "ai_edit_enabled": "BOOLEAN NOT NULL DEFAULT 0",
        "ai_edit_mode": "VARCHAR(80) NOT NULL DEFAULT 'none'",
        "metadata_json": "JSON NOT NULL DEFAULT '{}'",
        "policy_json": "JSON NOT NULL DEFAULT '{}'",
        "created_at": "DATETIME NOT NULL DEFAULT '1970-01-01 00:00:00'",
        "updated_at": "DATETIME NOT NULL DEFAULT '1970-01-01 00:00:00'",
    },
    "resume_bullets": {
        "display_order": "INTEGER NOT NULL DEFAULT 0",
        "is_visible": "BOOLEAN NOT NULL DEFAULT 1",
        "ai_edit_enabled": "BOOLEAN NOT NULL DEFAULT 0",
        "fact_link_required": "BOOLEAN NOT NULL DEFAULT 1",
        "created_at": "DATETIME NOT NULL DEFAULT '1970-01-01 00:00:00'",
        "updated_at": "DATETIME NOT NULL DEFAULT '1970-01-01 00:00:00'",
    },
    "facts": {
        "claim": "TEXT NOT NULL DEFAULT ''",
        "evidence": "TEXT NOT NULL DEFAULT ''",
        "source": "VARCHAR(240) NOT NULL DEFAULT ''",
        "allowed_claim_level": "VARCHAR(40) NOT NULL DEFAULT 'mention_only'",
        "confidence": "VARCHAR(40) NOT NULL DEFAULT 'medium'",
        "is_active": "BOOLEAN NOT NULL DEFAULT 1",
        "created_at": "DATETIME NOT NULL DEFAULT '1970-01-01 00:00:00'",
        "updated_at": "DATETIME NOT NULL DEFAULT '1970-01-01 00:00:00'",
    },
    "prompt_templates": {
        "section_type": "VARCHAR(80) NOT NULL DEFAULT ''",
        "is_active": "BOOLEAN NOT NULL DEFAULT 1",
        "profile_id": "INTEGER",
        "resume_id": "INTEGER",
        "section_id": "INTEGER",
        "created_at": "DATETIME NOT NULL DEFAULT '1970-01-01 00:00:00'",
        "updated_at": "DATETIME NOT NULL DEFAULT '1970-01-01 00:00:00'",
    },
    "applications": {
        "job_title": "VARCHAR(200) NOT NULL DEFAULT ''",
        "company_name": "VARCHAR(200) NOT NULL DEFAULT ''",
        "source_url": "VARCHAR(500) NOT NULL DEFAULT ''",
        "status": "VARCHAR(60) NOT NULL DEFAULT 'job_saved'",
        "created_at": "DATETIME NOT NULL DEFAULT '1970-01-01 00:00:00'",
        "updated_at": "DATETIME NOT NULL DEFAULT '1970-01-01 00:00:00'",
    },
}


def _apply_idempotent_sqlite_updates(engine: Engine) -> None:
    if engine.dialect.name != "sqlite":
        return
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    with engine.begin() as connection:
        for table_name, desired_columns in _SQLITE_COLUMN_REPAIRS.items():
            if table_name not in table_names:
                continue
            existing_columns = {
                column["name"] for column in inspect(connection).get_columns(table_name)
            }
            for column_name, column_sql in desired_columns.items():
                if column_name not in existing_columns:
                    connection.execute(
                        text(
                            f"ALTER TABLE {table_name} ADD COLUMN "
                            f"{column_name} {column_sql}"
                        )
                    )


def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    with factory() as session:
        yield session
