from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_session
from app.db.models import Application, PersonProfile, Resume
from app.web.templating import templates

router = APIRouter()


@router.get("/")
def dashboard(request: Request, session: Session = Depends(get_session)):
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "profile_count": session.scalar(select(PersonProfile).count()) if False else len(list(session.scalars(select(PersonProfile.id)))),
            "resume_count": len(list(session.scalars(select(Resume.id)))),
            "application_count": len(list(session.scalars(select(Application.id)))),
        },
    )
