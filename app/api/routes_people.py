from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api.dependencies import get_session, read_form_data
from app.db.models import ClaimLevel, PersonProfile
from app.people.service import PeopleService
from app.web.templating import templates

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.get("")
def profiles(request: Request, session: Session = Depends(get_session)):
    return templates.TemplateResponse("profiles.html", {"request": request, "profiles": PeopleService(session).list_profiles()})


@router.get("/new")
def new_profile(request: Request):
    return templates.TemplateResponse("profile_form.html", {"request": request, "profile": None})


@router.post("/new")
async def create_profile(request: Request, session: Session = Depends(get_session)):
    data = await read_form_data(request)
    profile = PeopleService(session).create_profile(data["display_name"], data.get("full_name", ""), data.get("location", ""))
    return RedirectResponse(f"/profiles/{profile.id}", status_code=303)


@router.get("/{profile_id}")
def profile_detail(profile_id: int, request: Request, session: Session = Depends(get_session)):
    profile = session.get(PersonProfile, profile_id)
    return templates.TemplateResponse("profile_detail.html", {"request": request, "profile": profile})


@router.get("/{profile_id}/edit")
def edit_profile(profile_id: int, request: Request, session: Session = Depends(get_session)):
    return templates.TemplateResponse("profile_form.html", {"request": request, "profile": session.get(PersonProfile, profile_id)})


@router.post("/{profile_id}/edit")
async def update_profile(profile_id: int, request: Request, session: Session = Depends(get_session)):
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
    )
    return RedirectResponse(f"/profiles/{profile_id}", status_code=303)


@router.get("/{profile_id}/facts")
def facts(profile_id: int, request: Request, session: Session = Depends(get_session)):
    return templates.TemplateResponse("facts.html", {"request": request, "profile_id": profile_id, "facts": PeopleService(session).list_facts(profile_id)})


@router.get("/{profile_id}/facts/new")
def new_fact(profile_id: int, request: Request):
    return templates.TemplateResponse("fact_form.html", {"request": request, "profile_id": profile_id, "levels": [level.value for level in ClaimLevel]})


@router.post("/{profile_id}/facts/new")
async def create_fact(profile_id: int, request: Request, session: Session = Depends(get_session)):
    data = await read_form_data(request)
    PeopleService(session).create_fact(
        profile_id,
        fact_key=data["fact_key"],
        category=data.get("category", ""),
        claim=data["claim"],
        evidence=data.get("evidence", ""),
        source=data.get("source", ""),
        allowed_claim_level=data.get("allowed_claim_level", ClaimLevel.MENTION_ONLY.value),
    )
    return RedirectResponse(f"/profiles/{profile_id}/facts", status_code=303)
