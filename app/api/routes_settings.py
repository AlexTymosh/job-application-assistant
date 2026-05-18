from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from app.api.dependencies import SessionDep, form_bool, read_form_data
from app.db.models import Resume, ResumeSection
from app.settings.service import PROMPT_TEMPLATE_TYPES, SettingsService
from app.storage.location import (
    clear_user_selected_app_data_root,
    set_user_selected_app_data_root,
)
from app.web.templating import templates

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("")
def settings(
    request: Request,
    session: SessionDep,
    section: str = "profiles",
    data_folder_error: str = "",
):
    service = SettingsService(session)
    effective = service.effective()
    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "settings": effective,
            "section": section,
            "profiles": service.list_profiles(),
            "model_settings": service.model_settings(),
            "openai_key_available": (
                request.app.state.openai_secret_service.get_api_key() is not None
            ),
            "data_folder_error": data_folder_error,
        },
    )


@router.post("")
async def update_settings(request: Request, session: SessionDep):
    data = await read_form_data(request)
    service = SettingsService(session)
    section = data.get("settings_section") or "profiles"
    if "locale" in data:
        locale = data.get("locale") or "en"
        service.set("locale", locale if locale in {"en", "ru"} else "en")
    if "active_profile_id" in data:
        service.set_active_profile(
            int(data["active_profile_id"]) if data.get("active_profile_id") else None
        )
    if section == "exports":
        service.set(
            "exports",
            {
                "markdown": form_bool(data, "export_markdown"),
                "html": form_bool(data, "export_html"),
                "pdf": form_bool(data, "export_pdf"),
                "docx": form_bool(data, "export_docx"),
            },
        )
    if section == "ai-policy":
        service.set(
            "ai_policy_defaults",
            {
                "use_master_cv": form_bool(data, "use_master_cv"),
                "allow_new_bullets": form_bool(data, "allow_new_bullets"),
                "allow_hide_bullets": form_bool(data, "allow_hide_bullets"),
                "allow_title_edits": form_bool(data, "allow_title_edits"),
            },
        )
    model_fields = {
        "openai_model_default",
        "openai_model_qa",
        "openai_model_extract",
        "openai_model_tailor",
    }
    if model_fields & data.keys():
        service.set_model_settings({key: data.get(key, "") for key in model_fields})
    if data.get("openai_api_key", "").strip():
        request.app.state.openai_secret_service.set_api_key(
            data["openai_api_key"].strip()
        )
    if section == "data-folder":
        action = data.get("data_folder_action", "save")
        if action == "reset":
            clear_user_selected_app_data_root()
        else:
            raw_root = data.get("root", "").strip()
            if not raw_root:
                return RedirectResponse(
                    "/settings?section=data-folder&data_folder_error=Enter%20a%20folder%20path.",
                    status_code=303,
                )
            root = Path(raw_root).expanduser()
            try:
                root.mkdir(parents=True, exist_ok=True)
            except OSError:
                return RedirectResponse(
                    "/settings?section=data-folder&data_folder_error=The%20folder%20could%20not%20be%20created%20or%20used.",
                    status_code=303,
                )
            set_user_selected_app_data_root(root)
    return RedirectResponse(f"/settings?section={section}", status_code=303)


@router.post("/active-profile")
async def set_active_profile(request: Request, session: SessionDep):
    data = await read_form_data(request)
    try:
        SettingsService(session).set_active_profile(
            int(data["active_profile_id"]) if data.get("active_profile_id") else None
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RedirectResponse(data.get("next") or "/", status_code=303)


@router.get("/prompts")
def prompt_templates(
    request: Request, session: SessionDep, block_type: str = "summary"
):
    service = SettingsService(session)
    prompt_types = PROMPT_TEMPLATE_TYPES
    current_block_type = block_type if block_type in prompt_types else "summary"
    templates_for_type = [
        template
        for template in service.list_prompt_templates()
        if template.block_type == current_block_type
    ]
    return templates.TemplateResponse(
        "prompt_templates.html",
        {
            "request": request,
            "prompt_templates": templates_for_type,
            "all_prompt_templates": service.list_prompt_templates(),
            "prompt_types": prompt_types,
            "current_block_type": current_block_type,
            "profiles": service.list_profiles(),
            "resumes": list(session.scalars(select(Resume).order_by(Resume.name))),
            "sections": list(
                session.scalars(select(ResumeSection).order_by(ResumeSection.title))
            ),
        },
    )


@router.post("/prompts-scoped")
async def create_scoped_prompt_template(request: Request, session: SessionDep):
    data = await read_form_data(request)

    def optional_int(key: str) -> int | None:
        value = data.get(key, "").strip()
        return int(value) if value else None

    scope = data.get("scope", "global")
    block_type = data.get("block_type", "summary")
    SettingsService(session).upsert_scoped_prompt_template(
        scope=scope,
        block_type=block_type,
        user_prompt_template=data.get("user_prompt_template", ""),
        profile_id=optional_int("profile_id"),
        resume_id=optional_int("resume_id"),
        section_id=optional_int("section_id"),
    )
    return RedirectResponse(
        f"/settings/prompts?block_type={block_type}", status_code=303
    )


@router.post("/prompts/{template_id}")
async def update_prompt_template(
    template_id: int, request: Request, session: SessionDep
):
    data = await read_form_data(request)
    block_type = data.get("block_type", "summary")
    SettingsService(session).update_prompt_template(
        template_id, data.get("user_prompt_template", "")
    )
    return RedirectResponse(
        f"/settings/prompts?block_type={block_type}", status_code=303
    )
