from __future__ import annotations

from fastapi import APIRouter, Request

from app.api.dependencies import SessionDep, get_app_data_root
from app.setup.service import SetupStatusService
from app.web.templating import templates

router = APIRouter(prefix="/setup", tags=["setup"])


@router.get("")
def setup(request: Request, session: SessionDep):
    status = SetupStatusService(
        session, get_app_data_root(request), key_available=True
    ).evaluate()
    return templates.TemplateResponse(
        "setup.html", {"request": request, "setup_status": status}
    )
