from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.setup.checks import SetupStatus
from app.web.templating import templates

router = APIRouter(tags=["setup"])


@router.get("/setup", response_class=HTMLResponse)
async def setup(request: Request) -> HTMLResponse:
    setup_status: SetupStatus = request.app.state.setup_status

    return templates.TemplateResponse(
        request=request,
        name="setup.html",
        context={
            "project_name": "Local Job Application Assistant",
            "setup_status": setup_status,
        },
    )
