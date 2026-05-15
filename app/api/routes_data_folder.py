from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from app.api.dependencies import read_form_data
from app.storage.location import get_app_data_location_status, set_user_selected_app_data_root
from app.web.templating import templates

router = APIRouter(prefix="/data-folder", tags=["data-folder"])


@router.get("")
def data_folder(request: Request):
    return templates.TemplateResponse("data_folder.html", {"request": request, "status": get_app_data_location_status()})


@router.post("")
async def update_data_folder(request: Request):
    data = await read_form_data(request)
    set_user_selected_app_data_root(Path(data["root"]))
    return RedirectResponse("/data-folder", status_code=303)
