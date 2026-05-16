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


def _apply_idempotent_sqlite_updates(engine: Engine) -> None:
    """Repair known SQL-first MVP SQLite schema drift in existing local databases.

    The local-first app intentionally starts without a full migration framework for the
    first release. ``create_all`` creates missing tables, but SQLite does not add new
    columns to tables that already exist. These explicit, idempotent repairs bridge
    databases created during the architecture reset to the current SQLAlchemy models.
    """

    if engine.dialect.name != "sqlite":
        return

    table_repairs: dict[str, dict[str, str]] = {
        "app_settings": {
            "created_at": "DATETIME DEFAULT '1970-01-01 00:00:00' NOT NULL",
            "updated_at": "DATETIME DEFAULT '1970-01-01 00:00:00' NOT NULL",
        },
        "person_profiles": {
            "full_name": "VARCHAR(200) DEFAULT '' NOT NULL",
            "preferred_name": "VARCHAR(120) DEFAULT '' NOT NULL",
            "location": "VARCHAR(200) DEFAULT '' NOT NULL",
            "is_active": "BOOLEAN DEFAULT 1 NOT NULL",
            "created_at": "DATETIME DEFAULT '1970-01-01 00:00:00' NOT NULL",
            "updated_at": "DATETIME DEFAULT '1970-01-01 00:00:00' NOT NULL",
        },
        "profile_contacts": {
            "email": "VARCHAR(254) DEFAULT '' NOT NULL",
            "phone": "VARCHAR(80) DEFAULT '' NOT NULL",
            "address_line": "VARCHAR(240) DEFAULT '' NOT NULL",
            "city": "VARCHAR(120) DEFAULT '' NOT NULL",
            "country": "VARCHAR(120) DEFAULT '' NOT NULL",
            "links_json": "JSON DEFAULT '[]' NOT NULL",
            "visibility_json": "JSON DEFAULT '{}' NOT NULL",
            "created_at": "DATETIME DEFAULT '1970-01-01 00:00:00' NOT NULL",
            "updated_at": "DATETIME DEFAULT '1970-01-01 00:00:00' NOT NULL",
        },
        "resumes": {
            "target_role": "VARCHAR(160) DEFAULT '' NOT NULL",
            "language": "VARCHAR(32) DEFAULT 'en' NOT NULL",
            "is_default": "BOOLEAN DEFAULT 0 NOT NULL",
            "created_at": "DATETIME DEFAULT '1970-01-01 00:00:00' NOT NULL",
            "updated_at": "DATETIME DEFAULT '1970-01-01 00:00:00' NOT NULL",
        },
        "resume_sections": {
            "display_order": "INTEGER DEFAULT 0 NOT NULL",
            "is_visible": "BOOLEAN DEFAULT 1 NOT NULL",
            "ai_edit_enabled": "BOOLEAN DEFAULT 0 NOT NULL",
            "ai_prompt_key": "VARCHAR(120) DEFAULT '' NOT NULL",
            "policy_json": "JSON DEFAULT '{}' NOT NULL",
            "created_at": "DATETIME DEFAULT '1970-01-01 00:00:00' NOT NULL",
            "updated_at": "DATETIME DEFAULT '1970-01-01 00:00:00' NOT NULL",
        },
        "resume_blocks": {
            "subtitle": "VARCHAR(200) DEFAULT '' NOT NULL",
            "organisation": "VARCHAR(200) DEFAULT '' NOT NULL",
            "role_title": "VARCHAR(200) DEFAULT '' NOT NULL",
            "location": "VARCHAR(200) DEFAULT '' NOT NULL",
            "start_date": "VARCHAR(40) DEFAULT '' NOT NULL",
            "end_date": "VARCHAR(40) DEFAULT '' NOT NULL",
            "is_current": "BOOLEAN DEFAULT 0 NOT NULL",
            "content": "TEXT DEFAULT '' NOT NULL",
            "display_order": "INTEGER DEFAULT 0 NOT NULL",
            "is_visible": "BOOLEAN DEFAULT 1 NOT NULL",
            "ai_edit_enabled": "BOOLEAN DEFAULT 0 NOT NULL",
            "ai_edit_mode": "VARCHAR(80) DEFAULT 'none' NOT NULL",
            "metadata_json": "JSON DEFAULT '{}' NOT NULL",
            "policy_json": "JSON DEFAULT '{}' NOT NULL",
            "created_at": "DATETIME DEFAULT '1970-01-01 00:00:00' NOT NULL",
            "updated_at": "DATETIME DEFAULT '1970-01-01 00:00:00' NOT NULL",
        },
        "resume_bullets": {
            "display_order": "INTEGER DEFAULT 0 NOT NULL",
            "is_visible": "BOOLEAN DEFAULT 1 NOT NULL",
            "ai_edit_enabled": "BOOLEAN DEFAULT 0 NOT NULL",
            "fact_link_required": "BOOLEAN DEFAULT 1 NOT NULL",
            "created_at": "DATETIME DEFAULT '1970-01-01 00:00:00' NOT NULL",
            "updated_at": "DATETIME DEFAULT '1970-01-01 00:00:00' NOT NULL",
        },
        "skill_items": {
            "category": "VARCHAR(120) DEFAULT '' NOT NULL",
            "display_order": "INTEGER DEFAULT 0 NOT NULL",
            "created_at": "DATETIME DEFAULT '1970-01-01 00:00:00' NOT NULL",
            "updated_at": "DATETIME DEFAULT '1970-01-01 00:00:00' NOT NULL",
        },
        "facts": {
            "category": "VARCHAR(120) DEFAULT '' NOT NULL",
            "claim": "TEXT DEFAULT '' NOT NULL",
            "evidence": "TEXT DEFAULT '' NOT NULL",
            "source": "VARCHAR(240) DEFAULT '' NOT NULL",
            "allowed_claim_level": "VARCHAR(40) DEFAULT 'mention_only' NOT NULL",
            "confidence": "VARCHAR(40) DEFAULT 'medium' NOT NULL",
            "is_active": "BOOLEAN DEFAULT 1 NOT NULL",
            "created_at": "DATETIME DEFAULT '1970-01-01 00:00:00' NOT NULL",
            "updated_at": "DATETIME DEFAULT '1970-01-01 00:00:00' NOT NULL",
        },
        "prompt_templates": {
            "section_type": "VARCHAR(80) DEFAULT '' NOT NULL",
            "is_active": "BOOLEAN DEFAULT 1 NOT NULL",
            "profile_id": "INTEGER",
            "resume_id": "INTEGER",
            "section_id": "INTEGER",
            "created_at": "DATETIME DEFAULT '1970-01-01 00:00:00' NOT NULL",
            "updated_at": "DATETIME DEFAULT '1970-01-01 00:00:00' NOT NULL",
        },
        "applications": {
            "job_title": "VARCHAR(200) DEFAULT '' NOT NULL",
            "company_name": "VARCHAR(200) DEFAULT '' NOT NULL",
            "source_url": "VARCHAR(500) DEFAULT '' NOT NULL",
            "status": "VARCHAR(60) DEFAULT 'job_saved' NOT NULL",
            "created_at": "DATETIME DEFAULT '1970-01-01 00:00:00' NOT NULL",
            "updated_at": "DATETIME DEFAULT '1970-01-01 00:00:00' NOT NULL",
        },
        "application_events": {
            "message": "TEXT DEFAULT '' NOT NULL",
            "metadata_json": "JSON DEFAULT '{}' NOT NULL",
            "created_at": "DATETIME DEFAULT '1970-01-01 00:00:00' NOT NULL",
        },
        "extracted_job_requirements": {
            "keywords_json": "JSON DEFAULT '[]' NOT NULL",
            "priority": "INTEGER DEFAULT 3 NOT NULL",
            "created_at": "DATETIME DEFAULT '1970-01-01 00:00:00' NOT NULL",
        },
        "tailoring_runs": {
            "status": "VARCHAR(60) DEFAULT 'proposed' NOT NULL",
            "model": "VARCHAR(120) DEFAULT 'fake-deterministic' NOT NULL",
            "warnings_json": "JSON DEFAULT '[]' NOT NULL",
            "created_at": "DATETIME DEFAULT '1970-01-01 00:00:00' NOT NULL",
            "completed_at": "DATETIME",
        },
        "ai_change_proposals": {
            "before_text": "TEXT DEFAULT '' NOT NULL",
            "after_text": "TEXT DEFAULT '' NOT NULL",
            "reason": "TEXT DEFAULT '' NOT NULL",
            "risk_level": "VARCHAR(40) DEFAULT 'low' NOT NULL",
            "requirement_ids_json": "JSON DEFAULT '[]' NOT NULL",
            "fact_ids_json": "JSON DEFAULT '[]' NOT NULL",
            "warning_codes_json": "JSON DEFAULT '[]' NOT NULL",
            "status": "VARCHAR(40) DEFAULT 'proposed' NOT NULL",
            "created_at": "DATETIME DEFAULT '1970-01-01 00:00:00' NOT NULL",
            "decided_at": "DATETIME",
        },
        "tailored_resume_snapshots": {
            "content_json": "JSON DEFAULT '{}' NOT NULL",
            "rendered_markdown": "TEXT DEFAULT '' NOT NULL",
            "created_at": "DATETIME DEFAULT '1970-01-01 00:00:00' NOT NULL",
        },
        "cover_letters": {
            "prompt_version": "VARCHAR(80) DEFAULT 'cover-letter-v1' NOT NULL",
            "status": "VARCHAR(40) DEFAULT 'draft' NOT NULL",
            "created_at": "DATETIME DEFAULT '1970-01-01 00:00:00' NOT NULL",
            "updated_at": "DATETIME DEFAULT '1970-01-01 00:00:00' NOT NULL",
        },
        "artifacts": {
            "created_at": "DATETIME DEFAULT '1970-01-01 00:00:00' NOT NULL",
        },
    }

    with engine.begin() as connection:
        inspector = inspect(connection)
        existing_tables = set(inspector.get_table_names())
        for table_name, desired_columns in table_repairs.items():
            if table_name not in existing_tables:
                continue
            existing_columns = {
                column["name"] for column in inspector.get_columns(table_name)
            }
            for column_name, column_definition in desired_columns.items():
                if column_name not in existing_columns:
                    connection.execute(
                        text(
                            f"ALTER TABLE {table_name} "
                            f"ADD COLUMN {column_name} {column_definition}"
                        )
                    )


def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    with factory() as session:
        yield session
