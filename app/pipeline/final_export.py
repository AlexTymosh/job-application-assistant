from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.artifacts.resolution import resolve_artifact_path_under_applications_dir
from app.artifacts.writer import ArtifactWriter
from app.core.config import ProjectConfig
from app.core.paths import ProfilePaths
from app.db.models import Application, ApplicationStatus, Artifact
from app.db.repositories import (
    ApplicationEventRepository,
    ApplicationRepository,
    ArtifactRepository,
)
from app.exporters.docx_exporter import DocxExporter
from app.exporters.pdf_exporter import PdfExporter
from app.pipeline.export_markdown_html import TAILORED_CV_MARKDOWN_ARTIFACT_TYPE
from app.pipeline.export_pdf_docx import (
    TAILORED_CV_DOCX_ARTIFACT_TYPE,
    TAILORED_CV_PDF_ARTIFACT_TYPE,
)


@dataclass(frozen=True)
class FinalExportResult:
    application: Application
    pdf_artifact: Artifact
    docx_artifact: Artifact
    created_artifact_count: int


class FinalApplicationExportService:
    """Approve reviewed CV artefacts and generate final PDF/DOCX exports."""

    def __init__(
        self,
        *,
        session: Session,
        config: ProjectConfig,
        profile_paths: ProfilePaths,
    ) -> None:
        self._session = session
        self._config = config
        self._profile_paths = profile_paths
        self._artifact_writer = ArtifactWriter(
            applications_dir=profile_paths.applications_dir
        )

    def approve_and_export_for_application_number(
        self,
        application_number: int,
    ) -> FinalExportResult:
        applications = ApplicationRepository(self._session)
        application = applications.get_by_number_with_related(
            profile_name=self._config.app.profile_name,
            application_number=application_number,
        )
        if application is None:
            raise ValueError("Application not found.")

        if application.artifact_dir_name is None:
            raise ValueError("Application artefact directory name is missing.")

        artifacts_by_type = _first_artifact_by_type(application.artifacts)
        pdf_artifact = artifacts_by_type.get(TAILORED_CV_PDF_ARTIFACT_TYPE)
        docx_artifact = artifacts_by_type.get(TAILORED_CV_DOCX_ARTIFACT_TYPE)

        if application.status == ApplicationStatus.EXPORTED.value:
            if pdf_artifact is None or docx_artifact is None:
                raise ValueError(
                    "Application is marked as exported but final export artefacts "
                    "are incomplete."
                )
            self._ensure_artifact_file_exists(pdf_artifact)
            self._ensure_artifact_file_exists(docx_artifact)
            return FinalExportResult(
                application=application,
                pdf_artifact=pdf_artifact,
                docx_artifact=docx_artifact,
                created_artifact_count=0,
            )

        if application.status == ApplicationStatus.QA_WARNING.value:
            raise ValueError(
                "Application has QA warnings. Review warnings before final export."
            )

        if application.warnings:
            raise ValueError(
                "Application has warnings. Review warnings before final export."
            )

        if application.status != ApplicationStatus.AWAITING_APPROVAL.value:
            raise ValueError(
                "Application is not waiting for human approval. Run the local "
                "pipeline first."
            )

        markdown_artifact = artifacts_by_type.get(TAILORED_CV_MARKDOWN_ARTIFACT_TYPE)
        if markdown_artifact is None:
            raise ValueError("Tailored CV Markdown review artefact is missing.")

        tailored_cv_markdown = self._read_markdown_artifact(markdown_artifact)

        created_artifact_count = 0
        artifacts = ArtifactRepository(self._session)

        if pdf_artifact is None:
            pdf_bytes = PdfExporter().export(
                tailored_cv_markdown,
                title="Tailored CV",
            )
            written_pdf = self._artifact_writer.write_tailored_cv_pdf(
                artifact_dir_name=application.artifact_dir_name,
                pdf_bytes=pdf_bytes,
            )
            pdf_artifact = artifacts.create(
                application_id=application.id,
                artifact_type=TAILORED_CV_PDF_ARTIFACT_TYPE,
                path=written_pdf.relative_path,
            )
            created_artifact_count += 1
        else:
            self._ensure_artifact_file_exists(pdf_artifact)

        if docx_artifact is None:
            docx_bytes = DocxExporter().export(
                tailored_cv_markdown,
                title="Tailored CV",
            )
            written_docx = self._artifact_writer.write_tailored_cv_docx(
                artifact_dir_name=application.artifact_dir_name,
                docx_bytes=docx_bytes,
            )
            docx_artifact = artifacts.create(
                application_id=application.id,
                artifact_type=TAILORED_CV_DOCX_ARTIFACT_TYPE,
                path=written_docx.relative_path,
            )
            created_artifact_count += 1
        else:
            self._ensure_artifact_file_exists(docx_artifact)

        applications.update_status(
            application_id=application.id,
            status=ApplicationStatus.EXPORTED,
        )
        ApplicationEventRepository(self._session).create(
            application_id=application.id,
            event_type="application_final_export_approved",
            message=(
                "Human approval was recorded and final PDF/DOCX exports were generated."
            ),
        )

        refreshed_application = applications.get_by_number_with_related(
            profile_name=self._config.app.profile_name,
            application_number=application_number,
        )
        if refreshed_application is None:
            raise ValueError("Application not found after final export.")

        return FinalExportResult(
            application=refreshed_application,
            pdf_artifact=pdf_artifact,
            docx_artifact=docx_artifact,
            created_artifact_count=created_artifact_count,
        )

    def _read_markdown_artifact(self, artifact: Artifact) -> str:
        artifact_path = resolve_artifact_path_under_applications_dir(
            applications_dir=self._profile_paths.applications_dir,
            stored_relative_path=artifact.path,
        )
        if not artifact_path.is_file():
            raise FileNotFoundError(
                "Tailored CV Markdown review artefact file is missing."
            )

        content = artifact_path.read_text(encoding="utf-8")
        if not content.strip():
            raise ValueError("Tailored CV Markdown review artefact is empty.")

        return content

    def _ensure_artifact_file_exists(self, artifact: Artifact) -> None:
        artifact_path = resolve_artifact_path_under_applications_dir(
            applications_dir=self._profile_paths.applications_dir,
            stored_relative_path=artifact.path,
        )
        if not artifact_path.is_file():
            raise FileNotFoundError(
                f"{artifact.artifact_type} artefact file is missing."
            )


def _first_artifact_by_type(artifacts: list[Artifact]) -> dict[str, Artifact]:
    artifacts_by_type: dict[str, Artifact] = {}
    for artifact in artifacts:
        artifacts_by_type.setdefault(artifact.artifact_type, artifact)
    return artifacts_by_type
