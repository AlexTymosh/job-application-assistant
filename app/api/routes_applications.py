from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy import select

from app.api.dependencies import SessionDep, get_app_data_root, read_form_data
from app.applications.service import ApplicationService
from app.core.errors import (
    ActiveProfileRequiredError,
    ApplicationWorkflowError,
    ProfileScopeError,
)
from app.cover_letters.service import CoverLetterService
from app.db.models import Artifact, ProposalStatus, TailoredResumeSnapshot
from app.settings.service import SettingsService
from app.web.templating import templates

router = APIRouter(prefix="/applications", tags=["applications"])


@router.get("")
def applications(request: Request, session: SessionDep):
    settings = SettingsService(session)
    active_profile = settings.get_active_profile()
    resumes = []
    applications_list = []
    if active_profile is not None:
        from app.resumes.service import ResumeService

        resumes = ResumeService(session).list_resumes(active_profile.id)
        applications_list = ApplicationService(session).list_applications(
            active_profile.id
        )
    return templates.TemplateResponse(
        "applications.html",
        {
            "request": request,
            "active_profile": active_profile,
            "resumes": resumes,
            "applications": applications_list,
        },
    )


@router.get("/new")
def new_application(request: Request, session: SessionDep):
    return applications(request, session)


@router.post("/adapt")
async def adapt_application(request: Request, session: SessionDep):
    data = await read_form_data(request)
    active_profile = SettingsService(session).get_active_profile()
    if active_profile is None:
        raise ActiveProfileRequiredError("Select an active profile first.")
    if not data.get("resume_id"):
        raise ApplicationWorkflowError(
            "Create and select a resume before adapting a job description."
        )
    app = ApplicationService(session).adapt_application(
        profile_id=active_profile.id,
        resume_id=int(data["resume_id"]),
        job_title=data.get("job_title", ""),
        company_name=data.get("company_name", ""),
        source_url=data.get("source_url", ""),
        raw_job_text=data.get("raw_job_text", ""),
    )
    return RedirectResponse(f"/applications/{app.id}", status_code=303)


@router.post("/new")
async def create_application(request: Request, session: SessionDep):
    return await adapt_application(request, session)


def _require_active_profile_application(application_id: int, session: SessionDep):
    app = ApplicationService(session).get_application(application_id)
    active_profile = SettingsService(session).get_active_profile()
    if active_profile is None:
        raise ActiveProfileRequiredError("Select an active profile first.")
    if app.profile_id != active_profile.id:
        raise ProfileScopeError("Application not found for the active profile.")
    return app


@router.get("/{application_id}")
def application_detail(application_id: int, request: Request, session: SessionDep):
    service = ApplicationService(session)
    app = _require_active_profile_application(application_id, session)
    run = service.latest_tailoring_run(application_id)
    snapshot = service.latest_snapshot(application_id)
    letter = CoverLetterService(session).latest(application_id)
    artifacts = list(
        session.scalars(
            select(Artifact).where(Artifact.application_id == application_id)
        )
    )
    return templates.TemplateResponse(
        "application_detail.html",
        {
            "request": request,
            "application": app,
            "run": run,
            "snapshot": snapshot,
            "letter": letter,
            "artifacts": artifacts,
            "accepted": ProposalStatus.ACCEPTED.value,
            "accepted_edited": ProposalStatus.ACCEPTED_EDITED.value,
            "rejected": ProposalStatus.REJECTED.value,
        },
    )


@router.post("/{application_id}/review")
async def save_review(application_id: int, request: Request, session: SessionDep):
    _require_active_profile_application(application_id, session)
    data = await read_form_data(request)
    decisions: dict[int, str] = {}
    edited: dict[int, str] = {}
    for key, value in data.items():
        if key.startswith("decision_"):
            decisions[int(key.removeprefix("decision_"))] = value
        if key.startswith("after_text_"):
            edited[int(key.removeprefix("after_text_"))] = value
    ApplicationService(session).save_review_decisions(application_id, decisions, edited)
    if data.get("cover_letter_id"):
        CoverLetterService(session).update_content(
            int(data["cover_letter_id"]), data.get("cover_letter_content", "")
        )
    return RedirectResponse(f"/applications/{application_id}", status_code=303)


@router.post("/{application_id}/extract")
def extract(application_id: int, session: SessionDep):
    _require_active_profile_application(application_id, session)
    ApplicationService(session).extract_requirements(application_id)
    return RedirectResponse(f"/applications/{application_id}", status_code=303)


@router.post("/{application_id}/tailoring/run")
def run_tailoring(application_id: int, session: SessionDep):
    _require_active_profile_application(application_id, session)
    ApplicationService(session).tailoring_service().run_tailoring(application_id)
    return RedirectResponse(f"/applications/{application_id}", status_code=303)


@router.get("/{application_id}/tailoring")
def tailoring(application_id: int, request: Request, session: SessionDep):
    return application_detail(application_id, request, session)


@router.post("/{application_id}/tailoring/decide")
async def decide(application_id: int, request: Request, session: SessionDep):
    return await save_review(application_id, request, session)


@router.post("/{application_id}/snapshot")
def create_snapshot(application_id: int, session: SessionDep):
    _require_active_profile_application(application_id, session)
    snapshot = ApplicationService(session).create_snapshot(application_id)
    return RedirectResponse(
        f"/applications/{application_id}/exports?snapshot_id={snapshot.id}",
        status_code=303,
    )


@router.get("/{application_id}/exports")
def exports(
    application_id: int,
    request: Request,
    session: SessionDep,
    snapshot_id: int | None = None,
):
    service = ApplicationService(session)
    application = _require_active_profile_application(application_id, session)
    snapshot = None

    if snapshot_id is not None:
        snapshot = session.get(TailoredResumeSnapshot, snapshot_id)
        if snapshot is None or snapshot.application_id != application_id:
            raise HTTPException(status_code=404, detail="Snapshot not found.")
    else:
        snapshot = service.latest_snapshot(application_id)

    artifacts = list(
        session.scalars(
            select(Artifact).where(Artifact.application_id == application_id)
        )
    )

    return templates.TemplateResponse(
        "exports.html",
        {
            "request": request,
            "application": application,
            "snapshot": snapshot,
            "artifacts": artifacts,
        },
    )


@router.post("/{application_id}/exports")
async def run_exports(application_id: int, request: Request, session: SessionDep):
    _require_active_profile_application(application_id, session)
    data = await read_form_data(request)
    ApplicationService(session).export_snapshot(
        int(data["snapshot_id"]), get_app_data_root(request)
    )
    return RedirectResponse(f"/applications/{application_id}", status_code=303)


@router.post("/{application_id}/events/copy")
async def record_copy(application_id: int, request: Request, session: SessionDep):
    _require_active_profile_application(application_id, session)
    data = await read_form_data(request)
    ApplicationService(session).record_copy_event(
        application_id,
        data.get("target_type", "resume_text"),
        data.get("target_id", ""),
        data.get("label", "content"),
    )
    return RedirectResponse(f"/applications/{application_id}", status_code=303)


@router.post("/{application_id}/events/download")
async def record_download(application_id: int, request: Request, session: SessionDep):
    _require_active_profile_application(application_id, session)
    data = await read_form_data(request)
    ApplicationService(session).record_download_event(
        application_id,
        int(data.get("artifact_id", "0")),
        data.get("label", "artifact"),
    )
    return RedirectResponse(f"/applications/{application_id}", status_code=303)


@router.post("/{application_id}/mark-applied")
def mark_applied(application_id: int, session: SessionDep):
    _require_active_profile_application(application_id, session)
    ApplicationService(session).mark_manually_applied(application_id)
    return RedirectResponse(f"/applications/{application_id}", status_code=303)


@router.get("/{application_id}/download/{artifact_id}")
def download(
    application_id: int, artifact_id: int, request: Request, session: SessionDep
):
    _require_active_profile_application(application_id, session)
    artifact = session.get(Artifact, artifact_id)
    if artifact is None or artifact.application_id != application_id:
        raise HTTPException(status_code=404, detail="Artifact not found.")
    root = get_app_data_root(request).resolve()
    path = (root / artifact.relative_path).resolve()
    if root not in path.parents and path != root:
        raise HTTPException(status_code=400, detail="Unsafe artifact path.")
    if not path.exists():
        raise HTTPException(status_code=404, detail="Artifact file not found.")
    ApplicationService(session).record_download_event(
        application_id, artifact.id, artifact.artifact_type
    )
    return FileResponse(path, filename=path.name)
