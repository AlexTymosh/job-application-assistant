from __future__ import annotations

from typing import Annotated
from urllib.parse import parse_qs

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.api.dependencies import get_session
from app.core.config import ProjectConfig
from app.core.paths import ProfilePaths
from app.db.repositories import ApplicationRepository
from app.jobs.input_models import JobInput
from app.pipeline.intake import ApplicationIntakeService
from app.web.templating import render_error_page, templates

router = APIRouter(tags=["applications"])


def _empty_to_none(value: str | None) -> str | None:
    if value is None:
        return None

    stripped_value = value.strip()
    return stripped_value or None


@router.get("/applications/new", response_class=HTMLResponse)
async def new_application(request: Request) -> HTMLResponse:
    config: ProjectConfig = request.app.state.config

    return templates.TemplateResponse(
        request=request,
        name="applications_new.html",
        context={
            "project_name": "Local Job Application Assistant",
            "default_cv_variant": config.cv.default_variant,
            "cv_variants": config.cv.variants,
            "form_values": {},
            "errors": [],
        },
    )


@router.post("/applications", response_class=HTMLResponse)
async def create_application(
    request: Request,
    session: Annotated[Session, Depends(get_session)],
) -> Response:
    config: ProjectConfig = request.app.state.config
    profile_paths: ProfilePaths = request.app.state.profile_paths
    form_data = parse_qs((await request.body()).decode(), keep_blank_values=True)
    manual_text = form_data.get("manual_text", [""])[0]
    source_url = form_data.get("source_url", [None])[0]
    selected_cv_variant = form_data.get("selected_cv_variant", [None])[0]
    selected_variant = _empty_to_none(selected_cv_variant) or config.cv.default_variant

    try:
        job_input = JobInput(
            manual_text=manual_text,
            source_url=_empty_to_none(source_url),
        )
    except ValidationError as exc:
        return templates.TemplateResponse(
            request=request,
            name="applications_new.html",
            status_code=status.HTTP_400_BAD_REQUEST,
            context={
                "project_name": "Local Job Application Assistant",
                "default_cv_variant": config.cv.default_variant,
                "cv_variants": config.cv.variants,
                "form_values": {
                    "manual_text": manual_text,
                    "source_url": source_url or "",
                    "selected_cv_variant": selected_variant,
                },
                "errors": [error["msg"] for error in exc.errors()],
            },
        )

    intake_service = ApplicationIntakeService(
        session=session,
        blacklist_path=profile_paths.blacklist_file,
        applications_dir=profile_paths.applications_dir,
    )
    result = intake_service.create_application_from_job_input(
        profile_name=config.app.profile_name,
        selected_cv_variant=selected_variant,
        job_input=job_input,
    )

    return RedirectResponse(
        url=f"/applications/{result.application.application_number}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/applications/{application_number}", response_class=HTMLResponse)
async def application_detail(
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

    return templates.TemplateResponse(
        request=request,
        name="applications_detail.html",
        context={
            "project_name": "Local Job Application Assistant",
            "application": application,
            "warnings": application.warnings,
            "events": application.events,
            "artifacts": application.artifacts,
            "has_job_text_hash": application.job_text_hash is not None,
        },
    )
