from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from app.artifacts.writer import ArtifactWriter, WrittenArtifact
from app.db.models import Artifact
from app.db.repositories import ArtifactRepository
from app.exporters.html_exporter import HtmlExporter
from app.exporters.markdown_exporter import MarkdownExporter

TAILORED_CV_MARKDOWN_ARTIFACT_TYPE = "tailored_cv_markdown"
TAILORED_CV_HTML_ARTIFACT_TYPE = "tailored_cv_html"


@dataclass(frozen=True)
class MarkdownHtmlExportResult:
    markdown: WrittenArtifact
    html: WrittenArtifact
    markdown_artifact: Artifact
    html_artifact: Artifact


def export_markdown_html_artifacts(
    *,
    session: Session,
    application_id: UUID,
    tailored_cv_markdown: str,
    artifact_writer: ArtifactWriter | None = None,
    applications_dir: Path | None = None,
    title: str = "Tailored CV",
) -> MarkdownHtmlExportResult:
    """Export tailored CV Markdown and HTML artefacts through the artefact boundary."""

    if artifact_writer is None:
        if applications_dir is None:
            raise ValueError(
                "Either artifact_writer or applications_dir must be provided."
            )
        artifact_writer = ArtifactWriter(applications_dir=applications_dir)

    markdown_content = MarkdownExporter().export(tailored_cv_markdown)
    html_content = HtmlExporter().export(markdown_content, title=title)

    written_markdown = artifact_writer.write_tailored_cv_markdown(
        application_id=application_id,
        markdown=markdown_content,
    )
    written_html = artifact_writer.write_tailored_cv_html(
        application_id=application_id,
        html=html_content,
    )

    artifacts = ArtifactRepository(session)
    markdown_artifact = artifacts.create(
        application_id=application_id,
        artifact_type=TAILORED_CV_MARKDOWN_ARTIFACT_TYPE,
        path=written_markdown.relative_path,
    )
    html_artifact = artifacts.create(
        application_id=application_id,
        artifact_type=TAILORED_CV_HTML_ARTIFACT_TYPE,
        path=written_html.relative_path,
    )

    return MarkdownHtmlExportResult(
        markdown=written_markdown,
        html=written_html,
        markdown_artifact=markdown_artifact,
        html_artifact=html_artifact,
    )
