from __future__ import annotations

from fastapi import APIRouter, Request
from sqlalchemy import select

from app.api.dependencies import SessionDep
from app.db.models import Application, PersonProfile, Resume
from app.web.templating import templates

router = APIRouter()


@router.get("/")
def dashboard(request: Request, session: SessionDep):
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "profile_count": session.scalar(select(PersonProfile).count())
            if False
            else len(list(session.scalars(select(PersonProfile.id)))),
            "resume_count": len(list(session.scalars(select(Resume.id)))),
            "application_count": len(list(session.scalars(select(Application.id)))),
        },
    )
