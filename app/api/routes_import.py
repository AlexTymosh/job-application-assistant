from __future__ import annotations

from fastapi import APIRouter, Request, status
from fastapi.responses import HTMLResponse, Response

from app.import_tools.service import (
    ImportApplyBlockedError,
    ImportToolsError,
    ManagedCvImportService,
)
from app.web.templating import templates

router = APIRouter(tags=["import"])


@router.get("/profiles/import", response_class=HTMLResponse)
async def import_page(request: Request) -> HTMLResponse:
    return _render_import_page(request, status_code=status.HTTP_200_OK)


@router.post("/profiles/import/preview", response_class=HTMLResponse)
async def preview_import(request: Request) -> HTMLResponse:
    return _render_import_page(
        request, include_preview=True, status_code=status.HTTP_200_OK
    )


@router.post("/profiles/import/apply", response_class=HTMLResponse)
async def apply_import(request: Request) -> Response:
    try:
        result = _import_service(request).apply_import()
    except ImportApplyBlockedError as exc:
        return _render_import_page(
            request,
            include_preview=True,
            error_message=str(exc),
            status_code=status.HTTP_409_CONFLICT,
        )
    except ImportToolsError as exc:
        return _render_import_page(
            request,
            error_message=str(exc),
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    return _render_import_page(
        request,
        include_preview=True,
        success_message=(
            "Import applied. Created "
            f"{result.created_variants} variants, "
            f"{result.created_sections} sections, "
            f"{result.created_blocks} blocks, and "
            f"{result.created_facts} facts."
        ),
        status_code=status.HTTP_200_OK,
    )


def _render_import_page(
    request: Request,
    *,
    include_preview: bool = False,
    error_message: str | None = None,
    success_message: str | None = None,
    status_code: int,
) -> HTMLResponse:
    preview = None
    if include_preview and error_message is None:
        try:
            preview = _import_service(request).preview_import()
        except ImportToolsError as exc:
            error_message = str(exc)

    return templates.TemplateResponse(
        request=request,
        name="profiles_import.html",
        context={
            "project_name": "Local Job Application Assistant",
            "preview": preview,
            "error_message": error_message,
            "success_message": success_message,
        },
        status_code=status_code,
    )


def _import_service(request: Request) -> ManagedCvImportService:
    app_settings_service = getattr(request.app.state, "app_settings_service", None)
    if app_settings_service is None:
        raise ImportToolsError("App settings storage is not available.")
    return ManagedCvImportService(app_settings_service.session_factory)
