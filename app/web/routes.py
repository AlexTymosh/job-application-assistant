from __future__ import annotations

from fastapi import APIRouter, Request

from app.api.dependencies import SessionDep
from app.applications.service import ApplicationService
from app.resumes.service import ResumeService
from app.settings.service import SettingsService
from app.web.templating import templates

router = APIRouter()


@router.get("/")
def dashboard(request: Request, session: SessionDep):
    settings = SettingsService(session)
    active_profile = settings.get_active_profile()
    stats = None
    days = _normalise_dashboard_days(request.query_params.get("days"))
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
            "selected_days": days,
            "allowed_days": [10, 20, 30],
        },
    )


def _normalise_dashboard_days(raw_days: str | None) -> int:
    try:
        days = int(raw_days or "30")
    except ValueError:
        return 30
    return days if days in {10, 20, 30} else 30


@router.get("/cv-builder")
def cv_builder(request: Request, session: SessionDep):
    settings = SettingsService(session)
    active_profile = settings.get_active_profile()
    resumes = []
    selected_resume = None
    if active_profile is not None:
        resumes = ResumeService(session).list_resumes(active_profile.id)
        requested_resume_id = request.query_params.get("resume_id")
        if requested_resume_id:
            try:
                requested_id = int(requested_resume_id)
            except ValueError:
                requested_id = None
            selected_resume = next(
                (resume for resume in resumes if resume.id == requested_id),
                None,
            )
        selected_resume = selected_resume or (resumes[0] if resumes else None)
        if selected_resume is not None:
            selected_resume = ResumeService(session).get_resume(selected_resume.id)
    return templates.TemplateResponse(
        "cv_builder.html",
        {
            "request": request,
            "active_profile": active_profile,
            "resumes": resumes,
            "resume": selected_resume,
        },
    )
