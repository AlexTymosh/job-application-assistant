from __future__ import annotations

from urllib.parse import parse_qsl

from fastapi import APIRouter, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from pydantic import ValidationError

from app.core.config import LlmExtractionMode
from app.runtime import refresh_runtime_state
from app.settings.form_models import (
    SettingsFormError,
    parse_settings_form,
    persist_settings_form,
)
from app.settings.schema import ManagedAppSettings
from app.settings.service import AppSettingsService
from app.setup.checks import SetupCheck, SetupStatus
from app.web.templating import templates

router = APIRouter(tags=["settings"])


@router.get("/settings", response_class=HTMLResponse)
async def settings(request: Request) -> HTMLResponse:
    return _render_settings(request, status_code=status.HTTP_200_OK)


@router.post("/settings", response_class=HTMLResponse)
async def save_settings(request: Request) -> Response:
    form = await _read_urlencoded_form(request)
    service: AppSettingsService | None = request.app.state.app_settings_service
    if service is None:
        return _render_settings(
            request,
            error_message=(
                "App settings storage is not available. Restart the app so settings "
                "storage can be initialised."
            ),
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    try:
        result = parse_settings_form(form)
        persist_settings_form(service, result)
    except SettingsFormError as exc:
        return _render_settings(
            request,
            submitted_values={str(key): value for key, value in form.items()},
            error_message=str(exc),
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    refresh_runtime_state(request.app)
    return RedirectResponse(url="/settings", status_code=status.HTTP_303_SEE_OTHER)


async def _read_urlencoded_form(request: Request) -> dict[str, str]:
    body = await request.body()
    return dict(parse_qsl(body.decode("utf-8"), keep_blank_values=True))


def _render_settings(
    request: Request,
    *,
    submitted_values: dict[str, object] | None = None,
    error_message: str | None = None,
    status_code: int,
) -> HTMLResponse:
    service: AppSettingsService | None = request.app.state.app_settings_service
    managed_settings = ManagedAppSettings()
    if service is not None:
        try:
            managed_settings = service.get_managed_settings()
        except (ValueError, ValidationError) as exc:
            error_message = error_message or f"Stored app settings are invalid: {exc}"
    setup_status: SetupStatus = request.app.state.setup_status
    llm_check = _check_by_code(setup_status, "llm_mode")

    return templates.TemplateResponse(
        request=request,
        name="settings.html",
        context={
            "project_name": "Local Job Application Assistant",
            "settings": managed_settings,
            "effective_config": getattr(request.app.state, "config", None),
            "llm_modes": [mode.value for mode in LlmExtractionMode],
            "llm_check": llm_check,
            "setup_status": setup_status,
            "submitted_values": submitted_values or {},
            "error_message": error_message,
        },
        status_code=status_code,
    )


def _check_by_code(setup_status: SetupStatus, code: str) -> SetupCheck | None:
    return next((check for check in setup_status.checks if check.code == code), None)
