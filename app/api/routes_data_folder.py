from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import RedirectResponse

router = APIRouter(prefix="/data-folder", tags=["data-folder"])


@router.get("")
def data_folder_redirect():
    return RedirectResponse("/settings?section=data-folder", status_code=303)


@router.post("")
def update_data_folder_redirect():
    return RedirectResponse("/settings?section=data-folder", status_code=303)
