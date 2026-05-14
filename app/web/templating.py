from __future__ import annotations

from pathlib import Path

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=TEMPLATES_DIR)


def render_error_page(
    *, request: Request, status_code: int, message: str
) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="error.html",
        status_code=status_code,
        context={
            "project_name": "Local Job Application Assistant",
            "message": message,
        },
    )
