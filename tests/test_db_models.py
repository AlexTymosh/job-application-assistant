from pathlib import Path

from sqlalchemy import inspect

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
