from pathlib import Path
from uuid import uuid4

from app.db.models import ApplicationWarning
from app.db.repositories import ApplicationRepository, ApplicationWarningRepository
from app.db.session import (
    create_all_tables,
    create_session_factory,
    create_sqlite_engine,
)
from app.preflight.persistence import persist_preflight_warnings
from app.preflight.service import PreflightResult


def test_persist_preflight_warnings_creates_warning_records(tmp_path: Path) -> None:
    database_file = tmp_path / "applications.sqlite3"
    engine = create_sqlite_engine(database_file)
    create_all_tables(engine)
    session_factory = create_session_factory(engine)

    duplicate_application_id = uuid4()

    with session_factory() as session:
        applications = ApplicationRepository(session)
        warning_repository = ApplicationWarningRepository(session)

        application = applications.create(profile_name="example")

        result = PreflightResult(
            prompt_injection_phrases=["ignore previous instructions"],
            blacklist_matches=["bad company"],
            duplicate_application_id=str(duplicate_application_id),
        )

        persist_preflight_warnings(
            warnings=warning_repository,
            application_id=application.id,
            result=result,
        )

        session.commit()
        application_id = application.id

    with session_factory() as session:
        warnings = (
            session.query(ApplicationWarning)
            .filter(ApplicationWarning.application_id == application_id)
            .all()
        )

        warning_codes = {warning.code for warning in warnings}

        assert warning_codes == {
            "prompt_injection_phrase",
            "blacklist_match",
            "possible_duplicate",
        }


def test_persist_preflight_warnings_is_noop_for_clean_result(tmp_path: Path) -> None:
    database_file = tmp_path / "applications.sqlite3"
    engine = create_sqlite_engine(database_file)
    create_all_tables(engine)
    session_factory = create_session_factory(engine)

    with session_factory() as session:
        applications = ApplicationRepository(session)
        warning_repository = ApplicationWarningRepository(session)

        application = applications.create(profile_name="example")

        result = PreflightResult(
            prompt_injection_phrases=[],
            blacklist_matches=[],
            duplicate_application_id=None,
        )

        persist_preflight_warnings(
            warnings=warning_repository,
            application_id=application.id,
            result=result,
        )

        session.commit()
        application_id = application.id

    with session_factory() as session:
        warnings = (
            session.query(ApplicationWarning)
            .filter(ApplicationWarning.application_id == application_id)
            .all()
        )

        assert warnings == []
