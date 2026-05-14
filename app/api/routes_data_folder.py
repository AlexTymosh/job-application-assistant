from __future__ import annotations

from urllib.parse import parse_qsl

from fastapi import APIRouter, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from app.runtime import refresh_app_data_state
from app.storage.service import (
    AppDataFolderError,
    bootstrap_or_connect_app_data_root,
    get_app_data_folder_status,
)
from app.web.templating import templates

router = APIRouter(tags=["data-folder"])


@router.get("/data-folder", response_class=HTMLResponse)
async def data_folder(request: Request) -> HTMLResponse:
    message = request.query_params.get("message")
    return _render_data_folder(
        request,
        success_message=message,
        status_code=status.HTTP_200_OK,
    )


@router.post("/data-folder", response_class=HTMLResponse)
async def save_data_folder(request: Request) -> Response:
    form = await _read_urlencoded_form(request)
    submitted_path = form.get("app_data_root", "")

    try:
        result = bootstrap_or_connect_app_data_root(submitted_path)
    except AppDataFolderError as exc:
        return _render_data_folder(
            request,
            submitted_path=submitted_path,
            error_message=str(exc),
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    refresh_app_data_state(request.app, result.paths)
    return RedirectResponse(
        url="/data-folder?message=Data+folder+connected",
        status_code=status.HTTP_303_SEE_OTHER,
    )


async def _read_urlencoded_form(request: Request) -> dict[str, str]:
    body = await request.body()
    return dict(parse_qsl(body.decode("utf-8"), keep_blank_values=True))


def _render_data_folder(
    request: Request,
    *,
    submitted_path: str | None = None,
    error_message: str | None = None,
    success_message: str | None = None,
    status_code: int,
) -> HTMLResponse:
    folder_status = get_app_data_folder_status()
    setup_status = request.app.state.setup_status_service.build_status(
        config=request.app.state.explicit_config
    )
    request.app.state.setup_status = setup_status

    return templates.TemplateResponse(
        request=request,
        name="data_folder.html",
        context={
            "project_name": "Local Job Application Assistant",
            "folder_status": folder_status,
            "source_labels": {
                "environment": "APP_DATA_DIR environment override",
                "user_selection": "persisted user selection",
                "default": "default Documents location",
            },
            "submitted_path": submitted_path,
            "error_message": error_message,
            "success_message": success_message,
            "setup_status": setup_status,
        },
        status_code=status_code,
    )
