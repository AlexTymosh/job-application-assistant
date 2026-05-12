from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base


def build_sqlite_url(database_file: Path) -> str:
    return f"sqlite:///{database_file.as_posix()}"


def create_sqlite_engine(database_file: Path) -> Engine:
    database_file.parent.mkdir(parents=True, exist_ok=True)

    return create_engine(
        build_sqlite_url(database_file),
        connect_args={"check_same_thread": False},
    )


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )


def create_all_tables(engine: Engine) -> None:
    Base.metadata.create_all(bind=engine)


def session_scope(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    with session_factory() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
