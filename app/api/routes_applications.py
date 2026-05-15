from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_app_data_root, get_session, read_form_data
from app.applications.service import ApplicationService
from app.cover_letters.service import CoverLetterService
from app.db.models import Artifact, PersonProfile, ProposalStatus, Resume
from app.tailoring.service import TailoringService
from app.web.templating import templates

router = APIRouter(prefix="/applications", tags=["applications"])


@router.get("")
def applications(request: Request, session: Session = Depends(get_session)):
    return templates.TemplateResponse(
        "applications.html",
        {
            "request": request,
            "applications": ApplicationService(session).list_applications(),
        },
    )


@router.get("/new")
def new_application(request: Request, session: Session = Depends(get_session)):
    profiles = list(session.scalars(select(PersonProfile).order_by(PersonProfile.display_name)))
    resumes = list(session.scalars(select(Resume).order_by(Resume.name)))
    return templates.TemplateResponse(
        "application_form.html",
        {"request": request, "profiles": profiles, "resumes": resumes},
    )


@router.post("/new")
async def create_application(request: Request, session: Session = Depends(get_session)):
    data = await read_form_data(request)
    profile_id = int(data["profile_id"])
    resume_id = int(data["resume_id"])
    resume = session.get(Resume, resume_id)
    if resume is None or resume.profile_id != profile_id:
        raise HTTPException(status_code=400, detail="Resume must belong to the selected profile.")
    app = ApplicationService(session).create_application(
        profile_id=profile_id,
        resume_id=resume_id,
        job_title=data.get("job_title", ""),
        company_name=data.get("company_name", ""),
        source_url=data.get("source_url", ""),
        raw_job_text=data["raw_job_text"],
    )
    return RedirectResponse(f"/applications/{app.id}", status_code=303)


@router.get("/{application_id}")
def application_detail(application_id: int, request: Request, session: Session = Depends(get_session)):
    service = ApplicationService(session)
    app = service.get_application(application_id)
    run = service.latest_tailoring_run(application_id)
    letter = CoverLetterService(session).latest(application_id)
    artifacts = list(session.scalars(select(Artifact).where(Artifact.application_id == application_id)))
    return templates.TemplateResponse(
        "application_detail.html",
        {
            "request": request,
            "application": app,
            "run": run,
            "letter": letter,
            "artifacts": artifacts,
        },
    )


@router.post("/{application_id}/extract")
def extract(application_id: int, session: Session = Depends(get_session)):
    ApplicationService(session).extract_requirements(application_id)
    return RedirectResponse(f"/applications/{application_id}", status_code=303)


@router.post("/{application_id}/tailoring/run")
def run_tailoring(application_id: int, session: Session = Depends(get_session)):
    TailoringService(session).run_tailoring(application_id)
    return RedirectResponse(f"/applications/{application_id}/tailoring", status_code=303)


@router.get("/{application_id}/tailoring")
def tailoring(application_id: int, request: Request, session: Session = Depends(get_session)):
    service = ApplicationService(session)
    app = service.get_application(application_id)
    run = service.latest_tailoring_run(application_id)
    return templates.TemplateResponse(
        "tailoring_review.html",
        {
            "request": request,
            "application": app,
            "run": run,
            "accepted": ProposalStatus.ACCEPTED.value,
            "rejected": ProposalStatus.REJECTED.value,
        },
    )


@router.post("/{application_id}/tailoring/decide")
async def decide(application_id: int, request: Request, session: Session = Depends(get_session)):
    data = await read_form_data(request)
    decisions: dict[int, str] = {}
    for key, value in data.items():
        if key.startswith("decision_"):
            decisions[int(key.removeprefix("decision_"))] = value
    ApplicationService(session).decide_proposals(decisions)
    return RedirectResponse(f"/applications/{application_id}/tailoring", status_code=303)


@router.post("/{application_id}/snapshot")
def create_snapshot(application_id: int, session: Session = Depends(get_session)):
    snapshot = ApplicationService(session).create_snapshot(application_id)
    return RedirectResponse(
        f"/applications/{application_id}/exports?snapshot_id={snapshot.id}",
        status_code=303,
    )


@router.get("/{application_id}/exports")
def exports(
    application_id: int,
    request: Request,
    snapshot_id: int | None = None,
    session: Session = Depends(get_session),
):
    app = ApplicationService(session).get_application(application_id)
    artifacts = list(session.scalars(select(Artifact).where(Artifact.application_id == application_id)))
    return templates.TemplateResponse(
        "exports.html",
        {
            "request": request,
            "application": app,
            "snapshot_id": snapshot_id,
            "artifacts": artifacts,
        },
    )


@router.post("/{application_id}/exports")
async def run_exports(
    application_id: int,
    request: Request,
    snapshot_id: int | None = None,
    session: Session = Depends(get_session),
):
    data = await read_form_data(request)
    ApplicationService(session).export_snapshot(int(data["snapshot_id"]), get_app_data_root(request))
    return RedirectResponse(f"/applications/{application_id}", status_code=303)


@router.get("/{application_id}/download/{artifact_id}")
def download(
    application_id: int,
    artifact_id: int,
    request: Request,
    session: Session = Depends(get_session),
):
    artifact = session.get(Artifact, artifact_id)
    if artifact is None or artifact.application_id != application_id:
        raise HTTPException(status_code=404, detail="Artifact not found.")
    root = get_app_data_root(request).resolve()
    path = (root / artifact.relative_path).resolve()
    if root not in path.parents and path != root:
        raise HTTPException(status_code=400, detail="Unsafe artifact path.")
    if not path.exists():
        raise HTTPException(status_code=404, detail="Artifact file not found.")
    return FileResponse(path)


@router.get("/{application_id}/cover-letter")
def cover_letter(application_id: int, request: Request, session: Session = Depends(get_session)):
    app = ApplicationService(session).get_application(application_id)
    letter = CoverLetterService(session).latest(application_id)
    return templates.TemplateResponse("cover_letter.html", {"request": request, "application": app, "letter": letter})


@router.post("/{application_id}/cover-letter")
def generate_cover_letter(application_id: int, session: Session = Depends(get_session)):
    CoverLetterService(session).generate(application_id)
    return RedirectResponse(f"/applications/{application_id}/cover-letter", status_code=303)
