from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, inspect, text

from app.db.session import initialise_database


def test_initialise_database_repairs_missing_prompt_variant_column(tmp_path: Path):
    db_path = tmp_path / "legacy.sqlite3"
    engine = create_engine(f"sqlite:///{db_path}", future=True)

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE applications (
                    id INTEGER PRIMARY KEY,
                    profile_id INTEGER NOT NULL,
                    base_resume_id INTEGER NOT NULL,
                    tailored_resume_id INTEGER,
                    application_number INTEGER NOT NULL UNIQUE,
                    job_title VARCHAR(200) NOT NULL DEFAULT '',
                    company_name VARCHAR(200) NOT NULL DEFAULT '',
                    source_url VARCHAR(500) NOT NULL DEFAULT '',
                    raw_job_text TEXT NOT NULL,
                    status VARCHAR(60) NOT NULL DEFAULT 'job_saved',
                    created_at DATETIME,
                    updated_at DATETIME
                )
                """
            )
        )

    initialise_database(engine)
    inspector = inspect(engine)

    columns = {column["name"] for column in inspector.get_columns("applications")}
    tables = set(inspector.get_table_names())

    assert "prompt_variant_id" in columns
    assert "prompt_variants" in tables
    assert "prompt_variant_templates" in tables
