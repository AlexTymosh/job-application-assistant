from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from app.api.dependencies import SessionDep, form_bool, read_form_data
from app.llm.schemas import expected_response_contract_for_task
from app.prompt_variants.service import PromptVariantService
from app.settings.service import SettingsService
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
    if "llm_mode" in data:
        service.set_llm_mode(data.get("llm_mode", "openai"))
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
    except ValueError:
        return RedirectResponse("/settings?section=profiles", status_code=303)
    return RedirectResponse(data.get("next") or "/", status_code=303)


@router.get("/prompts")
def prompt_templates_redirect():
    return RedirectResponse("/settings/prompt-variants", status_code=303)


@router.post("/prompts-scoped")
def create_scoped_prompt_template_redirect():
    return RedirectResponse("/settings/prompt-variants", status_code=303)


@router.post("/prompts/{template_id}")
def update_prompt_template_redirect(template_id: int):
    _ = template_id
    return RedirectResponse("/settings/prompt-variants", status_code=303)


@router.get("/prompt-variants")
def prompt_variants_page(request: Request, session: SessionDep):
    service = PromptVariantService(session)
    return templates.TemplateResponse(
        "prompt_variants.html",
        {"request": request, "variants": service.list_active()},
    )


@router.get("/prompt-variants/new")
def prompt_variant_new(request: Request, session: SessionDep):
    service = PromptVariantService(session)
    default = service.ensure_default_variant()
    return templates.TemplateResponse(
        "prompt_variant_form.html",
        {
            "request": request,
            "variant": None,
            "prompts": service.prompts_for(default.id),
            "action": "/settings/prompt-variants/new",
            "title": "New Prompt Variant",
            "is_builtin": False,
            "expected_contracts": {
                task: expected_response_contract_for_task(task)
                for task in ["resume_tailoring", "cover_letter", "fit_analysis"]
            },
        },
    )


@router.post("/prompt-variants/new")
async def prompt_variant_new_post(request: Request, session: SessionDep):
    data = await read_form_data(request)
    PromptVariantService(session).create_variant(
        name=data.get("name", ""),
        description=data.get("description", ""),
        prompts={
            "resume_tailoring": data.get("resume_tailoring", ""),
            "cover_letter": data.get("cover_letter", ""),
            "fit_analysis": data.get("fit_analysis", ""),
        },
    )
    return RedirectResponse("/settings/prompt-variants", status_code=303)


@router.get("/prompt-variants/{variant_id}/edit")
def prompt_variant_edit(variant_id: int, request: Request, session: SessionDep):
    service = PromptVariantService(session)
    variant = service.get_variant(variant_id)
    return templates.TemplateResponse(
        "prompt_variant_form.html",
        {
            "request": request,
            "variant": variant,
            "prompts": service.prompts_for(variant.id),
            "action": f"/settings/prompt-variants/{variant.id}/edit",
            "title": "Edit Prompt Variant",
            "is_builtin": variant.is_builtin,
            "expected_contracts": {
                task: expected_response_contract_for_task(task)
                for task in ["resume_tailoring", "cover_letter", "fit_analysis"]
            },
        },
    )


@router.post("/prompt-variants/{variant_id}/edit")
async def prompt_variant_edit_post(
    variant_id: int, request: Request, session: SessionDep
):
    data = await read_form_data(request)
    PromptVariantService(session).update_variant(
        variant_id,
        name=data.get("name", ""),
        description=data.get("description", ""),
        prompts={
            "resume_tailoring": data.get("resume_tailoring", ""),
            "cover_letter": data.get("cover_letter", ""),
            "fit_analysis": data.get("fit_analysis", ""),
        },
    )
    return RedirectResponse("/settings/prompt-variants", status_code=303)


@router.post("/prompt-variants/{variant_id}/restore-defaults")
def prompt_variant_restore_defaults(variant_id: int, session: SessionDep):
    PromptVariantService(session).restore_defaults(variant_id)
    return RedirectResponse(
        f"/settings/prompt-variants/{variant_id}/edit", status_code=303
    )


@router.post("/prompt-variants/{variant_id}/deactivate")
def prompt_variant_deactivate(variant_id: int, session: SessionDep):
    PromptVariantService(session).deactivate_variant(variant_id)
    return RedirectResponse("/settings/prompt-variants", status_code=303)


@router.post("/prompt-variants/{variant_id}/copy")
def prompt_variant_copy(variant_id: int, session: SessionDep):
    PromptVariantService(session).copy_variant(variant_id)
    return RedirectResponse("/settings/prompt-variants", status_code=303)
