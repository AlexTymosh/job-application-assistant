from pathlib import Path
from uuid import uuid4

from app.db.repositories import ApplicationRepository
from app.db.session import (
    create_all_tables,
    create_session_factory,
    create_sqlite_engine,
)
from app.preflight.duplicate_detection import find_duplicate_by_job_text_hash


def test_find_duplicate_by_job_text_hash_returns_matching_application(
    tmp_path: Path,
) -> None:
    database_file = tmp_path / "applications.sqlite3"
    engine = create_sqlite_engine(database_file)
    create_all_tables(engine)
    session_factory = create_session_factory(engine)

    with session_factory() as session:
        applications = ApplicationRepository(session)
        application = applications.create(profile_name="example")
        application.job_text_hash = "abc123"
        session.commit()
        application_id = application.id

    with session_factory() as session:
        result = find_duplicate_by_job_text_hash(
            session=session,
            profile_name="example",
            job_text_hash="abc123",
        )

        assert result is not None
        assert result.id == application_id


def test_find_duplicate_by_job_text_hash_ignores_other_profiles(
    tmp_path: Path,
) -> None:
    database_file = tmp_path / "applications.sqlite3"
    engine = create_sqlite_engine(database_file)
    create_all_tables(engine)
    session_factory = create_session_factory(engine)

    with session_factory() as session:
        applications = ApplicationRepository(session)
        application = applications.create(profile_name="other")
        application.job_text_hash = "abc123"
        session.commit()

    with session_factory() as session:
        result = find_duplicate_by_job_text_hash(
            session=session,
            profile_name="example",
            job_text_hash="abc123",
        )

        assert result is None


def test_find_duplicate_by_job_text_hash_returns_none_for_missing_hash(
    tmp_path: Path,
) -> None:
    database_file = tmp_path / "applications.sqlite3"
    engine = create_sqlite_engine(database_file)
    create_all_tables(engine)
    session_factory = create_session_factory(engine)

    with session_factory() as session:
        result = find_duplicate_by_job_text_hash(
            session=session,
            profile_name="example",
            job_text_hash=None,
        )

        assert result is None


def test_find_duplicate_by_job_text_hash_returns_none_when_no_match(
    tmp_path: Path,
) -> None:
    database_file = tmp_path / "applications.sqlite3"
    engine = create_sqlite_engine(database_file)
    create_all_tables(engine)
    session_factory = create_session_factory(engine)

    with session_factory() as session:
        applications = ApplicationRepository(session)
        application = applications.create(profile_name="example")
        application.job_text_hash = "abc123"
        session.commit()

    with session_factory() as session:
        result = find_duplicate_by_job_text_hash(
            session=session,
            profile_name="example",
            job_text_hash="different_hash",
        )

        assert result is None


def test_find_duplicate_by_job_text_hash_can_exclude_current_application(
    tmp_path: Path,
) -> None:
    database_file = tmp_path / "applications.sqlite3"
    engine = create_sqlite_engine(database_file)
    create_all_tables(engine)
    session_factory = create_session_factory(engine)

    with session_factory() as session:
        applications = ApplicationRepository(session)
        application = applications.create(profile_name="example")
        application.job_text_hash = "abc123"
        session.commit()
        application_id = application.id

    with session_factory() as session:
        result = find_duplicate_by_job_text_hash(
            session=session,
            profile_name="example",
            job_text_hash="abc123",
            exclude_application_id=application_id,
        )

        assert result is None


def test_find_duplicate_by_job_text_hash_does_not_exclude_other_application(
    tmp_path: Path,
) -> None:
    database_file = tmp_path / "applications.sqlite3"
    engine = create_sqlite_engine(database_file)
    create_all_tables(engine)
    session_factory = create_session_factory(engine)

    with session_factory() as session:
        applications = ApplicationRepository(session)
        application = applications.create(profile_name="example")
        application.job_text_hash = "abc123"
        session.commit()
        application_id = application.id

    with session_factory() as session:
        result = find_duplicate_by_job_text_hash(
            session=session,
            profile_name="example",
            job_text_hash="abc123",
            exclude_application_id=uuid4(),
        )

        assert result is not None
        assert result.id == application_id
