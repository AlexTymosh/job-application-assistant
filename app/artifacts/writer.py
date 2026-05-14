from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from app.artifacts.paths import (
    build_application_artifact_dir,
    build_evidence_matrix_path,
    build_evidence_matrix_relative_path,
    build_extracted_job_path,
    build_extracted_job_relative_path,
    build_match_report_path,
    build_match_report_relative_path,
    build_raw_job_text_path,
    build_raw_job_text_relative_path,
    build_tailored_cv_docx_path,
    build_tailored_cv_docx_relative_path,
    build_tailored_cv_html_path,
    build_tailored_cv_html_relative_path,
    build_tailored_cv_markdown_path,
    build_tailored_cv_markdown_relative_path,
    build_tailored_cv_pdf_path,
    build_tailored_cv_pdf_relative_path,
)


@dataclass(frozen=True)
class WrittenArtifact:
    absolute_path: Path
    relative_path: str


class ArtifactWriter:
    def __init__(self, *, applications_dir: Path) -> None:
        self._applications_dir = applications_dir

    def create_application_dir(self, *, artifact_dir_name: str) -> Path:
        application_dir = build_application_artifact_dir(
            applications_dir=self._applications_dir,
            artifact_dir_name=artifact_dir_name,
        )
        application_dir.mkdir(parents=True, exist_ok=True)
        return application_dir

    def write_raw_job_text(
        self,
        *,
        artifact_dir_name: str,
        raw_text: str,
    ) -> WrittenArtifact:
        self.create_application_dir(artifact_dir_name=artifact_dir_name)
        absolute_path = build_raw_job_text_path(
            applications_dir=self._applications_dir,
            artifact_dir_name=artifact_dir_name,
        )
        absolute_path.write_text(raw_text, encoding="utf-8")

        return WrittenArtifact(
            absolute_path=absolute_path,
            relative_path=build_raw_job_text_relative_path(
                artifact_dir_name=artifact_dir_name,
            ),
        )

    def write_extracted_job(
        self,
        *,
        artifact_dir_name: str,
        extracted_job_data: dict[str, object],
    ) -> WrittenArtifact:
        self.create_application_dir(artifact_dir_name=artifact_dir_name)
        absolute_path = build_extracted_job_path(
            applications_dir=self._applications_dir,
            artifact_dir_name=artifact_dir_name,
        )
        absolute_path.write_text(
            json.dumps(extracted_job_data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        return WrittenArtifact(
            absolute_path=absolute_path,
            relative_path=build_extracted_job_relative_path(
                artifact_dir_name=artifact_dir_name,
            ),
        )

    def write_tailored_cv_markdown(
        self,
        *,
        artifact_dir_name: str,
        markdown: str,
    ) -> WrittenArtifact:
        self.create_application_dir(artifact_dir_name=artifact_dir_name)
        absolute_path = build_tailored_cv_markdown_path(
            applications_dir=self._applications_dir,
            artifact_dir_name=artifact_dir_name,
        )
        absolute_path.write_text(_ensure_final_newline(markdown), encoding="utf-8")

        return WrittenArtifact(
            absolute_path=absolute_path,
            relative_path=build_tailored_cv_markdown_relative_path(
                artifact_dir_name=artifact_dir_name,
            ),
        )

    def write_tailored_cv_html(
        self,
        *,
        artifact_dir_name: str,
        html: str,
    ) -> WrittenArtifact:
        self.create_application_dir(artifact_dir_name=artifact_dir_name)
        absolute_path = build_tailored_cv_html_path(
            applications_dir=self._applications_dir,
            artifact_dir_name=artifact_dir_name,
        )
        absolute_path.write_text(_ensure_final_newline(html), encoding="utf-8")

        return WrittenArtifact(
            absolute_path=absolute_path,
            relative_path=build_tailored_cv_html_relative_path(
                artifact_dir_name=artifact_dir_name,
            ),
        )

    def write_tailored_cv_pdf(
        self,
        *,
        artifact_dir_name: str,
        pdf_bytes: bytes,
    ) -> WrittenArtifact:
        self.create_application_dir(artifact_dir_name=artifact_dir_name)
        absolute_path = build_tailored_cv_pdf_path(
            applications_dir=self._applications_dir,
            artifact_dir_name=artifact_dir_name,
        )
        absolute_path.write_bytes(pdf_bytes)

        return WrittenArtifact(
            absolute_path=absolute_path,
            relative_path=build_tailored_cv_pdf_relative_path(
                artifact_dir_name=artifact_dir_name,
            ),
        )

    def write_tailored_cv_docx(
        self,
        *,
        artifact_dir_name: str,
        docx_bytes: bytes,
    ) -> WrittenArtifact:
        self.create_application_dir(artifact_dir_name=artifact_dir_name)
        absolute_path = build_tailored_cv_docx_path(
            applications_dir=self._applications_dir,
            artifact_dir_name=artifact_dir_name,
        )
        absolute_path.write_bytes(docx_bytes)

        return WrittenArtifact(
            absolute_path=absolute_path,
            relative_path=build_tailored_cv_docx_relative_path(
                artifact_dir_name=artifact_dir_name,
            ),
        )

    def write_evidence_matrix(
        self,
        *,
        artifact_dir_name: str,
        evidence_matrix_data: list[dict[str, object]],
    ) -> WrittenArtifact:
        self.create_application_dir(artifact_dir_name=artifact_dir_name)
        absolute_path = build_evidence_matrix_path(
            applications_dir=self._applications_dir,
            artifact_dir_name=artifact_dir_name,
        )
        absolute_path.write_text(
            json.dumps(evidence_matrix_data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        return WrittenArtifact(
            absolute_path=absolute_path,
            relative_path=build_evidence_matrix_relative_path(
                artifact_dir_name=artifact_dir_name,
            ),
        )

    def write_match_report(
        self,
        *,
        artifact_dir_name: str,
        match_report_data: dict[str, object],
    ) -> WrittenArtifact:
        self.create_application_dir(artifact_dir_name=artifact_dir_name)
        absolute_path = build_match_report_path(
            applications_dir=self._applications_dir,
            artifact_dir_name=artifact_dir_name,
        )
        absolute_path.write_text(
            json.dumps(match_report_data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        return WrittenArtifact(
            absolute_path=absolute_path,
            relative_path=build_match_report_relative_path(
                artifact_dir_name=artifact_dir_name,
            ),
        )


def _ensure_final_newline(content: str) -> str:
    if content.endswith("\n"):
        return content
    return f"{content}\n"
