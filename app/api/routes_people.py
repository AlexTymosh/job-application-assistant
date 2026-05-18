from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from app.api.dependencies import (
    SessionDep,
    get_app_data_root,
    read_form_data,
    require_active_profile_workspace,
)
from app.people.service import PeopleService
from app.settings.service import SettingsService
from app.web.templating import templates

router = APIRouter(prefix="/profiles", tags=["profiles"])

MASTER_CV_CATEGORIES = [
    ("summary", "Summary"),
    ("skills", "Skills"),
    ("work_experience", "Work Experience"),
    ("education", "Education"),
]
MASTER_CV_DEFAULT_CATEGORY = "work_experience"


def _source_title(default_title: str, content: str) -> str:
    first_line = next(
        (line.strip("-• ").strip() for line in content.splitlines() if line.strip()), ""
    )
    return first_line[:80] if first_line else default_title


def _content_from_master_form(category: str, data: dict[str, str]) -> tuple[str, str]:
    if category == "summary":
        content = data.get("summary", "").strip()
        return "Summary Source", content
    if category == "skills":
        hard = data.get("hard_skills", "").strip()
        soft = data.get("soft_skills", "").strip()
        return "Skills Source", f"Hard Skills:\n{hard}\n\nSoft Skills:\n{soft}".strip()
    if category == "work_experience":
        content = data.get("key_bullets", "").strip()
        return _source_title("Work Experience Source", content), content
    if category == "education":
        content = data.get("key_bullets", "").strip()
        return _source_title("Education Source", content), content
    return "Work Experience Source", data.get("content", "").strip()


def _normalise_master_cv_category(category: str) -> str:
    valid_categories = {key for key, _title in MASTER_CV_CATEGORIES}
    return category if category in valid_categories else MASTER_CV_DEFAULT_CATEGORY


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
def master_cv_default(profile_id: int, session: SessionDep):
    require_active_profile_workspace(profile_id, session)
    return RedirectResponse(
        f"/profiles/{profile_id}/master-cv/work_experience", status_code=303
    )


@router.get("/{profile_id}/master-cv/{category}")
def master_cv(profile_id: int, category: str, request: Request, session: SessionDep):
    profile = require_active_profile_workspace(profile_id, session)
    service = PeopleService(session)
    entries = service.list_master_entries(profile_id, ai_safe_only=True)
    current_category = _normalise_master_cv_category(category)
    if current_category != category:
        return RedirectResponse(
            f"/profiles/{profile_id}/master-cv/{current_category}", status_code=303
        )
    return templates.TemplateResponse(
        "master_cv.html",
        {
            "request": request,
            "profile": profile,
            "entries": entries,
            "current_entries": [
                entry for entry in entries if entry.category == current_category
            ],
            "category_nav": MASTER_CV_CATEGORIES,
            "current_category": current_category,
            "current_title": dict(MASTER_CV_CATEGORIES)[current_category],
        },
    )


@router.post("/{profile_id}/master-cv")
async def create_master_cv_entry(
    profile_id: int, request: Request, session: SessionDep
):
    require_active_profile_workspace(profile_id, session)
    data = await read_form_data(request)
    category = _normalise_master_cv_category(
        data.get("category", MASTER_CV_DEFAULT_CATEGORY)
    )
    title, content = _content_from_master_form(category, data)
    PeopleService(session).create_master_entry(
        profile_id,
        category=category,
        title=title,
        content=content,
        keywords="",
        allowed_wording="",
        forbidden_wording="",
        inference_notes="",
        claim_strength="normal",
    )
    return RedirectResponse(
        f"/profiles/{profile_id}/master-cv/{category}",
        status_code=303,
    )


@router.get("/{profile_id}/master-cv/items/{entry_id}/edit")
def edit_master_cv_entry(
    profile_id: int, entry_id: int, request: Request, session: SessionDep
):
    profile = require_active_profile_workspace(profile_id, session)
    service = PeopleService(session)
    entry = service.get_profile_master_entry(profile_id, entry_id, ai_safe_only=True)
    current_category = _normalise_master_cv_category(entry.category)
    return templates.TemplateResponse(
        "master_cv.html",
        {
            "request": request,
            "profile": profile,
            "entries": service.list_master_entries(profile_id, ai_safe_only=True),
            "current_entries": [entry],
            "category_nav": MASTER_CV_CATEGORIES,
            "current_category": current_category,
            "current_title": dict(MASTER_CV_CATEGORIES)[current_category],
            "editing_entry": entry,
        },
    )


@router.post("/{profile_id}/master-cv/items/{entry_id}/edit")
async def update_master_cv_entry(
    profile_id: int, entry_id: int, request: Request, session: SessionDep
):
    require_active_profile_workspace(profile_id, session)
    service = PeopleService(session)
    entry = service.get_profile_master_entry(profile_id, entry_id, ai_safe_only=True)
    data = await read_form_data(request)
    category = _normalise_master_cv_category(data.get("category", entry.category))
    title, content = _content_from_master_form(category, data)
    service.update_master_entry(
        entry_id, category=category, title=title, content=content
    )
    return RedirectResponse(
        f"/profiles/{profile_id}/master-cv/{category}", status_code=303
    )


@router.post("/{profile_id}/master-cv/items/{entry_id}/delete")
async def delete_master_cv_entry(
    profile_id: int, entry_id: int, request: Request, session: SessionDep
):
    require_active_profile_workspace(profile_id, session)
    service = PeopleService(session)
    entry = service.get_profile_master_entry(profile_id, entry_id, ai_safe_only=True)
    data = await read_form_data(request)
    service.delete_master_entry(entry_id, confirm=data.get("confirm_delete_entry", ""))
    return RedirectResponse(
        f"/profiles/{profile_id}/master-cv/{_normalise_master_cv_category(entry.category)}",
        status_code=303,
    )


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
