from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, RedirectResponse

from app.api.dependencies import (
    SessionDep,
    get_app_data_root,
    read_form_data,
    read_form_multi_data,
    require_active_profile_resume,
    require_active_profile_workspace,
)
from app.resumes.renderer import render_resume_html
from app.resumes.service import (
    STANDARD_SECTIONS,
    ResumeService,
)
from app.web.templating import templates

router = APIRouter(tags=["resumes"])


@router.get("/profiles/{profile_id}/resumes")
def profile_resumes(profile_id: int, request: Request, session: SessionDep):
    require_active_profile_workspace(profile_id, session)
    return templates.TemplateResponse(
        "resumes.html",
        {
            "request": request,
            "profile_id": profile_id,
            "resumes": ResumeService(session).list_resumes(profile_id),
        },
    )


@router.get("/profiles/{profile_id}/resumes/new")
def new_resume(profile_id: int, request: Request, session: SessionDep):
    require_active_profile_workspace(profile_id, session)
    return templates.TemplateResponse(
        "resume_form.html", {"request": request, "profile_id": profile_id}
    )


@router.post("/profiles/{profile_id}/resumes/new")
async def create_resume(profile_id: int, request: Request, session: SessionDep):
    require_active_profile_workspace(profile_id, session)
    data = await read_form_data(request)
    resume = ResumeService(session).create_resume(
        profile_id,
        data["name"],
        data.get("target_role", ""),
        data.get("language", "en"),
        create_standard_sections=True,
        is_default=data.get("is_default") == "on",
    )
    return RedirectResponse(f"/resumes/{resume.id}/builder", status_code=303)


@router.get("/resumes/{resume_id}")
def resume_detail_redirect(resume_id: int, session: SessionDep):
    require_active_profile_resume(resume_id, session)
    return RedirectResponse(f"/resumes/{resume_id}/builder", status_code=303)


@router.get("/resumes/{resume_id}/edit")
def edit_resume_metadata(resume_id: int, request: Request, session: SessionDep):
    resume = require_active_profile_resume(resume_id, session)
    return templates.TemplateResponse(
        "resume_form.html",
        {
            "request": request,
            "profile_id": None,
            "resume": resume,
        },
    )


@router.post("/resumes/{resume_id}/edit")
async def update_resume_metadata(resume_id: int, request: Request, session: SessionDep):
    require_active_profile_resume(resume_id, session)
    data = await read_form_data(request)
    ResumeService(session).update_resume(
        resume_id,
        name=data["name"],
        target_role=data.get("target_role", ""),
        language=data.get("language", "en"),
    )
    return RedirectResponse(f"/resumes/{resume_id}/builder", status_code=303)


@router.get("/resumes/{resume_id}/builder")
def builder_default(resume_id: int, session: SessionDep):
    require_active_profile_resume(resume_id, session)
    return RedirectResponse(f"/resumes/{resume_id}/builder/header", status_code=303)


@router.get("/resumes/{resume_id}/builder/{section_type}")
def resume_builder_section(
    resume_id: int, section_type: str, request: Request, session: SessionDep
):
    service = ResumeService(session)
    resume = require_active_profile_resume(resume_id, session)
    service.create_standard_skeleton(resume_id)
    resume = require_active_profile_resume(resume_id, session)
    section = next(
        (item for item in resume.sections if item.section_type == section_type), None
    )
    if section is None:
        return RedirectResponse(f"/resumes/{resume_id}/builder/header", status_code=303)
    return templates.TemplateResponse(
        "resume_builder.html",
        {
            "request": request,
            "resume": resume,
            "section": section,
            "sections_nav": STANDARD_SECTIONS,
            "section_type": section_type,
            "preview_html": render_resume_html(resume),
        },
    )


@router.post("/resumes/{resume_id}/builder/{section_type}")
async def save_resume_builder_section(
    resume_id: int, section_type: str, request: Request, session: SessionDep
):
    require_active_profile_resume(resume_id, session)
    data = await read_form_multi_data(request)
    ResumeService(session).save_section(resume_id, section_type, data)
    return RedirectResponse(
        f"/resumes/{resume_id}/builder/{section_type}", status_code=303
    )


@router.post("/resumes/{resume_id}/export/pdf")
def export_base_resume_pdf(resume_id: int, request: Request, session: SessionDep):
    require_active_profile_resume(resume_id, session)
    ResumeService(session).export_base_resume(
        resume_id, "pdf", get_app_data_root(request)
    )
    return RedirectResponse(
        f"/resumes/{resume_id}/exports/pdf/download", status_code=303
    )


@router.post("/resumes/{resume_id}/export/docx")
def export_base_resume_docx(resume_id: int, request: Request, session: SessionDep):
    require_active_profile_resume(resume_id, session)
    ResumeService(session).export_base_resume(
        resume_id, "docx", get_app_data_root(request)
    )
    return RedirectResponse(
        f"/resumes/{resume_id}/exports/docx/download", status_code=303
    )


@router.post("/resumes/{resume_id}/exports")
async def export_base_resume_legacy(
    resume_id: int, request: Request, session: SessionDep
):
    require_active_profile_resume(resume_id, session)
    data = await read_form_data(request)
    export_format = data.get("format", "pdf")
    ResumeService(session).export_base_resume(
        resume_id, export_format, get_app_data_root(request)
    )
    return RedirectResponse(
        f"/resumes/{resume_id}/exports/{export_format}/download", status_code=303
    )


@router.get("/resumes/{resume_id}/exports/{export_format}/download")
def download_base_resume(
    resume_id: int, export_format: str, request: Request, session: SessionDep
):
    service = ResumeService(session)
    require_active_profile_resume(resume_id, session)
    path = service.base_resume_export_path(
        resume_id, export_format, get_app_data_root(request)
    )
    if not path.exists():
        path = service.export_base_resume(
            resume_id, export_format, get_app_data_root(request)
        )
    return FileResponse(path, filename=path.name)
