from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.artifacts.resolution import resolve_artifact_path_under_applications_dir
from app.artifacts.writer import ArtifactWriter
from app.core.config import ProjectConfig
from app.core.paths import ProfilePaths
from app.db.models import Application, ApplicationStatus, WarningLevel
from app.db.repositories import (
    ApplicationEventRepository,
    ApplicationRepository,
    ApplicationWarningRepository,
    ArtifactRepository,
)
from app.llm.factory import build_job_extraction_client
from app.llm.fake_tailor import FakeCvTailoringClient
from app.pipeline.cv_source import PipelineCvSourceLoader
from app.pipeline.cv_tailoring import CvTailoringStep
from app.pipeline.export_markdown_html import export_markdown_html_artifacts
from app.pipeline.export_pdf_docx import export_pdf_docx_artifacts
from app.pipeline.extraction_persistence import persist_extracted_job_artifact
from app.pipeline.job_extraction import JobExtractionStep
from app.pipeline.state import ApplicationRunState
from app.reports.evidence_matrix import build_evidence_matrix
from app.reports.match_report import build_cv_match_report
from app.secrets.openai_key import OpenAISecretService
from app.storage.app_dirs import AppDataPaths

EVIDENCE_MATRIX_ARTIFACT_TYPE = "evidence_matrix"
MATCH_REPORT_ARTIFACT_TYPE = "match_report"
_PIPELINE_TERMINAL_STATUSES = frozenset(
    {
        ApplicationStatus.AWAITING_APPROVAL.value,
        ApplicationStatus.QA_WARNING.value,
        ApplicationStatus.EXPORTED.value,
    }
)


@dataclass(frozen=True)
class LocalPipelineResult:
    application: Application
    artifact_count: int


class LocalApplicationPipelineService:
    """Run the local release pipeline for one stored application."""

    def __init__(
        self,
        *,
        session: Session,
        config: ProjectConfig,
        profile_paths: ProfilePaths,
        openai_secret_service: OpenAISecretService | None = None,
        app_data_paths: AppDataPaths | None = None,
    ) -> None:
        self._session = session
        self._config = config
        self._profile_paths = profile_paths
        self._openai_secret_service = openai_secret_service
        self._app_data_paths = app_data_paths
        self._artifact_writer = ArtifactWriter(
            applications_dir=profile_paths.applications_dir
        )

    def run_for_application_number(
        self, application_number: int
    ) -> LocalPipelineResult:
        applications = ApplicationRepository(self._session)
        application = applications.get_by_number_with_related(
            profile_name=self._config.app.profile_name,
            application_number=application_number,
        )
        if application is None:
            raise ValueError("Application not found.")

        if application.status in _PIPELINE_TERMINAL_STATUSES:
            raise ValueError(
                "Local pipeline has already generated review or export artefacts for "
                "this application. Re-running is not supported yet."
            )

        if application.artifact_dir_name is None:
            raise ValueError("Application artefact directory name is missing.")

        persisted_warning_exists = bool(application.warnings)
        manual_job_text = self._read_raw_job_text(application)
        selected_variant = (
            application.selected_cv_variant or self._config.cv.default_variant
        )
        state = ApplicationRunState(
            application_id=str(application.id),
            profile_name=application.profile_name,
            selected_cv_variant=selected_variant,
            input_url=application.source_url,
            manual_job_text=manual_job_text,
            job_text_hash=application.job_text_hash,
        )

        extraction_client = build_job_extraction_client(
            self._config,
            openai_secret_service=self._openai_secret_service,
        )
        state = JobExtractionStep(extraction_client).run(state)
        if state.extracted_job is None:
            raise ValueError("Job extraction did not produce a structured job.")

        artifacts = ArtifactRepository(self._session)
        events = ApplicationEventRepository(self._session)

        persist_extracted_job_artifact(
            artifacts=artifacts,
            artifact_writer=self._artifact_writer,
            application_id=application.id,
            artifact_dir_name=application.artifact_dir_name,
            extracted_job=state.extracted_job,
        )
        application.job_title = state.extracted_job.job_title or application.job_title
        application.company_name = (
            state.extracted_job.company_name or application.company_name
        )
        applications.update_status(
            application_id=application.id,
            status=ApplicationStatus.JOB_EXTRACTED,
        )
        events.create(
            application_id=application.id,
            event_type="pipeline_job_extracted",
            message="Job requirements were extracted by the configured local pipeline.",
        )

        cv_source = PipelineCvSourceLoader(
            config=self._config,
            profile_paths=self._profile_paths,
            app_data_paths=self._app_data_paths,
        ).load(selected_variant=selected_variant)
        events.create(
            application_id=application.id,
            event_type="pipeline_cv_source_loaded",
            message=cv_source.metadata.message,
        )
        state = CvTailoringStep(FakeCvTailoringClient()).run(
            state,
            loaded_cv=cv_source.loaded_cv,
            fact_bank=cv_source.fact_bank,
        )
        tailoring_status = (
            ApplicationStatus.TAILORED
            if state.status == ApplicationStatus.TAILORED.value
            else ApplicationStatus.QA_WARNING
        )
        applications.update_status(
            application_id=application.id,
            status=tailoring_status,
        )
        events.create(
            application_id=application.id,
            event_type="pipeline_cv_tailored",
            message="Safe fake CV tailoring completed using verified fact-bank data.",
        )

        evidence_matrix = build_evidence_matrix(
            state.extracted_job, cv_source.fact_bank
        )
        match_report = build_cv_match_report(
            str(application.id),
            state.extracted_job,
            cv_source.fact_bank,
            evidence_matrix,
        )
        match_report_missing_skills_exists = bool(match_report.missing_skills)

        self._persist_qa_warning_reasons(
            application=application,
            state=state,
            match_report_missing_skills_exists=match_report_missing_skills_exists,
        )

        state = state.model_copy(
            update={
                "evidence_matrix": evidence_matrix,
                "match_report": match_report,
            }
        )

        written_evidence = self._artifact_writer.write_evidence_matrix(
            artifact_dir_name=application.artifact_dir_name,
            evidence_matrix_data=[
                item.model_dump(mode="json") for item in evidence_matrix
            ],
        )
        artifacts.create(
            application_id=application.id,
            artifact_type=EVIDENCE_MATRIX_ARTIFACT_TYPE,
            path=written_evidence.relative_path,
        )
        written_report = self._artifact_writer.write_match_report(
            artifact_dir_name=application.artifact_dir_name,
            match_report_data=match_report.model_dump(mode="json"),
        )
        artifacts.create(
            application_id=application.id,
            artifact_type=MATCH_REPORT_ARTIFACT_TYPE,
            path=written_report.relative_path,
        )
        events.create(
            application_id=application.id,
            event_type="pipeline_reports_generated",
            message="Evidence Matrix and CV Match Report artefacts were generated.",
        )

        if state.tailored_cv_markdown is None:
            raise ValueError("Tailoring did not produce Markdown for export.")

        export_markdown_html_artifacts(
            session=self._session,
            application_id=application.id,
            artifact_dir_name=application.artifact_dir_name,
            tailored_cv_markdown=state.tailored_cv_markdown,
            artifact_writer=self._artifact_writer,
        )
        if self._config.workflow.require_human_approval_before_export:
            review_status = self._status_before_final_export(
                state=state,
                match_report_missing_skills_exists=match_report_missing_skills_exists,
                persisted_application_warning_exists=persisted_warning_exists,
            )
            applications.update_status(
                application_id=application.id,
                status=review_status,
            )
            events.create(
                application_id=application.id,
                event_type="pipeline_review_artifacts_generated",
                message=(
                    "Markdown and HTML review artefacts were generated. "
                    "Final PDF and DOCX exports are waiting for human approval."
                ),
            )
        else:
            export_pdf_docx_artifacts(
                session=self._session,
                application_id=application.id,
                artifact_dir_name=application.artifact_dir_name,
                tailored_cv_markdown=state.tailored_cv_markdown,
                artifact_writer=self._artifact_writer,
            )
            applications.update_status(
                application_id=application.id,
                status=ApplicationStatus.EXPORTED,
            )
            events.create(
                application_id=application.id,
                event_type="pipeline_exports_generated",
                message="Markdown, HTML, PDF, and DOCX CV artefacts were generated.",
            )

        self._session.flush()
        refreshed_application = applications.get_by_number_with_related(
            profile_name=self._config.app.profile_name,
            application_number=application_number,
        )
        if refreshed_application is None:
            raise ValueError("Application not found after pipeline run.")

        return LocalPipelineResult(
            application=refreshed_application,
            artifact_count=len(refreshed_application.artifacts),
        )

    def _status_before_final_export(
        self,
        *,
        state: ApplicationRunState,
        match_report_missing_skills_exists: bool,
        persisted_application_warning_exists: bool,
    ) -> ApplicationStatus:
        warning_exists = bool(
            persisted_application_warning_exists
            or state.warning_codes
            or state.tailoring_warning_codes
            or match_report_missing_skills_exists
        )
        if warning_exists:
            return ApplicationStatus.QA_WARNING

        return ApplicationStatus.AWAITING_APPROVAL

    def _read_raw_job_text(self, application: Application) -> str:
        raw_artifact = next(
            (
                artifact
                for artifact in application.artifacts
                if artifact.artifact_type == "job_raw"
            ),
            None,
        )
        if raw_artifact is None:
            raise ValueError("Raw job text artefact is missing.")

        raw_path = resolve_artifact_path_under_applications_dir(
            applications_dir=self._profile_paths.applications_dir,
            stored_relative_path=raw_artifact.path,
        )
        if not raw_path.is_file():
            raise FileNotFoundError("Raw job text artefact file is missing.")

        raw_text = raw_path.read_text(encoding="utf-8")
        if not raw_text.strip():
            raise ValueError("Raw job text artefact is empty.")

        return raw_text

    def _persist_qa_warning_reasons(
        self,
        *,
        application: Application,
        state: ApplicationRunState,
        match_report_missing_skills_exists: bool,
    ) -> None:
        warnings = ApplicationWarningRepository(self._session)
        existing_codes = {warning.code for warning in application.warnings}

        def create_once(code: str, message: str) -> None:
            if code in existing_codes:
                return

            warnings.create(
                application_id=application.id,
                code=code,
                message=message,
                level=WarningLevel.WARNING,
            )
            existing_codes.add(code)

        if state.warning_codes:
            warning_codes = ", ".join(sorted(set(state.warning_codes)))
            create_once(
                code="pipeline_warning",
                message=f"Pipeline warnings detected: {warning_codes}.",
            )

        if state.tailoring_warning_codes:
            warning_codes = ", ".join(sorted(set(state.tailoring_warning_codes)))
            create_once(
                code="tailoring_warning",
                message=(
                    "CV tailoring produced warnings: "
                    f"{warning_codes}. Review tailored_cv.md before approval."
                ),
            )

        if match_report_missing_skills_exists:
            create_once(
                code="match_report_missing_skills",
                message=(
                    "CV Match Report found missing skills or uncovered requirements. "
                    "Review match_report.json and evidence_matrix.json before approval."
                ),
            )
