from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.core.config import ProjectConfig

router = APIRouter(tags=["web"])
templates = Jinja2Templates(directory="app/web/templates")


@router.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    config: ProjectConfig = request.app.state.config

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "profile_name": config.app.profile_name,
            "project_name": "Local Job Application Assistant",
        },
    )
