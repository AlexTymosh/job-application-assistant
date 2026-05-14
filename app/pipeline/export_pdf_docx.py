from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from app.artifacts.writer import ArtifactWriter, WrittenArtifact
from app.db.models import Artifact
from app.db.repositories import ArtifactRepository
from app.exporters.docx_exporter import DocxExporter
from app.exporters.pdf_exporter import PdfExporter

TAILORED_CV_PDF_ARTIFACT_TYPE = "tailored_cv_pdf"
TAILORED_CV_DOCX_ARTIFACT_TYPE = "tailored_cv_docx"


@dataclass(frozen=True)
class PdfDocxExportResult:
    pdf: WrittenArtifact
    docx: WrittenArtifact
    pdf_artifact: Artifact
    docx_artifact: Artifact


def export_pdf_docx_artifacts(
    *,
    session: Session,
    application_id: UUID,
    artifact_dir_name: str,
    tailored_cv_markdown: str,
    artifact_writer: ArtifactWriter | None = None,
    applications_dir: Path | None = None,
    title: str = "Tailored CV",
) -> PdfDocxExportResult:
    """Export tailored CV PDF and DOCX artefacts through the artefact boundary."""

    if artifact_writer is None:
        if applications_dir is None:
            raise ValueError(
                "Either artifact_writer or applications_dir must be provided."
            )
        artifact_writer = ArtifactWriter(applications_dir=applications_dir)

    pdf_bytes = PdfExporter().export(tailored_cv_markdown, title=title)
    docx_bytes = DocxExporter().export(tailored_cv_markdown, title=title)

    written_pdf = artifact_writer.write_tailored_cv_pdf(
        artifact_dir_name=artifact_dir_name,
        pdf_bytes=pdf_bytes,
    )
    written_docx = artifact_writer.write_tailored_cv_docx(
        artifact_dir_name=artifact_dir_name,
        docx_bytes=docx_bytes,
    )

    artifacts = ArtifactRepository(session)
    pdf_artifact = artifacts.create(
        application_id=application_id,
        artifact_type=TAILORED_CV_PDF_ARTIFACT_TYPE,
        path=written_pdf.relative_path,
    )
    docx_artifact = artifacts.create(
        application_id=application_id,
        artifact_type=TAILORED_CV_DOCX_ARTIFACT_TYPE,
        path=written_docx.relative_path,
    )

    return PdfDocxExportResult(
        pdf=written_pdf,
        docx=written_docx,
        pdf_artifact=pdf_artifact,
        docx_artifact=docx_artifact,
    )
