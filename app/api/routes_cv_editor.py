from __future__ import annotations

from contextlib import suppress
from urllib.parse import parse_qs

from fastapi import APIRouter, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from app.managed_cv.editor_service import (
    ALLOWED_CLAIM_LEVEL_OPTIONS,
    FACT_CATEGORY_OPTIONS,
    ManagedCvEditorError,
    ManagedCvEditorService,
    build_managed_cv_editor_service,
)
from app.managed_cv.form_models import (
    ManagedCvEditorFormError,
    parse_cv_block_edit_form,
    parse_fact_create_form,
    parse_fact_edit_form,
)
from app.managed_cv.repository import ManagedCvStorageError
from app.web.templating import templates

router = APIRouter(tags=["managed-cv-editor"])


@router.get("/profiles/cv", response_class=HTMLResponse)
async def managed_cv_index(request: Request) -> HTMLResponse:
    try:
        state = _editor_service(request).load_index()
    except ManagedCvEditorError as exc:
        return _render_storage_error(request, str(exc), status.HTTP_400_BAD_REQUEST)
    return templates.TemplateResponse(
        request=request,
        name="cv_editor_index.html",
        context={
            "project_name": "Local Job Application Assistant",
            "state": state,
        },
        status_code=status.HTTP_200_OK,
    )


@router.get("/profiles/cv/variants/{variant_id}", response_class=HTMLResponse)
async def managed_cv_variant(request: Request, variant_id: str) -> HTMLResponse:
    try:
        detail = _editor_service(request).load_variant_detail(variant_id)
    except ManagedCvEditorError as exc:
        return _render_storage_error(request, str(exc), status.HTTP_404_NOT_FOUND)
    return templates.TemplateResponse(
        request=request,
        name="cv_variant_detail.html",
        context={
            "project_name": "Local Job Application Assistant",
            "detail": detail,
        },
        status_code=status.HTTP_200_OK,
    )


@router.get("/profiles/cv/blocks/{block_id}/edit", response_class=HTMLResponse)
async def edit_cv_block(request: Request, block_id: str) -> HTMLResponse:
    return _render_block_form(
        request,
        block_id=block_id,
        status_code=status.HTTP_200_OK,
    )


@router.post("/profiles/cv/blocks/{block_id}", response_class=HTMLResponse)
async def update_cv_block(request: Request, block_id: str) -> Response:
    form_values = await _read_urlencoded_form(request)
    try:
        form = parse_cv_block_edit_form(form_values)
        _editor_service(request).update_block(block_id, form)
    except (
        ManagedCvEditorFormError,
        ManagedCvEditorError,
        ManagedCvStorageError,
    ) as exc:
        return _render_block_form(
            request,
            block_id=block_id,
            submitted_values=form_values,
            error_message=str(exc),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    return RedirectResponse(
        url=f"/profiles/cv/blocks/{block_id}/edit?success=1",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/profiles/facts", response_class=HTMLResponse)
async def facts(request: Request) -> HTMLResponse:
    try:
        state = _editor_service(request).load_facts()
    except ManagedCvEditorError as exc:
        return _render_storage_error(request, str(exc), status.HTTP_400_BAD_REQUEST)
    return templates.TemplateResponse(
        request=request,
        name="facts.html",
        context={
            "project_name": "Local Job Application Assistant",
            "state": state,
        },
        status_code=status.HTTP_200_OK,
    )


@router.get("/profiles/facts/new", response_class=HTMLResponse)
async def new_fact(request: Request) -> HTMLResponse:
    return _render_fact_form(
        request,
        mode="create",
        action_url="/profiles/facts",
        status_code=status.HTTP_200_OK,
    )


@router.post("/profiles/facts", response_class=HTMLResponse)
async def create_fact(request: Request) -> Response:
    form_values = await _read_urlencoded_form(request)
    try:
        form = parse_fact_create_form(form_values)
        _editor_service(request).create_fact(form)
    except (
        ManagedCvEditorFormError,
        ManagedCvEditorError,
        ManagedCvStorageError,
    ) as exc:
        return _render_fact_form(
            request,
            mode="create",
            action_url="/profiles/facts",
            submitted_values=form_values,
            error_message=str(exc),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    return RedirectResponse(
        url="/profiles/facts", status_code=status.HTTP_303_SEE_OTHER
    )


@router.get("/profiles/facts/{fact_id}/edit", response_class=HTMLResponse)
async def edit_fact(request: Request, fact_id: str) -> HTMLResponse:
    try:
        fact = _editor_service(request).get_fact_for_edit(fact_id)
    except ManagedCvEditorError as exc:
        return _render_storage_error(request, str(exc), status.HTTP_404_NOT_FOUND)
    return _render_fact_form(
        request,
        mode="edit",
        action_url=f"/profiles/facts/{fact_id}",
        fact=fact,
        status_code=status.HTTP_200_OK,
    )


@router.post("/profiles/facts/{fact_id}", response_class=HTMLResponse)
async def update_fact(request: Request, fact_id: str) -> Response:
    form_values = await _read_urlencoded_form(request)
    try:
        form = parse_fact_edit_form(form_values)
        _editor_service(request).update_fact(fact_id, form)
    except (
        ManagedCvEditorFormError,
        ManagedCvEditorError,
        ManagedCvStorageError,
    ) as exc:
        fact = None
        with suppress(ManagedCvEditorError):
            fact = _editor_service(request).get_fact_for_edit(fact_id)
        return _render_fact_form(
            request,
            mode="edit",
            action_url=f"/profiles/facts/{fact_id}",
            fact=fact,
            submitted_values=form_values,
            error_message=str(exc),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    return RedirectResponse(
        url="/profiles/facts", status_code=status.HTTP_303_SEE_OTHER
    )


async def _read_urlencoded_form(request: Request) -> dict[str, str | list[str]]:
    body = await request.body()
    parsed = parse_qs(body.decode("utf-8"), keep_blank_values=True)
    return {
        key: values if len(values) > 1 else values[0] for key, values in parsed.items()
    }


def _editor_service(request: Request) -> ManagedCvEditorService:
    app_settings_service = getattr(request.app.state, "app_settings_service", None)
    if app_settings_service is None:
        raise ManagedCvEditorError("App settings storage is not available.")
    return build_managed_cv_editor_service(app_settings_service.session_factory)


def _render_block_form(
    request: Request,
    *,
    block_id: str,
    submitted_values: dict[str, str | list[str]] | None = None,
    error_message: str | None = None,
    status_code: int,
) -> HTMLResponse:
    try:
        state = _editor_service(request).load_block_edit(block_id)
    except ManagedCvEditorError as exc:
        return _render_storage_error(request, str(exc), status.HTTP_404_NOT_FOUND)
    return templates.TemplateResponse(
        request=request,
        name="cv_block_edit.html",
        context={
            "project_name": "Local Job Application Assistant",
            "state": state,
            "submitted_values": submitted_values or {},
            "error_message": error_message,
            "success_message": "Block saved."
            if request.query_params.get("success")
            else None,
        },
        status_code=status_code,
    )


def _render_fact_form(
    request: Request,
    *,
    mode: str,
    action_url: str,
    fact: object | None = None,
    submitted_values: dict[str, str | list[str]] | None = None,
    error_message: str | None = None,
    status_code: int,
) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="fact_form.html",
        context={
            "project_name": "Local Job Application Assistant",
            "mode": mode,
            "action_url": action_url,
            "fact": fact,
            "submitted_values": submitted_values or {},
            "error_message": error_message,
            "category_options": FACT_CATEGORY_OPTIONS,
            "claim_level_options": ALLOWED_CLAIM_LEVEL_OPTIONS,
        },
        status_code=status_code,
    )


def _render_storage_error(
    request: Request, message: str, status_code: int
) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="error.html",
        context={
            "project_name": "Local Job Application Assistant",
            "message": message,
        },
        status_code=status_code,
    )
