from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import Artifact
from app.db.session import create_all_tables, create_sqlite_engine


def test_create_all_tables(tmp_path: Path) -> None:
    database_file = tmp_path / "applications.sqlite3"
    engine = create_sqlite_engine(database_file)

    create_all_tables(engine)

    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())

    assert "applications" in table_names
    assert "artifacts" in table_names
    assert "application_events" in table_names
    assert "application_warnings" in table_names

    application_columns = {
        column["name"] for column in inspector.get_columns("applications")
    }
    assert "artifact_dir_name" in application_columns


def test_sqlite_foreign_keys_are_enforced(tmp_path: Path) -> None:
    database_file = tmp_path / "applications.sqlite3"
    engine = create_sqlite_engine(database_file)
    create_all_tables(engine)

    with Session(engine) as session:
        session.add(
            Artifact(
                application_id=uuid4(),
                artifact_type="job_raw",
                path="missing/application/job_raw.txt",
            )
        )

        with pytest.raises(IntegrityError):
            session.commit()
