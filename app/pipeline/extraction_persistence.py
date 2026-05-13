from __future__ import annotations

from uuid import UUID

from app.artifacts.writer import ArtifactWriter
from app.db.models import Artifact
from app.db.repositories import ArtifactRepository
from app.llm.schemas import ExtractedJob

EXTRACTED_JOB_ARTIFACT_TYPE = "extracted_job"


def persist_extracted_job_artifact(
    *,
    artifacts: ArtifactRepository,
    artifact_writer: ArtifactWriter,
    application_id: UUID,
    extracted_job: ExtractedJob,
) -> Artifact:
    """Persist an extracted job JSON artefact and register its relative path."""

    written_artifact = artifact_writer.write_extracted_job(
        application_id=application_id,
        extracted_job_data=extracted_job.model_dump(mode="json"),
    )

    return artifacts.create(
        application_id=application_id,
        artifact_type=EXTRACTED_JOB_ARTIFACT_TYPE,
        path=written_artifact.relative_path,
    )
