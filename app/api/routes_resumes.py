from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api.dependencies import form_bool, get_session, read_form_data
from app.db.models import BlockType, ResumeBlock, ResumeBullet, ResumeSection, SectionType
from app.resumes.service import ResumeService
from app.web.templating import templates

router = APIRouter(tags=["resumes"])


@router.get("/profiles/{profile_id}/resumes")
def profile_resumes(profile_id: int, request: Request, session: Session = Depends(get_session)):
    return templates.TemplateResponse("resumes.html", {"request": request, "profile_id": profile_id, "resumes": ResumeService(session).list_resumes(profile_id)})


@router.get("/profiles/{profile_id}/resumes/new")
def new_resume(profile_id: int, request: Request):
    return templates.TemplateResponse("resume_form.html", {"request": request, "profile_id": profile_id})


@router.post("/profiles/{profile_id}/resumes/new")
async def create_resume(profile_id: int, request: Request, session: Session = Depends(get_session)):
    data = await read_form_data(request)
    resume = ResumeService(session).create_resume(profile_id, data["name"], data.get("target_role", ""), data.get("language", "en"))
    return RedirectResponse(f"/resumes/{resume.id}", status_code=303)


@router.get("/resumes/{resume_id}")
def resume_builder(resume_id: int, request: Request, session: Session = Depends(get_session)):
    return templates.TemplateResponse("resume_builder.html", {"request": request, "resume": ResumeService(session).get_resume(resume_id)})


@router.get("/resumes/{resume_id}/sections/new")
def new_section(resume_id: int, request: Request):
    return templates.TemplateResponse("section_form.html", {"request": request, "resume_id": resume_id, "section_types": [item.value for item in SectionType]})


@router.post("/resumes/{resume_id}/sections/new")
async def create_section(resume_id: int, request: Request, session: Session = Depends(get_session)):
    data = await read_form_data(request)
    ResumeService(session).add_section(resume_id, data["section_type"], data["title"], form_bool(data, "ai_edit_enabled"))
    return RedirectResponse(f"/resumes/{resume_id}", status_code=303)


@router.get("/resumes/{resume_id}/sections/{section_id}")
def section_detail(resume_id: int, section_id: int, request: Request, session: Session = Depends(get_session)):
    return templates.TemplateResponse("section_detail.html", {"request": request, "resume_id": resume_id, "section": session.get(ResumeSection, section_id)})


@router.get("/resumes/{resume_id}/blocks/new")
def new_block(resume_id: int, request: Request, session: Session = Depends(get_session)):
    return templates.TemplateResponse("block_form.html", {"request": request, "resume": ResumeService(session).get_resume(resume_id), "block": None, "block_types": [item.value for item in BlockType]})


@router.post("/resumes/{resume_id}/blocks/new")
async def create_block(resume_id: int, request: Request, session: Session = Depends(get_session)):
    data = await read_form_data(request)
    ResumeService(session).add_block(
        int(data["section_id"]),
        block_type=data["block_type"],
        title=data.get("title", ""),
        role_title=data.get("role_title", ""),
        organisation=data.get("organisation", ""),
        content=data.get("content", ""),
        ai_edit_enabled=form_bool(data, "ai_edit_enabled"),
    )
    return RedirectResponse(f"/resumes/{resume_id}", status_code=303)


@router.get("/resumes/{resume_id}/blocks/{block_id}/edit")
def edit_block(resume_id: int, block_id: int, request: Request, session: Session = Depends(get_session)):
    resume = ResumeService(session).get_resume(resume_id)
    return templates.TemplateResponse("block_form.html", {"request": request, "resume": resume, "block": session.get(ResumeBlock, block_id), "block_types": [item.value for item in BlockType]})


@router.get("/resumes/{resume_id}/blocks/{block_id}/bullets/new")
def new_bullet(resume_id: int, block_id: int, request: Request):
    return templates.TemplateResponse("bullet_form.html", {"request": request, "resume_id": resume_id, "block_id": block_id, "bullet": None})


@router.post("/resumes/{resume_id}/blocks/{block_id}/bullets/new")
async def create_bullet(resume_id: int, block_id: int, request: Request, session: Session = Depends(get_session)):
    data = await read_form_data(request)
    ResumeService(session).add_bullet(block_id, data["text"], ai_edit_enabled=form_bool(data, "ai_edit_enabled"), fact_link_required=form_bool(data, "fact_link_required"))
    return RedirectResponse(f"/resumes/{resume_id}", status_code=303)


@router.get("/resumes/{resume_id}/bullets/{bullet_id}/edit")
def edit_bullet(resume_id: int, bullet_id: int, request: Request, session: Session = Depends(get_session)):
    return templates.TemplateResponse("bullet_form.html", {"request": request, "resume_id": resume_id, "block_id": None, "bullet": session.get(ResumeBullet, bullet_id)})
