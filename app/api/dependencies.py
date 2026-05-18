from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Annotated
from urllib.parse import parse_qs

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.errors import ProfileScopeError
from app.db.models import PersonProfile, Resume
from app.settings.service import SettingsService


def get_session(request: Request) -> Iterator[Session]:
    factory = request.app.state.session_factory
    with factory() as session:
        yield session


def get_app_data_root(request: Request) -> Path:
    return request.app.state.app_data_paths.root


SessionDep = Annotated[Session, Depends(get_session)]
AppDataRootDep = Annotated[Path, Depends(get_app_data_root)]


async def read_form_data(request: Request) -> dict[str, str]:
    body = (await request.body()).decode("utf-8")
    parsed = parse_qs(body, keep_blank_values=True)
    return {key: values[-1] if values else "" for key, values in parsed.items()}


async def read_form_multi_data(request: Request) -> dict[str, str | list[str]]:
    body = (await request.body()).decode("utf-8")
    parsed = parse_qs(body, keep_blank_values=True)
    return {
        key: values if len(values) > 1 else values[-1] if values else ""
        for key, values in parsed.items()
    }


def form_bool(data: dict[str, str], key: str) -> bool:
    return data.get(key, "").lower() in {"true", "on", "1", "yes"}


def require_active_profile_resume(resume_id: int, session: Session) -> Resume:
    """Return a resume only when it belongs to the active profile."""

    active_profile = SettingsService(session).require_active_profile()
    resume = session.get(Resume, resume_id)
    if resume is None or resume.profile_id != active_profile.id:
        raise ProfileScopeError("Resume not found in the active profile.")
    return resume


def require_active_profile_workspace(
    profile_id: int, session: Session
) -> PersonProfile:
    """Return a profile only when it is the active profile workspace."""

    active_profile = SettingsService(session).require_active_profile()
    profile = session.get(PersonProfile, profile_id)
    if profile is None or profile.id != active_profile.id:
        raise ProfileScopeError("Profile workspace not found.")
    return profile
