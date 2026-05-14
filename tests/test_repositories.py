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


def test_application_numbers_are_sequential_per_profile(tmp_path: Path) -> None:
    database_file = tmp_path / "applications.sqlite3"
    engine = create_sqlite_engine(database_file)
    create_all_tables(engine)
    session_factory = create_session_factory(engine)

    with session_factory() as session:
        applications = ApplicationRepository(session)
        first_example = applications.create(profile_name="example")
        second_example = applications.create(profile_name="example")
        first_other = applications.create(profile_name="other")
        session.commit()

        assert first_example.application_number == 1
        assert first_example.display_number == "APP-000001"
        assert second_example.application_number == 2
        assert second_example.display_number == "APP-000002"
        assert first_other.application_number == 1
        assert first_other.display_number == "APP-000001"


def test_application_repository_fetches_by_profile_number_and_uuid(
    tmp_path: Path,
) -> None:
    database_file = tmp_path / "applications.sqlite3"
    engine = create_sqlite_engine(database_file)
    create_all_tables(engine)
    session_factory = create_session_factory(engine)

    with session_factory() as session:
        applications = ApplicationRepository(session)
        application = applications.create(profile_name="example")
        application_id = application.id
        session.commit()

    with session_factory() as session:
        applications = ApplicationRepository(session)
        by_number = applications.get_by_number(
            profile_name="example",
            application_number=1,
        )
        by_uuid = applications.get(application_id)

        assert by_number is not None
        assert by_number.id == application_id
        assert by_uuid is not None
        assert by_uuid.application_number == 1
        assert (
            applications.get_by_number(
                profile_name="other",
                application_number=1,
            )
            is None
        )
