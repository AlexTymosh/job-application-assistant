from pathlib import Path

from sqlalchemy import select

from app.artifacts.writer import ArtifactWriter
from app.db.models import Artifact
from app.db.repositories import (
    ApplicationEventRepository,
    ApplicationRepository,
    ArtifactRepository,
)
from app.db.session import (
    create_all_tables,
    create_session_factory,
    create_sqlite_engine,
)
from app.jobs.input_models import JobInput
from app.jobs.service import JobInputService


def test_job_input_service_creates_application_raw_text_artifact_and_event(
    tmp_path: Path,
) -> None:
    database_file = tmp_path / "applications.sqlite3"
    applications_dir = tmp_path / "applications"

    engine = create_sqlite_engine(database_file)
    create_all_tables(engine)
    session_factory = create_session_factory(engine)

    manual_text = "Senior Python developer role with FastAPI and SQL. " * 10

    with session_factory() as session:
        applications = ApplicationRepository(session)
        artifacts = ArtifactRepository(session)
        events = ApplicationEventRepository(session)

        service = JobInputService(
            applications=applications,
            artifacts=artifacts,
            events=events,
            artifact_writer=ArtifactWriter(applications_dir=applications_dir),
        )

        application = service.create_from_input(
            profile_name="example",
            selected_cv_variant="backend_developer",
            job_input=JobInput.model_validate(
                {
                    "source_url": "https://Example.com/jobs/123?utm_source=test",
                    "manual_text": manual_text,
                }
            ),
        )

        session.commit()
        application_id = application.id

    application_dir = applications_dir / str(application_id)
    raw_job_path = application_dir / "job_raw.txt"

    assert raw_job_path.is_file()
    assert raw_job_path.read_text(encoding="utf-8") == manual_text

    with session_factory() as session:
        applications = ApplicationRepository(session)
        stored_application = applications.get(application_id)

        assert stored_application is not None
        assert stored_application.profile_name == "example"
        assert stored_application.selected_cv_variant == "backend_developer"
        assert stored_application.job_text_hash is not None
        assert stored_application.normalized_url == "https://example.com/jobs/123"

        artifact = session.scalars(select(Artifact)).one()

        assert artifact.artifact_type == "job_raw"
        assert artifact.path == f"applications/{application_id}/job_raw.txt"
        assert str(tmp_path) not in artifact.path
