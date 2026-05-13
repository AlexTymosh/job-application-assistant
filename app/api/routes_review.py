from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.api.dependencies import get_session
from app.db.repositories import ApplicationRepository
from app.web.templates import templates

router = APIRouter(tags=["review"])


@router.get("/applications/{application_id}/review", response_class=HTMLResponse)
async def review_application(
    request: Request,
    application_id: UUID,
    session: Annotated[Session, Depends(get_session)],
) -> HTMLResponse:
    application = ApplicationRepository(session).get_with_related(application_id)

    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    artifacts_by_type = {
        artifact.artifact_type: artifact for artifact in application.artifacts
    }

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
            "tailored_cv_artifact": artifacts_by_type.get("tailored_cv"),
            "match_report_artifact": artifacts_by_type.get("match_report"),
        },
    )
