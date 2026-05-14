from pathlib import Path

from app.db.models import ApplicationStatus
from app.db.repositories import (
    ApplicationEventRepository,
    ApplicationRepository,
    ApplicationWarningRepository,
    ArtifactRepository,
)
from app.db.session import (
    create_all_tables,
    create_session_factory,
    create_sqlite_engine,
    session_scope,
)


def test_create_application_and_related_records(tmp_path: Path) -> None:
    database_file = tmp_path / "applications.sqlite3"
    engine = create_sqlite_engine(database_file)
    create_all_tables(engine)
    session_factory = create_session_factory(engine)

    with session_factory() as session:
        applications = ApplicationRepository(session)
        artifacts = ArtifactRepository(session)
        events = ApplicationEventRepository(session)
        warnings = ApplicationWarningRepository(session)

        application = applications.create(
            profile_name="example",
            job_title="Backend Developer",
            company_name="Example Company",
            source_url="https://example.test/jobs/backend",
            selected_cv_variant="backend_developer",
        )

        artifacts.create(
            application_id=application.id,
            artifact_type="job_raw",
            path="profiles/example/applications/example/job_raw.txt",
        )
        events.create(
            application_id=application.id,
            event_type="application_created",
            message="Application record created.",
        )
        warnings.create(
            application_id=application.id,
            code="example_warning",
            message="Example warning.",
        )

        session.commit()

    with session_factory() as session:
        applications = ApplicationRepository(session)

        stored_applications = applications.list_by_profile("example")

        assert len(stored_applications) == 1
        assert stored_applications[0].job_title == "Backend Developer"
        assert stored_applications[0].status == ApplicationStatus.DRAFT.value
        assert stored_applications[0].artifact_dir_name is not None
        assert "example-company" in stored_applications[0].artifact_dir_name
        assert "backend-developer" in stored_applications[0].artifact_dir_name


def test_update_application_status(tmp_path: Path) -> None:
    database_file = tmp_path / "applications.sqlite3"
    engine = create_sqlite_engine(database_file)
    create_all_tables(engine)
    session_factory = create_session_factory(engine)

    with session_factory() as session:
        applications = ApplicationRepository(session)
        application = applications.create(profile_name="example")
        session.commit()
        application_id = application.id

    with session_factory() as session:
        applications = ApplicationRepository(session)
        updated = applications.update_status(
            application_id=application_id,
            status=ApplicationStatus.JOB_EXTRACTED,
        )
        session.commit()

        assert updated.status == ApplicationStatus.JOB_EXTRACTED.value


def test_session_scope_commits_successful_transaction(tmp_path: Path) -> None:
    database_file = tmp_path / "applications.sqlite3"
    engine = create_sqlite_engine(database_file)
    create_all_tables(engine)
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        applications = ApplicationRepository(session)
        application = applications.create(profile_name="example")
        application_id = application.id

    with session_factory() as session:
        applications = ApplicationRepository(session)
        stored_application = applications.get(application_id)

        assert stored_application is not None
        assert stored_application.profile_name == "example"


def test_session_scope_rolls_back_failed_transaction(tmp_path: Path) -> None:
    database_file = tmp_path / "applications.sqlite3"
    engine = create_sqlite_engine(database_file)
    create_all_tables(engine)
    session_factory = create_session_factory(engine)

    try:
        with session_scope(session_factory) as session:
            applications = ApplicationRepository(session)
            applications.create(profile_name="example")
            raise RuntimeError("forced failure")
    except RuntimeError:
        pass

    with session_factory() as session:
        applications = ApplicationRepository(session)

        assert applications.list_by_profile("example") == []
