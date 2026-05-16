from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from app.api.dependencies import SessionDep, form_bool, read_form_data
from app.db.models import Resume, ResumeSection
from app.people.service import PeopleService
from app.settings.service import SettingsService
from app.web.templating import templates

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("")
def settings_page(request: Request, session: SessionDep):
    service = SettingsService(session)
    settings = service.effective()
    section = request.query_params.get("section", "profiles")
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
            "section": section,
        },
    )


@router.post("")
async def update_settings(request: Request, session: SessionDep):
    data = await read_form_data(request)
    service = SettingsService(session)

    export_fields = {"export_markdown", "export_html", "export_pdf", "export_docx"}
    if export_fields.intersection(data):
        service.set(
            "exports",
            {
                "markdown": form_bool(data, "export_markdown"),
                "html": form_bool(data, "export_html"),
                "pdf": form_bool(data, "export_pdf"),
                "docx": form_bool(data, "export_docx"),
            },
        )

    policy_fields = {
        "fact_links_required",
        "allow_new_bullets",
        "allow_hide_bullets",
        "allow_title_edits",
    }
    if policy_fields.intersection(data):
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
        service.set("locale", data.get("locale") or "en")

    model_fields = {
        "openai_model_default",
        "openai_model_qa",
        "openai_model_extract",
        "openai_model_tailor",
    }
    if model_fields.intersection(data):
        for field in model_fields:
            if field in data:
                service.set(field, data.get(field, "").strip())

    if "active_profile_id" in data:
        service.set_active_profile(
            int(data["active_profile_id"]) if data.get("active_profile_id") else None
        )
    if data.get("openai_api_key", "").strip():
        request.app.state.openai_secret_service.set_api_key(
            data["openai_api_key"].strip()
        )
    return RedirectResponse(data.get("next") or "/settings", status_code=303)


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
        session.scalars(
            select(ResumeSection)
            .join(Resume)
            .order_by(Resume.name, ResumeSection.display_order)
        )
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
