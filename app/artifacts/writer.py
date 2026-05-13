from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from app.artifacts.paths import (
    build_application_artifact_dir,
    build_raw_job_text_path,
    build_raw_job_text_relative_path,
)


@dataclass(frozen=True)
class WrittenArtifact:
    absolute_path: Path
    relative_path: str


class ArtifactWriter:
    def __init__(self, *, applications_dir: Path) -> None:
        self._applications_dir = applications_dir

    def create_application_dir(self, *, application_id: UUID) -> Path:
        application_dir = build_application_artifact_dir(
            applications_dir=self._applications_dir,
            application_id=application_id,
        )
        application_dir.mkdir(parents=True, exist_ok=True)
        return application_dir

    def write_raw_job_text(
        self,
        *,
        application_id: UUID,
        raw_text: str,
    ) -> WrittenArtifact:
        self.create_application_dir(application_id=application_id)
        absolute_path = build_raw_job_text_path(
            applications_dir=self._applications_dir,
            application_id=application_id,
        )
        absolute_path.write_text(raw_text, encoding="utf-8")

        return WrittenArtifact(
            absolute_path=absolute_path,
            relative_path=build_raw_job_text_relative_path(
                application_id=application_id,
            ),
        )
