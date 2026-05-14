from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from sqlite3 import Connection as SQLiteConnection

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker


def build_settings_sqlite_url(database_file: Path) -> str:
    return f"sqlite:///{database_file.as_posix()}"


def create_settings_engine(database_file: Path) -> Engine:
    database_file.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        build_settings_sqlite_url(database_file),
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def enable_sqlite_foreign_keys(
        dbapi_connection: SQLiteConnection,
        _connection_record: object,
    ) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


def create_settings_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@contextmanager
def settings_session_scope(
    session_factory: sessionmaker[Session],
) -> Iterator[Session]:
    with session_factory() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
