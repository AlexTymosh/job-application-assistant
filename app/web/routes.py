from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.core.config import ProjectConfig

router = APIRouter(tags=["web"])
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=TEMPLATES_DIR)


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
