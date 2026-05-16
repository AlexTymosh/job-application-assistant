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
    inspector = inspect(engine)
    if "prompt_templates" not in inspector.get_table_names():
        return
    existing_columns = {
        column["name"] for column in inspector.get_columns("prompt_templates")
    }
    desired_columns = {
        "profile_id": "INTEGER",
        "resume_id": "INTEGER",
        "section_id": "INTEGER",
    }
    with engine.begin() as connection:
        for name, column_type in desired_columns.items():
            if name not in existing_columns:
                connection.execute(
                    text(
                        f"ALTER TABLE prompt_templates ADD COLUMN {name} {column_type}"
                    )
                )


def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    with factory() as session:
        yield session
