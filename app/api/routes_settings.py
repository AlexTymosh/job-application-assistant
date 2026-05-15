from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api.dependencies import form_bool, get_session, read_form_data
from app.settings.service import SettingsService
from app.web.templating import templates

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("")
def settings_page(request: Request, session: Session = Depends(get_session)):
    settings = SettingsService(session).effective()
    secret_service = request.app.state.openai_secret_service
    try:
        key_status = "configured" if secret_service.get_api_key() else "not configured"
    except Exception:
        key_status = "unavailable"
    return templates.TemplateResponse(
        "settings.html",
        {"request": request, "settings": settings, "key_status": key_status},
    )


@router.post("")
async def update_settings(request: Request, session: Session = Depends(get_session)):
    data = await read_form_data(request)
    service = SettingsService(session)
    service.set(
        "exports",
        {
            "markdown": form_bool(data, "export_markdown"),
            "html": form_bool(data, "export_html"),
            "pdf": form_bool(data, "export_pdf"),
            "docx": form_bool(data, "export_docx"),
        },
    )
    service.set(
        "ai_policy_defaults",
        {
            "fact_links_required": form_bool(data, "fact_links_required"),
            "allow_new_bullets": form_bool(data, "allow_new_bullets"),
            "allow_hide_bullets": form_bool(data, "allow_hide_bullets"),
            "allow_title_edits": form_bool(data, "allow_title_edits"),
        },
    )
    service.set("locale", data.get("locale") or "en")
    if data.get("openai_api_key", "").strip():
        request.app.state.openai_secret_service.set_api_key(data["openai_api_key"].strip())
    return RedirectResponse("/settings", status_code=303)
