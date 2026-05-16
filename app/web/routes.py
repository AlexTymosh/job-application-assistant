from __future__ import annotations

from fastapi import APIRouter, Request

from app.api.dependencies import SessionDep
from app.applications.service import ApplicationService
from app.settings.service import SettingsService
from app.web.templating import templates

router = APIRouter()


@router.get("/")
def dashboard(request: Request, session: SessionDep):
    settings = SettingsService(session)
    active_profile = settings.get_active_profile()
    stats = None
    if active_profile is not None:
        stats = ApplicationService(session).dashboard_stats(active_profile.id)
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "active_profile": active_profile,
            "stats": stats,
            "profiles": settings.list_profiles(),
        },
    )
