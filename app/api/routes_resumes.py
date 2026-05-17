from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from app.api.dependencies import (
    SessionDep,
    form_bool,
    get_app_data_root,
    read_form_data,
)
from app.db.models import (
    BlockType,
    ResumeBlock,
    ResumeBullet,
    ResumeSection,
    SectionType,
)
from app.resumes.service import ResumeService, validate_resume_upload_filename
from app.web.templating import templates

router = APIRouter(tags=["resumes"])


@router.get("/profiles/{profile_id}/resumes")
def profile_resumes(profile_id: int, request: Request, session: SessionDep):
    return templates.TemplateResponse(
        "resumes.html",
        {
            "request": request,
            "profile_id": profile_id,
            "resumes": ResumeService(session).list_resumes(profile_id),
        },
    )


@router.get("/profiles/{profile_id}/resumes/new")
def new_resume(profile_id: int, request: Request):
    return templates.TemplateResponse(
        "resume_form.html", {"request": request, "profile_id": profile_id}
    )


@router.post("/profiles/{profile_id}/resumes/new")
async def create_resume(profile_id: int, request: Request, session: SessionDep):
    data, upload = await _read_resume_create_payload(request)
    if upload is not None:
        validate_resume_upload_filename(str(upload["filename"]))
    service = ResumeService(session)
    resume = service.create_resume(
        profile_id,
        data["name"],
        data.get("target_role", ""),
        data.get("language", "en"),
        create_standard_sections=form_bool(data, "create_standard_sections"),
    )
    if upload is not None:
        service.attach_upload(
            resume.id,
            original_filename=str(upload["filename"]),
            content_type=str(upload["content_type"]),
            content=bytes(upload["content"]),
            app_data_root=get_app_data_root(request),
        )
    return RedirectResponse(f"/resumes/{resume.id}", status_code=303)


async def _read_resume_create_payload(
    request: Request,
) -> tuple[dict[str, str], dict[str, object] | None]:
    content_type = request.headers.get("content-type", "")
    if "multipart/form-data" not in content_type:
        return await read_form_data(request), None

    body = await request.body()
    boundary_marker = "boundary="
    if boundary_marker not in content_type:
        return {}, None
    boundary = content_type.split(boundary_marker, 1)[1].strip().strip('"')
    delimiter = ("--" + boundary).encode()
    data: dict[str, str] = {}
    upload: dict[str, object] | None = None
    for raw_part in body.split(delimiter):
        part = raw_part.strip(b"\r\n")
        if not part or part == b"--" or b"\r\n\r\n" not in part:
            continue
        raw_headers, content = part.split(b"\r\n\r\n", 1)
        if content.endswith(b"\r\n"):
            content = content[:-2]
        headers = raw_headers.decode("utf-8", errors="ignore")
        disposition = next(
            (
                line
                for line in headers.split("\r\n")
                if line.lower().startswith("content-disposition:")
            ),
            "",
        )
        name = _multipart_disposition_value(disposition, "name")
        filename = _multipart_disposition_value(disposition, "filename")
        if not name:
            continue
        if filename:
            content_type_line = next(
                (
                    line
                    for line in headers.split("\r\n")
                    if line.lower().startswith("content-type:")
                ),
                "",
            )
            upload = {
                "filename": filename,
                "content_type": content_type_line.split(":", 1)[1].strip()
                if ":" in content_type_line
                else "",
                "content": content,
            }
        else:
            data[name] = content.decode("utf-8", errors="ignore")
    return data, upload


def _multipart_disposition_value(disposition: str, key: str) -> str:
    prefix = f'{key}="'
    if prefix not in disposition:
        return ""
    return disposition.split(prefix, 1)[1].split('"', 1)[0]


@router.get("/resumes/{resume_id}/edit")
def edit_resume_metadata(resume_id: int, request: Request, session: SessionDep):
    return templates.TemplateResponse(
        "resume_form.html",
        {
            "request": request,
            "profile_id": None,
            "resume": ResumeService(session).get_resume(resume_id),
        },
    )


@router.post("/resumes/{resume_id}/edit")
async def update_resume_metadata(resume_id: int, request: Request, session: SessionDep):
    data = await read_form_data(request)
    ResumeService(session).update_resume(
        resume_id,
        name=data["name"],
        target_role=data.get("target_role", ""),
        language=data.get("language", "en"),
    )
    return RedirectResponse(f"/resumes/{resume_id}", status_code=303)


@router.get("/resumes/{resume_id}")
def resume_builder(resume_id: int, request: Request, session: SessionDep):
    return templates.TemplateResponse(
        "resume_builder.html",
        {"request": request, "resume": ResumeService(session).get_resume(resume_id)},
    )


@router.get("/resumes/{resume_id}/sections/new")
def new_section(resume_id: int, request: Request):
    return templates.TemplateResponse(
        "section_form.html",
        {
            "request": request,
            "resume_id": resume_id,
            "section_types": [item.value for item in SectionType],
        },
    )


@router.post("/resumes/{resume_id}/sections/new")
async def create_section(resume_id: int, request: Request, session: SessionDep):
    data = await read_form_data(request)
    ResumeService(session).add_section(
        resume_id,
        data["section_type"],
        data["title"],
        form_bool(data, "ai_edit_enabled"),
    )
    return RedirectResponse(f"/resumes/{resume_id}", status_code=303)


@router.get("/resumes/{resume_id}/sections/{section_id}")
def section_detail(
    resume_id: int,
    section_id: int,
    request: Request,
    session: SessionDep,
):
    return templates.TemplateResponse(
        "section_detail.html",
        {
            "request": request,
            "resume_id": resume_id,
            "section": session.get(ResumeSection, section_id),
        },
    )


@router.get("/resumes/{resume_id}/blocks/new")
def new_block(resume_id: int, request: Request, session: SessionDep):
    return templates.TemplateResponse(
        "block_form.html",
        {
            "request": request,
            "resume": ResumeService(session).get_resume(resume_id),
            "block": None,
            "block_types": [item.value for item in BlockType],
        },
    )


@router.post("/resumes/{resume_id}/blocks/new")
async def create_block(resume_id: int, request: Request, session: SessionDep):
    data = await read_form_data(request)
    ResumeService(session).add_block(
        int(data["section_id"]),
        block_type=data["block_type"],
        title=data.get("title", ""),
        role_title=data.get("role_title", ""),
        organisation=data.get("organisation", ""),
        subtitle=data.get("subtitle", ""),
        content=data.get("content", ""),
        location=data.get("location", ""),
        start_date=data.get("start_date", ""),
        end_date=data.get("end_date", ""),
        is_current=form_bool(data, "is_current"),
        ai_edit_enabled=form_bool(data, "ai_edit_enabled"),
    )
    return RedirectResponse(f"/resumes/{resume_id}", status_code=303)


@router.get("/resumes/{resume_id}/blocks/{block_id}/edit")
def edit_block(
    resume_id: int,
    block_id: int,
    request: Request,
    session: SessionDep,
):
    resume = ResumeService(session).get_resume(resume_id)
    return templates.TemplateResponse(
        "block_form.html",
        {
            "request": request,
            "resume": resume,
            "block": session.get(ResumeBlock, block_id),
            "block_types": [item.value for item in BlockType],
        },
    )


@router.post("/resumes/{resume_id}/blocks/{block_id}/edit")
async def update_block(
    resume_id: int,
    block_id: int,
    request: Request,
    session: SessionDep,
):
    data = await read_form_data(request)
    values = {
        key: data[key]
        for key in [
            "block_type",
            "title",
            "subtitle",
            "role_title",
            "organisation",
            "location",
            "start_date",
            "end_date",
            "content",
        ]
        if key in data
    }
    values["is_current"] = form_bool(data, "is_current")
    values["is_visible"] = form_bool(data, "is_visible")
    values["ai_edit_enabled"] = form_bool(data, "ai_edit_enabled")
    ResumeService(session).update_block(block_id, **values)
    return RedirectResponse(f"/resumes/{resume_id}", status_code=303)


@router.get("/resumes/{resume_id}/blocks/{block_id}/bullets/new")
def new_bullet(resume_id: int, block_id: int, request: Request):
    return templates.TemplateResponse(
        "bullet_form.html",
        {
            "request": request,
            "resume_id": resume_id,
            "block_id": block_id,
            "bullet": None,
            "linked_fact_ids": "",
        },
    )


@router.post("/resumes/{resume_id}/blocks/{block_id}/bullets/new")
async def create_bullet(
    resume_id: int,
    block_id: int,
    request: Request,
    session: SessionDep,
):
    data = await read_form_data(request)
    fact_ids = [
        int(value) for value in data.get("fact_ids", "").split(",") if value.strip()
    ]
    ResumeService(session).add_bullet(
        block_id,
        data["text"],
        ai_edit_enabled=form_bool(data, "ai_edit_enabled"),
        fact_link_required=form_bool(data, "fact_link_required"),
        fact_ids=fact_ids,
    )
    return RedirectResponse(f"/resumes/{resume_id}", status_code=303)


@router.get("/resumes/{resume_id}/bullets/{bullet_id}/edit")
def edit_bullet(
    resume_id: int,
    bullet_id: int,
    request: Request,
    session: SessionDep,
):
    bullet = session.get(ResumeBullet, bullet_id)
    linked_fact_ids = ""
    if bullet is not None:
        linked_fact_ids = ",".join(str(link.fact_id) for link in bullet.fact_links)
    return templates.TemplateResponse(
        "bullet_form.html",
        {
            "request": request,
            "resume_id": resume_id,
            "block_id": None,
            "bullet": bullet,
            "linked_fact_ids": linked_fact_ids,
        },
    )


@router.post("/resumes/{resume_id}/bullets/{bullet_id}/edit")
async def update_bullet(
    resume_id: int,
    bullet_id: int,
    request: Request,
    session: SessionDep,
):
    data = await read_form_data(request)
    fact_ids = None
    if "fact_ids" in data:
        raw_fact_ids = data.get("fact_ids", "").strip()
        if raw_fact_ids:
            fact_ids = [
                int(value) for value in raw_fact_ids.split(",") if value.strip()
            ]
        elif form_bool(data, "clear_fact_links"):
            fact_ids = []
    ResumeService(session).update_bullet(
        bullet_id,
        text=data["text"],
        is_visible=form_bool(data, "is_visible"),
        ai_edit_enabled=form_bool(data, "ai_edit_enabled"),
        fact_link_required=form_bool(data, "fact_link_required"),
        fact_ids=fact_ids,
    )
    return RedirectResponse(f"/resumes/{resume_id}", status_code=303)


@router.post("/resumes/{resume_id}/sections/{section_id}/move")
async def move_section(
    resume_id: int, section_id: int, request: Request, session: SessionDep
):
    data = await read_form_data(request)
    ResumeService(session).move_section(section_id, data.get("direction", "down"))
    return RedirectResponse(f"/resumes/{resume_id}", status_code=303)


@router.post("/resumes/{resume_id}/blocks/{block_id}/move")
async def move_block(
    resume_id: int, block_id: int, request: Request, session: SessionDep
):
    data = await read_form_data(request)
    ResumeService(session).move_block(block_id, data.get("direction", "down"))
    return RedirectResponse(f"/resumes/{resume_id}", status_code=303)


@router.post("/resumes/{resume_id}/bullets/{bullet_id}/move")
async def move_bullet(
    resume_id: int, bullet_id: int, request: Request, session: SessionDep
):
    data = await read_form_data(request)
    ResumeService(session).move_bullet(bullet_id, data.get("direction", "down"))
    return RedirectResponse(f"/resumes/{resume_id}", status_code=303)
