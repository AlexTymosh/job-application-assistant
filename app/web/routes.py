from __future__ import annotations

from fastapi import APIRouter, Request

from app.api.dependencies import SessionDep
from app.applications.service import ApplicationService
from app.resumes.service import ResumeService
from app.settings.service import SettingsService
from app.web.templating import templates

router = APIRouter()


@router.get("/")
def dashboard(request: Request, session: SessionDep, days: int = 30):
    settings = SettingsService(session)
    active_profile = settings.get_active_profile()
    stats = None
    if active_profile is not None:
        stats = ApplicationService(session).dashboard_stats(
            active_profile.id, days=days
        )
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "active_profile": active_profile,
            "stats": stats,
            "profiles": settings.list_profiles(),
        },
    )


@router.get("/cv-builder")
def cv_builder(request: Request, session: SessionDep, resume_id: int | None = None):
    settings = SettingsService(session)
    active_profile = settings.get_active_profile()
    resumes = []
    selected_resume = None
    if active_profile is not None:
        service = ResumeService(session)
        resumes = service.list_resumes(active_profile.id)
        if resumes:
            selected_id = resume_id or resumes[0].id
            selected_resume = next(
                (resume for resume in resumes if resume.id == selected_id), None
            )
            if selected_resume is None:
                selected_resume = resumes[0]
    return templates.TemplateResponse(
        "cv_builder.html",
        {
            "request": request,
            "active_profile": active_profile,
            "resumes": resumes,
            "resume": selected_resume,
        },
    )
