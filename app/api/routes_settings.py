from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from app.api.dependencies import SessionDep, form_bool, read_form_data
from app.people.service import PeopleService
from app.settings.service import SettingsService
from app.web.templating import templates

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("")
def settings_page(request: Request, session: SessionDep):
    service = SettingsService(session)
    settings = service.effective()
    secret_service = request.app.state.openai_secret_service
    try:
        key_status = "configured" if secret_service.get_api_key() else "not configured"
    except Exception:
        key_status = "unavailable"
    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "settings": settings,
            "key_status": key_status,
            "profiles": service.list_profiles(),
            "active_profile": service.get_active_profile(),
            "prompt_templates": service.list_prompt_templates(),
        },
    )


@router.post("")
async def update_settings(request: Request, session: SessionDep):
    data = await read_form_data(request)
    service = SettingsService(session)
    current = service.effective()
    if any(
        key in data
        for key in {"export_markdown", "export_html", "export_pdf", "export_docx"}
    ):
        service.set(
            "exports",
            {
                "markdown": form_bool(data, "export_markdown"),
                "html": form_bool(data, "export_html"),
                "pdf": form_bool(data, "export_pdf"),
                "docx": form_bool(data, "export_docx"),
            },
        )
    if any(
        key in data
        for key in {
            "fact_links_required",
            "allow_new_bullets",
            "allow_hide_bullets",
            "allow_title_edits",
        }
    ):
        service.set(
            "ai_policy_defaults",
            {
                "fact_links_required": form_bool(data, "fact_links_required"),
                "allow_new_bullets": form_bool(data, "allow_new_bullets"),
                "allow_hide_bullets": form_bool(data, "allow_hide_bullets"),
                "allow_title_edits": form_bool(data, "allow_title_edits"),
            },
        )
    service.set("locale", data.get("locale") or current.locale or "en")
    if data.get("active_profile_id"):
        service.set_active_profile(int(data["active_profile_id"]))
    if data.get("openai_api_key", "").strip():
        request.app.state.openai_secret_service.set_api_key(
            data["openai_api_key"].strip()
        )
    return RedirectResponse("/settings", status_code=303)


@router.post("/active-profile")
async def set_active_profile(request: Request, session: SessionDep):
    data = await read_form_data(request)
    service = SettingsService(session)
    raw_profile_id = data.get("active_profile_id")
    service.set_active_profile(int(raw_profile_id) if raw_profile_id else None)
    return RedirectResponse(data.get("next") or "/", status_code=303)


@router.get("/active-profile/facts")
def active_profile_facts(request: Request, session: SessionDep):
    service = SettingsService(session)
    active_profile = service.get_active_profile()
    if active_profile is None:
        return templates.TemplateResponse(
            "facts.html",
            {
                "request": request,
                "profile": None,
                "profile_id": None,
                "facts": [],
            },
        )
    return templates.TemplateResponse(
        "facts.html",
        {
            "request": request,
            "profile": active_profile,
            "profile_id": active_profile.id,
            "facts": PeopleService(session).list_facts(active_profile.id),
        },
    )


@router.get("/prompts")
def prompt_templates(request: Request, session: SessionDep):
    return templates.TemplateResponse(
        "prompt_templates.html",
        {
            "request": request,
            "prompt_templates": SettingsService(session).list_prompt_templates(),
        },
    )


@router.post("/prompts/{template_id}")
async def update_prompt_template(
    template_id: int, request: Request, session: SessionDep
):
    data = await read_form_data(request)
    SettingsService(session).update_prompt_template(
        template_id, data.get("user_prompt_template", "")
    )
    return RedirectResponse("/settings/prompts", status_code=303)
