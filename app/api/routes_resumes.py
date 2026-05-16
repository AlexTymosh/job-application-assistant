from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from app.api.dependencies import (
    SessionDep,
    form_bool,
    get_app_data_root,
    read_form_data,
)
from app.core.errors import ResumeBuilderError, ValidationAppError
from app.db.models import (
    BlockType,
    ResumeBlock,
    ResumeBullet,
    ResumeSection,
    SectionType,
)
from app.resumes.service import ResumeService
from app.settings.service import SettingsService
from app.web.templating import templates

router = APIRouter(tags=["resumes"])

_ALLOWED_UPLOAD_EXTENSIONS = {".pdf", ".doc", ".docx"}


def _safe_upload_name(filename: str) -> str:
    original = Path(filename or "uploaded-resume").name
    suffix = Path(original).suffix.lower()
    if suffix not in _ALLOWED_UPLOAD_EXTENSIONS:
        raise ValidationAppError("Upload a PDF, DOC, or DOCX resume file.")
    stem = "".join(
        char if char.isalnum() or char in {"-", "_"} else "-"
        for char in Path(original).stem
    ).strip("-")
    return f"{stem or 'resume'}-{uuid4().hex}{suffix}"


def _parse_multipart_form(
    body: bytes, content_type: str
) -> tuple[dict[str, str], tuple[str, bytes] | None]:
    marker = "boundary="
    if marker not in content_type:
        raise ValidationAppError("Invalid upload request.")
    boundary = content_type.split(marker, 1)[1].strip().strip('"')
    delimiter = ("--" + boundary).encode()
    data: dict[str, str] = {}
    upload: tuple[str, bytes] | None = None
    for raw_part in body.split(delimiter):
        part = raw_part.strip(b"\r\n")
        if not part or part == b"--" or b"\r\n\r\n" not in part:
            continue
        raw_headers, content = part.split(b"\r\n\r\n", 1)
        content = content.removesuffix(b"\r\n").removesuffix(b"--")
        headers = raw_headers.decode("utf-8", errors="ignore")
        if 'name="' not in headers:
            continue
        name = headers.split('name="', 1)[1].split('"', 1)[0]
        filename = ""
        if 'filename="' in headers:
            filename = headers.split('filename="', 1)[1].split('"', 1)[0]
        if filename:
            upload = (filename, content)
        else:
            data[name] = content.decode("utf-8", errors="ignore")
    return data, upload


def _store_resume_upload(request: Request, upload: tuple[str, bytes] | None) -> str:
    if upload is None or not upload[0]:
        return ""
    filename = _safe_upload_name(upload[0])
    root = get_app_data_root(request).resolve()
    upload_dir = root / "artifacts" / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    destination = (upload_dir / filename).resolve()
    if root not in destination.parents:
        raise ValidationAppError("Unsafe upload path.")
    destination.write_bytes(upload[1])
    return destination.relative_to(root).as_posix()


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
    content_type = request.headers.get("content-type", "")
    upload_path = ""
    if content_type.startswith("multipart/form-data"):
        data, upload = _parse_multipart_form(await request.body(), content_type)
        upload_path = _store_resume_upload(request, upload)
    else:
        data = await read_form_data(request)
    resume = ResumeService(session).create_resume(
        profile_id,
        data["name"],
        data.get("target_role", ""),
        data.get("language", "en"),
        create_standard_sections=form_bool(data, "create_standard_sections"),
    )
    if upload_path:
        request.app.state.last_resume_upload_path = upload_path
    return RedirectResponse(f"/resumes/{resume.id}", status_code=303)


@router.get("/resumes/{resume_id}/edit")
def edit_resume_metadata(resume_id: int, request: Request, session: SessionDep):
    return templates.TemplateResponse(
        "resume_form.html",
        {
            "request": request,
            "profile_id": ResumeService(session).get_resume(resume_id).profile_id,
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
    ResumeService(session).update_block(
        block_id,
        block_type=data.get("block_type", "custom"),
        title=data.get("title", ""),
        subtitle=data.get("subtitle", ""),
        role_title=data.get("role_title", ""),
        organisation=data.get("organisation", ""),
        location=data.get("location", ""),
        start_date=data.get("start_date", ""),
        end_date=data.get("end_date", ""),
        content=data.get("content", ""),
        is_current=form_bool(data, "is_current"),
        is_visible=form_bool(data, "is_visible"),
        ai_edit_enabled=form_bool(data, "ai_edit_enabled"),
    )
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


@router.post("/resumes/{resume_id}/sections/{section_id}/prompt")
async def update_section_prompt(
    resume_id: int, section_id: int, request: Request, session: SessionDep
):
    data = await read_form_data(request)
    section = session.get(ResumeSection, section_id)
    if section is None or section.resume_id != resume_id:
        raise ResumeBuilderError("Section not found for this resume.")
    SettingsService(session).upsert_prompt_instruction(
        block_type=data.get("block_type", "description_custom_block"),
        user_prompt_template=data.get("user_prompt_template", ""),
        scope=f"section:{section_id}",
        section_type=section.section_type,
        name=f"{section.title} section prompt",
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
