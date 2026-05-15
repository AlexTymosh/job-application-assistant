from __future__ import annotations

from urllib.parse import parse_qsl

from fastapi import APIRouter, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from app.profiles.service import (
    ManagedProfileError,
    ManagedProfileService,
    build_managed_profile_service,
)
from app.runtime import refresh_runtime_state
from app.web.templating import templates

router = APIRouter(tags=["profiles"])


@router.get("/profiles", response_class=HTMLResponse)
async def profiles(request: Request) -> HTMLResponse:
    return _render_profiles(request, status_code=status.HTTP_200_OK)


@router.post("/profiles", response_class=HTMLResponse)
async def connect_profile(request: Request) -> Response:
    form = await _read_urlencoded_form(request)
    try:
        service = _profile_service(request)
        service.create_file_based_profile(
            name=form.get("name", ""),
            display_name=form.get("display_name") or None,
            data_dir=form.get("data_dir", ""),
            make_active=form.get("make_active") == "on",
        )
    except ManagedProfileError as exc:
        return _render_profiles(
            request,
            submitted_values=form,
            error_message=str(exc),
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    refresh_runtime_state(request.app)
    return RedirectResponse(url="/profiles", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/profiles/{profile_id}/activate", response_class=HTMLResponse)
async def activate_profile(request: Request, profile_id: str) -> Response:
    try:
        service = _profile_service(request)
        service.set_active_profile(profile_id)
    except ManagedProfileError as exc:
        return _render_profiles(
            request,
            error_message=str(exc),
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    refresh_runtime_state(request.app)
    return RedirectResponse(url="/profiles", status_code=status.HTTP_303_SEE_OTHER)


async def _read_urlencoded_form(request: Request) -> dict[str, str]:
    body = await request.body()
    return dict(parse_qsl(body.decode("utf-8"), keep_blank_values=True))


def _profile_service(request: Request) -> ManagedProfileService:
    app_settings_service = request.app.state.app_settings_service
    if app_settings_service is None:
        raise ManagedProfileError("App settings storage is not available.")
    return build_managed_profile_service(
        app_settings_service.session_factory,
        app_settings_service=app_settings_service,
    )


def _render_profiles(
    request: Request,
    *,
    submitted_values: dict[str, str] | None = None,
    error_message: str | None = None,
    status_code: int,
) -> HTMLResponse:
    try:
        service = _profile_service(request)
        profiles = service.list_profiles()
        validation_by_id = {
            profile.id: service.validate_profile(profile) for profile in profiles
        }
    except ManagedProfileError as exc:
        profiles = []
        validation_by_id = {}
        error_message = error_message or str(exc)

    setup_status = request.app.state.setup_status_service.build_status(
        config=request.app.state.explicit_config
    )
    request.app.state.setup_status = setup_status

    return templates.TemplateResponse(
        request=request,
        name="profiles.html",
        context={
            "project_name": "Local Job Application Assistant",
            "profiles": profiles,
            "validation_by_id": validation_by_id,
            "submitted_values": submitted_values or {},
            "error_message": error_message,
            "setup_status": setup_status,
        },
        status_code=status_code,
    )
