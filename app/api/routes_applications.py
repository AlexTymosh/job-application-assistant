from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, RedirectResponse

from app.api.dependencies import SessionDep, get_app_data_root, read_form_data
from app.applications.service import ApplicationService
from app.resumes.renderer import render_resume_html, render_resume_html_from_content
from app.resumes.service import ResumeService
from app.settings.service import SettingsService
from app.web.templating import templates

router = APIRouter(prefix="/applications", tags=["applications"])


def _active_profile_id(session: SessionDep) -> int:
    return SettingsService(session).require_active_profile().id


def _guarded_application(application_id: int, session: SessionDep):
    return ApplicationService(session).get_profile_application(
        application_id, _active_profile_id(session)
    )


@router.get("")
def applications(request: Request, session: SessionDep):
    settings = SettingsService(session)
    active_profile = settings.get_active_profile()
    applications_list = (
        ApplicationService(session).list_applications(active_profile.id)
        if active_profile
        else []
    )
    return templates.TemplateResponse(
        "applications.html",
        {
            "request": request,
            "applications": applications_list,
            "active_profile": active_profile,
        },
    )


@router.get("/new")
def new_application(request: Request, session: SessionDep):
    settings = SettingsService(session)
    active_profile = settings.require_active_profile()
    resumes = ResumeService(session).list_resumes(active_profile.id)
    return templates.TemplateResponse(
        "applications_new.html",
        {"request": request, "active_profile": active_profile, "resumes": resumes},
    )


@router.post("/adapt")
async def adapt_application(request: Request, session: SessionDep):
    data = await read_form_data(request)
    active_profile = SettingsService(session).require_active_profile()
    application = ApplicationService(session).create_application(
        profile_id=active_profile.id,
        resume_id=int(data["resume_id"]),
        raw_job_text=data["raw_job_text"],
        source_url=data.get("source_url", ""),
        job_title=data.get("job_title", ""),
        company_name=data.get("company_name", ""),
    )
    ApplicationService(session).adapt_application(application.id)
    return RedirectResponse(
        f"/applications/{application.id}/tailored-resume", status_code=303
    )


@router.get("/{application_id}")
def application_detail_redirect(application_id: int, session: SessionDep):
    _guarded_application(application_id, session)
    return RedirectResponse(
        f"/applications/{application_id}/tailored-resume", status_code=303
    )


@router.get("/{application_id}/tailored-resume")
def tailored_resume(application_id: int, request: Request, session: SessionDep):
    application = _guarded_application(application_id, session)
    service = ApplicationService(session)
    tailored = (
        service.get_tailored_resume(application_id)
        if application.tailored_resume_id
        else None
    )
    cover_letter = service.latest_cover_letter(application_id)
    base_resume = ResumeService(session).get_resume(application.base_resume_id)
    return templates.TemplateResponse(
        "tailored_resume.html",
        {
            "request": request,
            "application": application,
            "base_resume": base_resume,
            "tailored": tailored,
            "cover_letter": cover_letter,
            "base_preview_html": render_resume_html(base_resume),
            "tailored_preview_html": render_resume_html_from_content(
                tailored.content_json
            )
            if tailored
            else "",
        },
    )


@router.post("/{application_id}/tailored-resume")
async def save_tailored_resume(application_id: int, session: SessionDep):
    _guarded_application(application_id, session)
    return RedirectResponse(
        f"/applications/{application_id}/tailored-resume", status_code=303
    )


@router.post("/{application_id}/tailored-resume/export/pdf")
def export_tailored_resume_pdf(
    application_id: int, request: Request, session: SessionDep
):
    _guarded_application(application_id, session)
    ApplicationService(session).export_tailored_resume(
        application_id, "pdf", get_app_data_root(request)
    )
    return RedirectResponse(
        f"/applications/{application_id}/tailored-resume/exports/pdf/download",
        status_code=303,
    )


@router.post("/{application_id}/tailored-resume/export/docx")
def export_tailored_resume_docx(
    application_id: int, request: Request, session: SessionDep
):
    _guarded_application(application_id, session)
    ApplicationService(session).export_tailored_resume(
        application_id, "docx", get_app_data_root(request)
    )
    return RedirectResponse(
        f"/applications/{application_id}/tailored-resume/exports/docx/download",
        status_code=303,
    )


@router.get("/{application_id}/cover-letter/download")
def download_cover_letter(application_id: int, request: Request, session: SessionDep):
    _guarded_application(application_id, session)
    service = ApplicationService(session)
    path = service.cover_letter_text_path(application_id, get_app_data_root(request))
    if not path.exists():
        path = service.export_cover_letter_text(
            application_id, get_app_data_root(request)
        )
    return FileResponse(path, filename=path.name, media_type="text/plain")


@router.get("/{application_id}/tailored-resume/exports/{export_format}/download")
def download_tailored_resume(
    application_id: int, export_format: str, request: Request, session: SessionDep
):
    _guarded_application(application_id, session)
    service = ApplicationService(session)
    path = service.tailored_resume_export_path(
        application_id, export_format, get_app_data_root(request)
    )
    if not path.exists():
        path = service.export_tailored_resume(
            application_id, export_format, get_app_data_root(request)
        )
    return FileResponse(path, filename=path.name)
