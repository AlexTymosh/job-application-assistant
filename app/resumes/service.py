from __future__ import annotations

import re
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import (
    PersonProfile,
    Resume,
    ResumeBlock,
    ResumeBullet,
    ResumeBulletFactLink,
    ResumeSection,
    ResumeUpload,
)
from app.exporters.docx_exporter import DocxExporter
from app.exporters.pdf_exporter import PdfExporter
from app.resumes.policies import AiEditPolicy
from app.resumes.renderer import render_resume_markdown

ALLOWED_UPLOAD_EXTENSIONS = {".pdf", ".doc", ".docx"}


def validate_resume_upload_filename(original_filename: str) -> str:
    source_name = Path(original_filename or "resume-upload").name
    suffix = Path(source_name).suffix.lower()
    if suffix not in ALLOWED_UPLOAD_EXTENSIONS:
        from app.core.errors import ResumeBuilderError

        raise ResumeBuilderError("Upload a PDF, DOC, or DOCX resume file.")
    return source_name


SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


class ResumeService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_resumes(self, profile_id: int | None = None) -> list[Resume]:
        stmt = select(Resume).order_by(Resume.name)
        if profile_id is not None:
            stmt = stmt.where(Resume.profile_id == profile_id)
        return list(self.session.scalars(stmt))

    def get_resume(self, resume_id: int) -> Resume:
        resume = self.session.scalar(
            select(Resume)
            .where(Resume.id == resume_id)
            .options(
                selectinload(Resume.profile),
                selectinload(Resume.sections)
                .selectinload(ResumeSection.blocks)
                .selectinload(ResumeBlock.bullets),
            )
        )
        if resume is None:
            raise ValueError("Resume not found.")
        return resume

    def create_resume(
        self,
        profile_id: int,
        name: str,
        target_role: str,
        language: str = "en",
        *,
        create_standard_sections: bool = False,
    ) -> Resume:
        resume = Resume(
            profile_id=profile_id, name=name, target_role=target_role, language=language
        )
        self.session.add(resume)
        self.session.flush()
        if create_standard_sections:
            self.create_standard_skeleton(resume.id, commit=False)
        self.session.commit()
        return resume

    def create_standard_skeleton(
        self, resume_id: int, *, commit: bool = True
    ) -> list[ResumeSection]:
        sections: list[ResumeSection] = []
        skeleton = [
            ("summary", "Summary"),
            ("skills", "Skills"),
            ("work_experience", "Work Experience"),
            ("education", "Education"),
            ("languages", "Languages"),
            ("certifications", "Certifications"),
            ("references", "References"),
        ]
        for index, (section_type, title) in enumerate(skeleton, start=1):
            section = ResumeSection(
                resume_id=resume_id,
                section_type=section_type,
                title=title,
                display_order=index * 10,
                ai_edit_enabled=section_type
                in {"summary", "skills", "work_experience"},
                ai_prompt_key=f"{section_type}_prompt",
            )
            self.session.add(section)
            self.session.flush()
            sections.append(section)
            if section_type == "summary":
                self.add_block(
                    section.id,
                    block_type="summary",
                    title="Professional Summary",
                    content="",
                    ai_edit_enabled=True,
                    commit=False,
                )
            if section_type == "skills":
                self.add_block(
                    section.id,
                    block_type="skills",
                    title="Hard Skills",
                    content="",
                    ai_edit_enabled=True,
                    commit=False,
                )
                self.add_block(
                    section.id,
                    block_type="skills",
                    title="Soft Skills",
                    content="",
                    ai_edit_enabled=True,
                    commit=False,
                )
            if section_type == "references":
                self.add_block(
                    section.id,
                    block_type="custom",
                    title="References",
                    content="Available on request.",
                    ai_edit_enabled=False,
                    commit=False,
                )
        if commit:
            self.session.commit()
        return sections

    def attach_upload(
        self,
        resume_id: int,
        *,
        original_filename: str,
        content_type: str,
        content: bytes,
        app_data_root: Path,
    ) -> ResumeUpload:
        from app.core.errors import ResumeBuilderError

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
            relative_path=(relative_dir / stored_filename).as_posix(),
            content_type=content_type or "application/octet-stream",
            extraction_status=(
                "Stored. Manual extraction/import is not implemented yet."
            ),
            extracted_preview="",
        )
        self.session.add(upload)
        self.session.commit()
        return upload

    def update_resume(self, resume_id: int, **values: str) -> Resume:
        resume = self.get_resume(resume_id)
        for field in ["name", "target_role", "language"]:
            if field in values:
                setattr(resume, field, values[field])
        self.session.commit()
        return resume

    def add_section(
        self,
        resume_id: int,
        section_type: str,
        title: str,
        ai_edit_enabled: bool = False,
    ) -> ResumeSection:
        order = self.session.scalar(
            select(ResumeSection)
            .where(ResumeSection.resume_id == resume_id)
            .order_by(ResumeSection.display_order.desc())
        )
        display_order = 10 if order is None else order.display_order + 10
        section = ResumeSection(
            resume_id=resume_id,
            section_type=section_type,
            title=title,
            display_order=display_order,
            ai_edit_enabled=ai_edit_enabled,
            ai_prompt_key=f"{section_type}_prompt",
        )
        self.session.add(section)
        self.session.commit()
        return section

    def update_section(
        self,
        section_id: int,
        *,
        title: str,
        is_visible: bool,
        ai_edit_enabled: bool,
    ) -> ResumeSection:
        section = self.session.get(ResumeSection, section_id)
        if section is None:
            raise ValueError("Section not found.")
        section.title = title
        section.is_visible = is_visible
        section.ai_edit_enabled = ai_edit_enabled
        self.session.commit()
        return section

    def add_block(
        self,
        section_id: int,
        *,
        block_type: str,
        title: str = "",
        subtitle: str = "",
        role_title: str = "",
        organisation: str = "",
        location: str = "",
        start_date: str = "",
        end_date: str = "",
        is_current: bool = False,
        content: str = "",
        ai_edit_enabled: bool = False,
        commit: bool = True,
    ) -> ResumeBlock:
        order = self.session.scalar(
            select(ResumeBlock)
            .where(ResumeBlock.section_id == section_id)
            .order_by(ResumeBlock.display_order.desc())
        )
        policy = AiEditPolicy(
            ai_editable=ai_edit_enabled,
            ai_can_rewrite=ai_edit_enabled,
            prompt_key=f"{block_type}_prompt",
            ai_can_edit_title=block_type == "title" and ai_edit_enabled,
        )
        block = ResumeBlock(
            section_id=section_id,
            block_type=block_type,
            title=title,
            subtitle=subtitle,
            role_title=role_title,
            organisation=organisation,
            location=location,
            start_date=start_date,
            end_date=end_date,
            is_current=is_current,
            content=content,
            display_order=10 if order is None else order.display_order + 10,
            ai_edit_enabled=ai_edit_enabled,
            ai_edit_mode="block" if ai_edit_enabled else "none",
            policy_json=policy.to_json(),
        )
        self.session.add(block)
        if commit:
            self.session.commit()
        else:
            self.session.flush()
        return block

    def update_block(self, block_id: int, **values: object) -> ResumeBlock:
        block = self.session.get(ResumeBlock, block_id)
        if block is None:
            raise ValueError("Block not found.")
        for field in [
            "block_type",
            "title",
            "subtitle",
            "role_title",
            "organisation",
            "location",
            "start_date",
            "end_date",
            "content",
        ]:
            if field in values:
                setattr(block, field, str(values[field] or ""))
        for field in ["is_current", "is_visible", "ai_edit_enabled"]:
            if field in values:
                setattr(block, field, bool(values[field]))
        block.ai_edit_mode = "block" if block.ai_edit_enabled else "none"
        self.session.commit()
        return block

    def add_bullet(
        self,
        block_id: int,
        text: str,
        *,
        ai_edit_enabled: bool,
        fact_link_required: bool,
        fact_ids: list[int] | None = None,
    ) -> ResumeBullet:
        order = self.session.scalar(
            select(ResumeBullet)
            .where(ResumeBullet.block_id == block_id)
            .order_by(ResumeBullet.display_order.desc())
        )
        bullet = ResumeBullet(
            block_id=block_id,
            text=text,
            display_order=10 if order is None else order.display_order + 10,
            ai_edit_enabled=ai_edit_enabled,
            fact_link_required=fact_link_required,
        )
        self.session.add(bullet)
        self.session.flush()
        self.update_bullet_fact_links(bullet.id, fact_ids or [], commit=False)
        self.session.commit()
        return bullet

    def update_bullet(
        self,
        bullet_id: int,
        *,
        text: str,
        is_visible: bool,
        ai_edit_enabled: bool,
        fact_link_required: bool,
        fact_ids: list[int] | None = None,
    ) -> ResumeBullet:
        bullet = self.session.get(ResumeBullet, bullet_id)
        if bullet is None:
            raise ValueError("Bullet not found.")
        bullet.text = text
        bullet.is_visible = is_visible
        bullet.ai_edit_enabled = ai_edit_enabled
        bullet.fact_link_required = fact_link_required
        if fact_ids is not None:
            self.update_bullet_fact_links(bullet.id, fact_ids, commit=False)
        self.session.commit()
        return bullet

    def update_bullet_fact_links(
        self, bullet_id: int, fact_ids: list[int], *, commit: bool = True
    ) -> None:
        for link in list(
            self.session.scalars(
                select(ResumeBulletFactLink).where(
                    ResumeBulletFactLink.bullet_id == bullet_id
                )
            )
        ):
            self.session.delete(link)
        self.session.flush()
        for fact_id in fact_ids:
            self.session.add(ResumeBulletFactLink(bullet_id=bullet_id, fact_id=fact_id))
        if commit:
            self.session.commit()

    def export_base_resume(
        self, resume_id: int, export_format: str, app_data_root: Path
    ) -> Path:
        if export_format not in {"pdf", "docx"}:
            from app.core.errors import ExportWorkflowError

            raise ExportWorkflowError(
                "Unsupported base resume export format.", status_code=400
            )
        resume = self.session.scalar(
            select(Resume)
            .where(Resume.id == resume_id)
            .options(
                selectinload(Resume.profile).selectinload(PersonProfile.contact),
                selectinload(Resume.sections)
                .selectinload(ResumeSection.blocks)
                .selectinload(ResumeBlock.bullets),
            )
        )
        if resume is None:
            from app.core.errors import NotFoundError

            raise NotFoundError("Resume not found.")
        markdown = render_resume_markdown(resume, contact=resume.profile.contact)
        export_dir = Path("artifacts") / "resumes" / f"resume-{resume.id}"
        absolute_dir = (app_data_root / export_dir).resolve()
        root = app_data_root.resolve()
        if root not in absolute_dir.parents and absolute_dir != root:
            from app.core.errors import ExportWorkflowError

            raise ExportWorkflowError("Unsafe resume export path.", status_code=400)
        absolute_dir.mkdir(parents=True, exist_ok=True)
        filename = f"base-resume.{export_format}"
        path = absolute_dir / filename
        if export_format == "pdf":
            path.write_bytes(
                PdfExporter().export(markdown, title=resume.name or "Base resume")
            )
        else:
            path.write_bytes(
                DocxExporter().export(markdown, title=resume.name or "Base resume")
            )
        return path

    def get_base_resume_export_path(
        self, resume_id: int, export_format: str, app_data_root: Path
    ) -> Path:
        if export_format not in {"pdf", "docx"}:
            from app.core.errors import ExportWorkflowError

            raise ExportWorkflowError(
                "Unsupported base resume export format.", status_code=400
            )
        path = (
            app_data_root
            / "artifacts"
            / "resumes"
            / f"resume-{resume_id}"
            / f"base-resume.{export_format}"
        ).resolve()
        root = app_data_root.resolve()
        if root not in path.parents and path != root:
            from app.core.errors import ExportWorkflowError

            raise ExportWorkflowError("Unsafe resume export path.", status_code=400)
        return path

    def move_section(self, section_id: int, direction: str) -> None:
        section = self.session.get(ResumeSection, section_id)
        if section is None:
            raise ValueError("Section not found.")
        peers = list(
            self.session.scalars(
                select(ResumeSection)
                .where(ResumeSection.resume_id == section.resume_id)
                .order_by(ResumeSection.display_order)
            )
        )
        self._move_ordered(peers, section, direction)

    def move_block(self, block_id: int, direction: str) -> None:
        block = self.session.get(ResumeBlock, block_id)
        if block is None:
            raise ValueError("Block not found.")
        peers = list(
            self.session.scalars(
                select(ResumeBlock)
                .where(ResumeBlock.section_id == block.section_id)
                .order_by(ResumeBlock.display_order)
            )
        )
        self._move_ordered(peers, block, direction)

    def move_bullet(self, bullet_id: int, direction: str) -> None:
        bullet = self.session.get(ResumeBullet, bullet_id)
        if bullet is None:
            raise ValueError("Bullet not found.")
        peers = list(
            self.session.scalars(
                select(ResumeBullet)
                .where(ResumeBullet.block_id == bullet.block_id)
                .order_by(ResumeBullet.display_order)
            )
        )
        self._move_ordered(peers, bullet, direction)

    def delete_section(self, section_id: int) -> None:
        section = self.session.get(ResumeSection, section_id)
        if section is not None:
            self.session.delete(section)
            self.session.commit()

    def delete_block(self, block_id: int) -> None:
        block = self.session.get(ResumeBlock, block_id)
        if block is not None:
            self.session.delete(block)
            self.session.commit()

    def delete_bullet(self, bullet_id: int) -> None:
        bullet = self.session.get(ResumeBullet, bullet_id)
        if bullet is not None:
            self.session.delete(bullet)
            self.session.commit()

    def _move_ordered(self, peers: list[object], item: object, direction: str) -> None:
        index = peers.index(item)
        target_index = index - 1 if direction == "up" else index + 1
        if target_index < 0 or target_index >= len(peers):
            return
        target = peers[target_index]
        item.display_order, target.display_order = (
            target.display_order,
            item.display_order,
        )
        self.session.commit()
