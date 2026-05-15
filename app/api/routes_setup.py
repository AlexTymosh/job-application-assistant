from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.dependencies import get_app_data_root, get_session
from app.setup.service import SetupStatusService
from app.web.templating import templates

router = APIRouter(prefix="/setup", tags=["setup"])


@router.get("")
def setup(request: Request, session: Session = Depends(get_session)):
    status = SetupStatusService(session, get_app_data_root(request), key_available=True).evaluate()
    return templates.TemplateResponse("setup.html", {"request": request, "setup_status": status})
