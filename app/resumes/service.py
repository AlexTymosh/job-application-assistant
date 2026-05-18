from __future__ import annotations

import re
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import NotFoundError, ResumeBuilderError
from app.db.models import (
    PersonProfile,
    Resume,
    ResumeBlock,
    ResumeSection,
    ResumeUpload,
)
from app.exporters.docx_exporter import DocxExporter
from app.exporters.pdf_exporter import PdfExporter
from app.resumes.renderer import render_resume_markdown, resume_to_content

ALLOWED_UPLOAD_EXTENSIONS = {".pdf", ".doc", ".docx"}
SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._-]+")
STANDARD_SECTIONS = [
    ("header", "Header", False),
    ("skills", "Skills", True),
    ("summary", "Summary", True),
    ("work_experience", "Work Experience", True),
    ("education", "Education", True),
    ("languages", "Languages", False),
    ("certificates", "Certificates", False),
    ("references", "References", False),
]


def validate_resume_upload_filename(original_filename: str) -> str:
    source_name = Path(original_filename or "resume-upload").name
    suffix = Path(source_name).suffix.lower()
    if suffix not in ALLOWED_UPLOAD_EXTENSIONS:
        raise ResumeBuilderError("Upload a PDF, DOC, or DOCX resume file.")
    return source_name


class ResumeService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_resumes(self, profile_id: int | None = None) -> list[Resume]:
        stmt = select(Resume).order_by(Resume.is_default.desc(), Resume.name)
        if profile_id is not None:
            stmt = stmt.where(Resume.profile_id == profile_id)
        return list(self.session.scalars(stmt))

    def get_resume(self, resume_id: int) -> Resume:
        resume = self.session.scalar(
            select(Resume)
            .where(Resume.id == resume_id)
            .options(
                selectinload(Resume.profile).selectinload(PersonProfile.contact),
                selectinload(Resume.sections).selectinload(ResumeSection.blocks),
            )
            .execution_options(populate_existing=True)
        )
        if resume is None:
            raise NotFoundError("Resume variant not found.")
        return resume

    def create_resume(
        self,
        profile_id: int,
        name: str,
        target_role: str,
        language: str = "en",
        *,
        create_standard_sections: bool = True,
        is_default: bool = False,
    ) -> Resume:
        if is_default:
            for existing in self.list_resumes(profile_id):
                existing.is_default = False
        resume = Resume(
            profile_id=profile_id,
            name=name.strip() or "Resume Variant",
            target_role=target_role.strip(),
            language=language,
            is_default=is_default,
        )
        self.session.add(resume)
        self.session.flush()
        if create_standard_sections:
            self.create_standard_skeleton(resume.id, commit=False)
        self.session.commit()
        self.session.refresh(resume)
        return resume

    def create_standard_skeleton(
        self, resume_id: int, *, commit: bool = True
    ) -> list[ResumeSection]:
        resume = self.session.get(Resume, resume_id)
        if resume is None:
            raise NotFoundError("Resume variant not found.")
        if resume.sections:
            return resume.sections
        sections: list[ResumeSection] = []
        for index, (section_type, title, ai_enabled) in enumerate(
            STANDARD_SECTIONS, start=1
        ):
            section = ResumeSection(
                resume_id=resume_id,
                section_type=section_type,
                title=title,
                display_order=index * 10,
                ai_edit_enabled=ai_enabled,
            )
            self.session.add(section)
            self.session.flush()
            sections.append(section)
            if section_type == "header":
                profile = resume.profile
                contact = profile.contact if profile else None
                self.session.add(
                    ResumeBlock(
                        section_id=section.id,
                        block_type="header",
                        title="Header",
                        ai_edit_enabled=False,
                        metadata_json={
                            "first_name": contact.first_name
                            if contact
                            else getattr(profile, "first_name", ""),
                            "surname": contact.surname
                            if contact
                            else getattr(profile, "surname", ""),
                            "location": contact.location
                            if contact
                            else getattr(profile, "location", ""),
                            "phone": contact.phone if contact else "",
                            "email": contact.email if contact else "",
                            "linkedin_url": contact.linkedin_url if contact else "",
                            "github_url": contact.github_url if contact else "",
                            "website_url": "",
                            "extra_text": contact.extra_text if contact else "",
                        },
                    )
                )
            elif section_type == "summary":
                self.session.add(
                    ResumeBlock(
                        section_id=section.id,
                        block_type="summary",
                        title="Summary",
                        ai_edit_enabled=True,
                    )
                )
            elif section_type == "skills":
                self.session.add(
                    ResumeBlock(
                        section_id=section.id,
                        block_type="skills",
                        title="Hard Skills",
                        ai_edit_enabled=True,
                        display_order=10,
                    )
                )
                self.session.add(
                    ResumeBlock(
                        section_id=section.id,
                        block_type="skills",
                        title="Soft Skills",
                        ai_edit_enabled=True,
                        display_order=20,
                    )
                )
        if commit:
            self.session.commit()
        return sections

    def update_resume(
        self, resume_id: int, *, name: str, target_role: str, language: str = "en"
    ) -> Resume:
        resume = self.get_resume(resume_id)
        resume.name = name.strip() or resume.name
        resume.target_role = target_role.strip()
        resume.language = language
        self.session.commit()
        return resume

    def section_for_type(self, resume_id: int, section_type: str) -> ResumeSection:
        resume = self.get_resume(resume_id)
        for section in resume.sections:
            if section.section_type == section_type:
                return section
        self.create_standard_skeleton(resume_id)
        resume = self.get_resume(resume_id)
        for section in resume.sections:
            if section.section_type == section_type:
                return section
        raise NotFoundError("Resume section not found.")

    def save_section(
        self, resume_id: int, section_type: str, data: dict[str, str | list[str]]
    ) -> None:
        section = self.section_for_type(resume_id, section_type)
        if section_type == "header":
            block = _first_or_create(self.session, section, "header", "Header")
            block.ai_edit_enabled = False
            block.metadata_json = {
                key: str(data.get(key, "")).strip()
                for key in [
                    "first_name",
                    "surname",
                    "location",
                    "phone",
                    "email",
                    "linkedin_url",
                    "github_url",
                    "website_url",
                    "personal_website_url",
                    "extra_text",
                ]
            }
        elif section_type == "summary":
            block = _first_or_create(
                self.session, section, "summary", "Summary", ai=True
            )
            block.content = str(data.get("description", "")).strip()
        elif section_type == "skills":
            hard = _named_or_create(
                self.session, section, "Hard Skills", order=10, ai=True
            )
            soft = _named_or_create(
                self.session, section, "Soft Skills", order=20, ai=True
            )
            hard.content = str(data.get("hard_skills_text", "")).strip()
            soft.content = str(data.get("soft_skills_text", "")).strip()
        else:
            self._replace_repeating_blocks(section, section_type, data)
        self.session.commit()

    def _replace_repeating_blocks(
        self,
        section: ResumeSection,
        section_type: str,
        data: dict[str, str | list[str]],
    ) -> None:
        for block in list(section.blocks):
            self.session.delete(block)
        rows = _rows_from_form(data, section_type)
        for index, row in enumerate(rows, start=1):
            if not any(str(value).strip() for value in row.values()):
                continue
            if section_type == "work_experience":
                block = ResumeBlock(
                    section_id=section.id,
                    block_type="work_experience",
                    role_title=row.get("job_title", ""),
                    organisation=row.get("employer", ""),
                    start_date=row.get("start_date", ""),
                    end_date=row.get("end_date", ""),
                    is_current=row.get("is_current", "") == "on",
                    optional_extra_enabled=row.get("optional_extra_enabled", "")
                    == "on",
                    optional_extra_text=row.get("optional_extra_text", ""),
                    content=row.get("key_bullets", ""),
                    ai_edit_enabled=True,
                    display_order=index * 10,
                )
            elif section_type == "education":
                block = ResumeBlock(
                    section_id=section.id,
                    block_type="education",
                    organisation=row.get("institution_name", ""),
                    role_title=row.get("specialisation", ""),
                    start_date=row.get("start_date", ""),
                    end_date=row.get("end_date", ""),
                    is_current=row.get("is_current", "") == "on",
                    content=row.get("key_bullets", ""),
                    ai_edit_enabled=True,
                    display_order=index * 10,
                )
            elif section_type == "languages":
                block = ResumeBlock(
                    section_id=section.id,
                    block_type="language",
                    title=row.get("language", ""),
                    subtitle=row.get("level", ""),
                    metadata_json=row,
                    display_order=index * 10,
                )
            elif section_type == "certificates":
                block = ResumeBlock(
                    section_id=section.id,
                    block_type="certificate",
                    title=row.get("certificate_name", ""),
                    metadata_json=row,
                    display_order=index * 10,
                )
            elif section_type == "references":
                block = ResumeBlock(
                    section_id=section.id,
                    block_type="reference",
                    title=row.get("name", ""),
                    metadata_json=row,
                    display_order=index * 10,
                )
            else:
                continue
            self.session.add(block)

    def attach_upload(
        self,
        resume_id: int,
        *,
        original_filename: str,
        content_type: str,
        content: bytes,
        app_data_root: Path,
    ) -> ResumeUpload:
        resume = self.get_resume(resume_id)
        source_name = validate_resume_upload_filename(original_filename)
        suffix = Path(source_name).suffix.lower()
        stem = (
            SAFE_FILENAME_RE.sub("-", Path(source_name).stem).strip(".-_") or "resume"
        )
        stored_filename = f"{uuid4().hex}-{stem}{suffix}"
        relative_dir = (
            Path("artifacts")
            / "uploads"
            / f"profile-{resume.profile_id}"
            / f"resume-{resume.id}"
        )
        absolute_dir = (app_data_root / relative_dir).resolve()
        root = app_data_root.resolve()
        if root not in absolute_dir.parents and absolute_dir != root:
            raise ResumeBuilderError("Unsafe upload path.")
        absolute_dir.mkdir(parents=True, exist_ok=True)
        absolute_path = (absolute_dir / stored_filename).resolve()
        if root not in absolute_path.parents:
            raise ResumeBuilderError("Unsafe upload path.")
        absolute_path.write_bytes(content)
        upload = ResumeUpload(
            resume_id=resume.id,
            original_filename=source_name,
            stored_filename=stored_filename,
            relative_path=str(relative_dir / stored_filename),
            content_type=content_type,
        )
        self.session.add(upload)
        self.session.commit()
        return upload

    def export_base_resume(
        self, resume_id: int, export_format: str, app_data_root: Path
    ) -> Path:
        resume = self.get_resume(resume_id)
        markdown = render_resume_markdown(resume)
        content = resume_to_content(resume)
        return _write_export(
            markdown,
            resume.name,
            export_format,
            app_data_root / "artifacts" / "resumes" / f"resume-{resume.id}",
            content=content,
        )

    def base_resume_export_path(
        self, resume_id: int, export_format: str, app_data_root: Path
    ) -> Path:
        resume = self.get_resume(resume_id)
        suffix = _normalise_format(export_format)
        return (
            app_data_root
            / "artifacts"
            / "resumes"
            / f"resume-{resume.id}"
            / f"{_safe_export_name(resume.name)}.{suffix}"
        )


def _write_export(
    markdown: str,
    title: str,
    export_format: str,
    directory: Path,
    *,
    content: dict | None = None,
) -> Path:
    suffix = _normalise_format(export_format)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{_safe_export_name(title)}.{suffix}"
    if suffix == "pdf":
        if content is None:
            path.write_bytes(PdfExporter().export(markdown, title=title))
        else:
            path.write_bytes(PdfExporter().export_content(content, title=title))
    elif suffix == "docx":
        if content is None:
            path.write_bytes(DocxExporter().export(markdown, title=title))
        else:
            path.write_bytes(DocxExporter().export_content(content, title=title))
    else:
        path.write_text(markdown, encoding="utf-8")
    return path


def _normalise_format(export_format: str) -> str:
    if export_format not in {"pdf", "docx", "md"}:
        raise ResumeBuilderError("Choose PDF or DOCX export.")
    return export_format


def _safe_export_name(title: str) -> str:
    return SAFE_FILENAME_RE.sub("-", title.lower()).strip(".-_") or "resume"


def _first_or_create(
    session: Session,
    section: ResumeSection,
    block_type: str,
    title: str,
    ai: bool = False,
) -> ResumeBlock:
    if section.blocks:
        return section.blocks[0]
    block = ResumeBlock(
        section_id=section.id, block_type=block_type, title=title, ai_edit_enabled=ai
    )
    session.add(block)
    session.flush()
    return block


def _named_or_create(
    session: Session, section: ResumeSection, title: str, order: int, ai: bool = False
) -> ResumeBlock:
    for block in section.blocks:
        if block.title == title:
            return block
    block = ResumeBlock(
        section_id=section.id,
        block_type="skills",
        title=title,
        display_order=order,
        ai_edit_enabled=ai,
    )
    session.add(block)
    session.flush()
    return block


def _rows_from_form(
    data: dict[str, str | list[str]], prefix: str
) -> list[dict[str, str]]:
    keys_by_section = {
        "work_experience": [
            "job_title",
            "employer",
            "start_date",
            "end_date",
            "is_current",
            "optional_extra_enabled",
            "optional_extra_text",
            "key_bullets",
        ],
        "education": [
            "institution_name",
            "specialisation",
            "start_date",
            "end_date",
            "is_current",
            "key_bullets",
        ],
        "languages": ["language", "level"],
        "certificates": ["certificate_name", "certificate_url", "issue_year"],
        "references": [
            "name",
            "role_title",
            "company",
            "phone",
            "email",
            "linkedin_url",
        ],
    }
    keys = keys_by_section[prefix]
    indexed_rows: dict[int, dict[str, str]] = {}
    indexed_pattern = re.compile(r"^rows\[(\d+)]\[([A-Za-z0-9_]+)]$")
    for form_key, raw_value in data.items():
        match = indexed_pattern.match(form_key)
        if match is None:
            continue
        row_index = int(match.group(1))
        row_key = match.group(2)
        if row_key not in keys:
            continue
        value = raw_value[-1] if isinstance(raw_value, list) else raw_value
        indexed_rows.setdefault(row_index, {})[row_key] = str(value).strip()
    if indexed_rows:
        return [
            {key: indexed_rows[index].get(key, "") for key in keys}
            for index in sorted(indexed_rows)
        ]

    lists: dict[str, list[str]] = {}
    max_len = 0
    for key in keys:
        value = data.get(key, [])
        values = value if isinstance(value, list) else [str(value)] if value else []
        lists[key] = [str(item).strip() for item in values]
        max_len = max(max_len, len(lists[key]))
    return [
        {key: lists[key][index] if index < len(lists[key]) else "" for key in keys}
        for index in range(max_len)
    ]
