from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy.orm import Session

from app.api.dependencies import get_session
from app.core.config import ProjectConfig
from app.core.paths import ProfilePaths
from app.db.repositories import ApplicationRepository
from app.pipeline.final_export import FinalApplicationExportService
from app.web.templating import render_error_page, templates

router = APIRouter(tags=["review"])


@router.get("/applications/{application_number}/review", response_class=HTMLResponse)
async def review_application(
    request: Request,
    application_number: int,
    session: Annotated[Session, Depends(get_session)],
) -> HTMLResponse:
    config: ProjectConfig = request.app.state.config
    application = ApplicationRepository(session).get_by_number_with_related(
        profile_name=config.app.profile_name,
        application_number=application_number,
    )

    if application is None:
        return render_error_page(
            request=request,
            status_code=status.HTTP_404_NOT_FOUND,
            message="Application not found.",
        )

    artifacts_by_type = {
        artifact.artifact_type: artifact for artifact in application.artifacts
    }
    final_export_ready = bool(
        artifacts_by_type.get("tailored_cv_pdf")
        and artifacts_by_type.get("tailored_cv_docx")
    )

    changed_cv_artifacts = [
        artifact
        for artifact in application.artifacts
        if artifact.artifact_type
        in {
            "tailored_cv_markdown",
            "tailored_cv_html",
            "tailored_cv_pdf",
            "tailored_cv_docx",
        }
    ]

    return templates.TemplateResponse(
        request=request,
        name="review.html",
        context={
            "project_name": "Local Job Application Assistant",
            "application": application,
            "warnings": application.warnings,
            "events": application.events,
            "artifacts": application.artifacts,
            "extracted_job_artifact": artifacts_by_type.get("extracted_job"),
            "tailored_cv_artifact": artifacts_by_type.get("tailored_cv_markdown"),
            "tailored_cv_markdown_artifact": artifacts_by_type.get(
                "tailored_cv_markdown"
            ),
            "tailored_cv_html_artifact": artifacts_by_type.get("tailored_cv_html"),
            "tailored_cv_pdf_artifact": artifacts_by_type.get("tailored_cv_pdf"),
            "tailored_cv_docx_artifact": artifacts_by_type.get("tailored_cv_docx"),
            "changed_cv_artifacts": changed_cv_artifacts,
            "match_report_artifact": artifacts_by_type.get("match_report"),
            "final_export_ready": final_export_ready,
            "approval_required": config.workflow.require_human_approval_before_export,
        },
    )


@router.post("/applications/{application_number}/approve-and-export")
async def approve_and_export_application(
    request: Request,
    application_number: int,
    session: Annotated[Session, Depends(get_session)],
) -> Response:
    config: ProjectConfig = request.app.state.config
    profile_paths: ProfilePaths = request.app.state.profile_paths
    service = FinalApplicationExportService(
        session=session,
        config=config,
        profile_paths=profile_paths,
    )

    try:
        service.approve_and_export_for_application_number(application_number)
    except FileNotFoundError as exc:
        return render_error_page(
            request=request,
            status_code=status.HTTP_404_NOT_FOUND,
            message=str(exc),
        )
    except ValueError as exc:
        return render_error_page(
            request=request,
            status_code=status.HTTP_400_BAD_REQUEST,
            message=str(exc),
        )

    session.commit()

    return RedirectResponse(
        url=f"/applications/{application_number}/review",
        status_code=status.HTTP_303_SEE_OTHER,
    )
