from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from app.api.dependencies import SessionDep, form_bool, read_form_data
from app.db.models import Resume, ResumeSection
from app.people.service import PeopleService
from app.settings.service import SettingsService
from app.storage.location import (
    clear_user_selected_app_data_root,
    get_app_data_location_status,
    set_user_selected_app_data_root,
)
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
    section = request.query_params.get("section", "profiles")
    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "settings": settings,
            "settings_section": section,
            "key_status": key_status,
            "profiles": service.list_profiles(),
            "active_profile": service.get_active_profile(),
            "prompt_templates": service.list_prompt_templates(),
            "data_folder_status": get_app_data_location_status(),
            "data_folder_error": request.query_params.get("data_folder_error", ""),
        },
    )


@router.post("")
async def update_settings(request: Request, session: SessionDep):
    data = await read_form_data(request)
    service = SettingsService(session)
    export_fields = {"export_markdown", "export_html", "export_pdf", "export_docx"}
    policy_fields = {
        "fact_links_required",
        "allow_new_bullets",
        "allow_hide_bullets",
        "allow_title_edits",
    }
    model_fields = {
        "openai_model_default",
        "openai_model_qa",
        "openai_model_extract",
        "openai_model_tailor",
    }

    section = data.get("settings_section", "")
    if section == "exports" or export_fields & data.keys():
        service.set(
            "exports",
            {
                "markdown": form_bool(data, "export_markdown"),
                "html": form_bool(data, "export_html"),
                "pdf": form_bool(data, "export_pdf"),
                "docx": form_bool(data, "export_docx"),
            },
        )
    if section == "ai-policy" or policy_fields & data.keys():
        service.set(
            "ai_policy_defaults",
            {
                "fact_links_required": form_bool(data, "fact_links_required"),
                "allow_new_bullets": form_bool(data, "allow_new_bullets"),
                "allow_hide_bullets": form_bool(data, "allow_hide_bullets"),
                "allow_title_edits": form_bool(data, "allow_title_edits"),
            },
        )
    if "locale" in data:
        locale = data.get("locale") or "en"
        service.set("locale", locale if locale in {"en", "ru"} else "en")
    if "active_profile_id" in data:
        service.set_active_profile(
            int(data["active_profile_id"]) if data.get("active_profile_id") else None
        )
    if model_fields & data.keys():
        service.set_model_settings({key: data.get(key, "") for key in model_fields})
    if data.get("openai_api_key", "").strip():
        request.app.state.openai_secret_service.set_api_key(
            data["openai_api_key"].strip()
        )
    if section == "data-folder":
        action = data.get("data_folder_action", "custom")
        if action == "default":
            clear_user_selected_app_data_root()
        else:
            root = data.get("root", "").strip()
            if not root:
                return RedirectResponse(
                    "/settings?section=data-folder&data_folder_error=Enter%20a%20folder%20path.",
                    status_code=303,
                )
            normalised = Path(root).expanduser().resolve(strict=False)
            try:
                normalised.mkdir(parents=True, exist_ok=True)
            except OSError:
                return RedirectResponse(
                    "/settings?section=data-folder&data_folder_error=The%20folder%20could%20not%20be%20created%20or%20used.",
                    status_code=303,
                )
            set_user_selected_app_data_root(normalised)
    next_section = data.get("settings_section") or "profiles"
    return RedirectResponse(f"/settings?section={next_section}", status_code=303)


@router.post("/active-profile")
async def set_active_profile(request: Request, session: SessionDep):
    data = await read_form_data(request)
    service = SettingsService(session)
    raw_profile_id = data.get("active_profile_id")
    try:
        service.set_active_profile(int(raw_profile_id) if raw_profile_id else None)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RedirectResponse(data.get("next") or "/", status_code=303)


@router.get("/facts")
def active_profile_facts(request: Request, session: SessionDep):
    service = SettingsService(session)
    active_profile = service.get_active_profile()
    facts = []
    if active_profile is not None:
        facts = PeopleService(session).list_facts(active_profile.id)
    return templates.TemplateResponse(
        "facts.html",
        {
            "request": request,
            "profile_id": active_profile.id if active_profile else None,
            "active_profile": active_profile,
            "facts": facts,
        },
    )


@router.get("/prompts")
def prompt_templates(request: Request, session: SessionDep):
    service = SettingsService(session)
    profiles = service.list_profiles()
    resumes = list(session.scalars(select(Resume).order_by(Resume.name)))
    sections = list(
        session.scalars(select(ResumeSection).order_by(ResumeSection.title))
    )
    return templates.TemplateResponse(
        "prompt_templates.html",
        {
            "request": request,
            "prompt_templates": service.list_prompt_templates(),
            "profiles": profiles,
            "resumes": resumes,
            "sections": sections,
        },
    )


@router.post("/prompts-scoped")
async def create_scoped_prompt_template(request: Request, session: SessionDep):
    data = await read_form_data(request)

    def optional_int(key: str) -> int | None:
        value = data.get(key, "").strip()
        return int(value) if value else None

    SettingsService(session).upsert_scoped_prompt_template(
        scope=data.get("scope", "global"),
        block_type=data.get("block_type", "summary"),
        user_prompt_template=data.get("user_prompt_template", ""),
        profile_id=optional_int("profile_id"),
        resume_id=optional_int("resume_id"),
        section_id=optional_int("section_id"),
    )
    return RedirectResponse("/settings/prompts", status_code=303)


@router.post("/prompts/{template_id}")
async def update_prompt_template(
    template_id: int, request: Request, session: SessionDep
):
    data = await read_form_data(request)
    SettingsService(session).update_prompt_template(
        template_id, data.get("user_prompt_template", "")
    )
    return RedirectResponse("/settings/prompts", status_code=303)
