from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import select

from app.artifacts.writer import ArtifactWriter
from app.db.models import Artifact
from app.db.repositories import ApplicationRepository, ArtifactRepository
from app.db.session import (
    create_all_tables,
    create_session_factory,
    create_sqlite_engine,
    session_scope,
)
from app.llm.schemas import (
    ExtractedJob,
    JobRequirement,
    RequirementCategory,
    RequirementPriority,
)
from app.pipeline.extraction_persistence import persist_extracted_job_artifact


def build_extracted_job() -> ExtractedJob:
    return ExtractedJob(
        job_title="Backend Developer",
        company_name="Example Company",
        requirements=[
            JobRequirement(
                id="req_python",
                text="Work with Python.",
                priority=RequirementPriority.MUST_HAVE,
                category=RequirementCategory.PROGRAMMING_LANGUAGE,
                keywords=["Python"],
            )
        ],
        technologies=["Python"],
    )


def test_persist_extracted_job_artifact_writes_json_and_database_row(
    tmp_path: Path,
) -> None:
    database_file = tmp_path / "applications.sqlite3"
    applications_dir = tmp_path / "private-profile" / "applications"
    engine = create_sqlite_engine(database_file)
    create_all_tables(engine)
    session_factory = create_session_factory(engine)

    with session_scope(session_factory) as session:
        application = ApplicationRepository(session).create(profile_name="example")
        application_id = application.id
        artifact_dir_name = application.artifact_dir_name
        assert artifact_dir_name is not None
        artifact = persist_extracted_job_artifact(
            artifacts=ArtifactRepository(session),
            artifact_writer=ArtifactWriter(applications_dir=applications_dir),
            application_id=application_id,
            artifact_dir_name=artifact_dir_name,
            extracted_job=build_extracted_job(),
        )

        assert artifact.artifact_type == "extracted_job"
        assert artifact.path == f"applications/{artifact_dir_name}/extracted_job.json"
        assert str(tmp_path) not in artifact.path
        assert not Path(artifact.path).is_absolute()

    extracted_job_path = applications_dir / artifact_dir_name / "extracted_job.json"
    assert extracted_job_path.is_file()

    stored_json = json.loads(extracted_job_path.read_text(encoding="utf-8"))
    assert stored_json["job_title"] == "Backend Developer"
    assert stored_json["company_name"] == "Example Company"
    assert stored_json["requirements"][0]["id"] == "req_python"
    assert stored_json["requirements"][0]["priority"] == "must_have"

    with session_factory() as session:
        stored_artifact = session.scalars(select(Artifact)).one()

        assert stored_artifact.artifact_type == "extracted_job"
        assert (
            stored_artifact.path
            == f"applications/{artifact_dir_name}/extracted_job.json"
        )
        assert str(tmp_path) not in stored_artifact.path
        assert not Path(stored_artifact.path).is_absolute()
