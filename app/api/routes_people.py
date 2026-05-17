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
    ("header", "Header"),
    ("summary", "Summary"),
    ("skills", "Skills"),
    ("work_experience", "Work Experience"),
    ("education", "Education"),
    ("languages", "Languages"),
    ("certificates", "Certificates"),
    ("references", "References"),
]


def _line(label: str, value: str | None) -> str:
    value = (value or "").strip()
    return f"{label}: {value}" if value else ""


def _content_from_master_form(category: str, data: dict[str, str]) -> tuple[str, str]:
    if category == "header":
        title = "Header"
        parts = [
            _line("First Name", data.get("first_name")),
            _line("Surname", data.get("surname")),
            _line("Location", data.get("location")),
            _line("Phone", data.get("phone")),
            _line("Email", data.get("email")),
            _line("LinkedIn", data.get("linkedin_url")),
            _line("GitHub", data.get("github_url")),
            _line("Extra", data.get("extra_text")),
        ]
        return title, "\n".join(part for part in parts if part)
    if category == "summary":
        return "Summary", data.get("summary", "").strip()
    if category == "skills":
        hard = data.get("hard_skills", "").strip()
        soft = data.get("soft_skills", "").strip()
        return "Skills", f"Hard Skills:\n{hard}\n\nSoft Skills:\n{soft}".strip()
    if category == "work_experience":
        title = (
            " - ".join(
                part
                for part in [
                    data.get("job_title", "").strip(),
                    data.get("employer", "").strip(),
                ]
                if part
            )
            or "Work Experience"
        )
        current = "I currently work here" if data.get("is_current") == "on" else ""
        parts = [
            _line("Job title", data.get("job_title")),
            _line("Employer", data.get("employer")),
            _line("Start Date", data.get("start_date")),
            current,
            _line("End Date", data.get("end_date")) if not current else "",
            _line("Extra", data.get("optional_extra_text"))
            if data.get("optional_extra_enabled") == "on"
            else "",
            _line("Key bullets", data.get("key_bullets")),
        ]
        return title, "\n".join(part for part in parts if part)
    if category == "education":
        title = data.get("institution_name", "").strip() or "Education"
        current = "Current" if data.get("is_current") == "on" else ""
        parts = [
            _line("Institution", data.get("institution_name")),
            _line("Specialisation", data.get("specialisation")),
            _line("Start Date", data.get("start_date")),
            current,
            _line("End Date", data.get("end_date")) if not current else "",
            _line("Achievements", data.get("key_bullets")),
        ]
        return title, "\n".join(part for part in parts if part)
    if category == "languages":
        title = data.get("language", "").strip() or "Language"
        return title, "\n".join(
            part
            for part in [
                _line("Language", data.get("language")),
                _line("Level", data.get("level")),
            ]
            if part
        )
    if category == "certificates":
        title = data.get("certificate_name", "").strip() or "Certificate"
        parts = [
            _line("Certificate", data.get("certificate_name")),
            _line("Certificate URL", data.get("certificate_url")),
            _line("Issue year", data.get("issue_year")),
        ]
        return title, "\n".join(part for part in parts if part)
    if category == "references":
        title = data.get("name", "").strip() or "Reference"
        parts = [
            _line("Name", data.get("name")),
            _line("Role title", data.get("role_title")),
            _line("Company", data.get("company")),
            _line("Phone", data.get("phone")),
            _line("Email", data.get("email")),
            _line("LinkedIn", data.get("linkedin_url")),
        ]
        return title, "\n".join(part for part in parts if part)
    return data.get("title", "Extended Experience").strip(), data.get(
        "content", ""
    ).strip()


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
    entries = service.list_master_entries(profile_id)
    valid_categories = {key for key, _title in MASTER_CV_CATEGORIES}
    current_category = category if category in valid_categories else "work_experience"
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
    category = data.get("category", "work_experience")
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
