from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.api.dependencies import get_session
from app.core.config import ProjectConfig
from app.db.repositories import ApplicationRepository
from app.web.templates import templates

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    session: Annotated[Session, Depends(get_session)],
) -> HTMLResponse:
    config: ProjectConfig = request.app.state.config
    applications = ApplicationRepository(session).list_dashboard_by_profile(
        config.app.profile_name
    )

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "project_name": "Local Job Application Assistant",
            "applications": applications,
        },
    )
