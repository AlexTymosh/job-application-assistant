from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from app.api.dependencies import SessionDep, get_app_data_root, read_form_data
from app.db.models import ClaimStrength
from app.people.service import PeopleService
from app.settings.service import SettingsService
from app.web.templating import templates

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.get("")
def profiles(request: Request, session: SessionDep):
    return templates.TemplateResponse(
        "profiles.html",
        {"request": request, "profiles": PeopleService(session).list_profiles()},
    )


@router.get("/new")
def new_profile(request: Request):
    return templates.TemplateResponse(
        "profile_form.html", {"request": request, "profile": None}
    )


@router.post("/new")
async def create_profile(request: Request, session: SessionDep):
    data = await read_form_data(request)
    profile = PeopleService(session).create_profile(
        data["display_name"], data.get("full_name", ""), data.get("preferred_name", "")
    )
    if SettingsService(session).get_active_profile() is None:
        SettingsService(session).set_active_profile(profile.id)
    return RedirectResponse(f"/profiles/{profile.id}", status_code=303)


@router.get("/{profile_id}")
def profile_detail(profile_id: int, request: Request, session: SessionDep):
    return templates.TemplateResponse(
        "profile_detail.html",
        {"request": request, "profile": PeopleService(session).get_profile(profile_id)},
    )


@router.get("/{profile_id}/edit")
def edit_profile(profile_id: int, request: Request, session: SessionDep):
    return templates.TemplateResponse(
        "profile_form.html",
        {"request": request, "profile": PeopleService(session).get_profile(profile_id)},
    )


@router.post("/{profile_id}/edit")
async def update_profile(profile_id: int, request: Request, session: SessionDep):
    data = await read_form_data(request)
    PeopleService(session).update_profile(
        profile_id,
        display_name=data["display_name"],
        full_name=data.get("full_name", ""),
        preferred_name=data.get("preferred_name", ""),
        location=data.get("location", ""),
        email=data.get("email", ""),
        phone=data.get("phone", ""),
        address_line=data.get("address_line", ""),
        city=data.get("city", ""),
        country=data.get("country", ""),
        linkedin_url=data.get("linkedin_url", ""),
        github_url=data.get("github_url", ""),
        extra_text=data.get("extra_text", ""),
    )
    return RedirectResponse(f"/profiles/{profile_id}", status_code=303)


@router.get("/{profile_id}/master-cv")
def master_cv(profile_id: int, request: Request, session: SessionDep):
    service = PeopleService(session)
    return templates.TemplateResponse(
        "master_cv.html",
        {
            "request": request,
            "profile": service.get_profile(profile_id),
            "entries": service.list_master_entries(profile_id),
            "strengths": [item.value for item in ClaimStrength],
        },
    )


@router.post("/{profile_id}/master-cv")
async def create_master_cv_entry(
    profile_id: int, request: Request, session: SessionDep
):
    data = await read_form_data(request)
    PeopleService(session).create_master_entry(
        profile_id,
        category=data.get("category", "work_experience"),
        title=data.get("title", ""),
        content=data.get("content", ""),
        keywords=data.get("keywords", ""),
        allowed_wording=data.get("allowed_wording", ""),
        forbidden_wording=data.get("forbidden_wording", ""),
        inference_notes=data.get("inference_notes", ""),
        claim_strength=data.get("claim_strength", ClaimStrength.NORMAL.value),
    )
    return RedirectResponse(f"/profiles/{profile_id}/master-cv", status_code=303)


@router.post("/{profile_id}/set-active")
def set_active_profile(profile_id: int, session: SessionDep):
    SettingsService(session).set_active_profile(profile_id)
    return RedirectResponse("/", status_code=303)


@router.post("/{profile_id}/applications/delete")
async def delete_profile_applications(
    profile_id: int, request: Request, session: SessionDep
):
    from app.applications.service import ApplicationService

    data = await read_form_data(request)
    if data.get("confirm_delete_applications") == "on":
        ApplicationService(session).delete_profile_applications(
            profile_id, app_data_root=get_app_data_root(request)
        )
    return RedirectResponse(f"/profiles/{profile_id}", status_code=303)


@router.post("/{profile_id}/delete")
async def delete_profile(profile_id: int, request: Request, session: SessionDep):
    data = await read_form_data(request)
    service = PeopleService(session)
    service.require_delete_confirmation(
        profile_id, data.get("confirm_profile_name", "")
    )
    active_profile = SettingsService(session).get_active_profile()
    service.delete_profile(profile_id, get_app_data_root(request))
    if active_profile is not None and active_profile.id == profile_id:
        SettingsService(session).set_active_profile(None)
    return RedirectResponse("/profiles", status_code=303)
