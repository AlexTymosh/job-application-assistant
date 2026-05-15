from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import (
    Resume,
    ResumeBlock,
    ResumeBullet,
    ResumeBulletFactLink,
    ResumeSection,
)
from app.resumes.policies import AiEditPolicy


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
                selectinload(Resume.sections).selectinload(ResumeSection.blocks).selectinload(ResumeBlock.bullets),
            )
        )
        if resume is None:
            raise ValueError("Resume not found.")
        return resume

    def create_resume(self, profile_id: int, name: str, target_role: str, language: str = "en") -> Resume:
        resume = Resume(profile_id=profile_id, name=name, target_role=target_role, language=language)
        self.session.add(resume)
        self.session.commit()
        return resume

    def add_section(
        self,
        resume_id: int,
        section_type: str,
        title: str,
        ai_edit_enabled: bool = False,
    ) -> ResumeSection:
        order = self.session.scalar(select(ResumeSection).where(ResumeSection.resume_id == resume_id).order_by(ResumeSection.display_order.desc()))
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

    def add_block(
        self,
        section_id: int,
        *,
        block_type: str,
        title: str = "",
        role_title: str = "",
        organisation: str = "",
        content: str = "",
        ai_edit_enabled: bool = False,
    ) -> ResumeBlock:
        order = self.session.scalar(select(ResumeBlock).where(ResumeBlock.section_id == section_id).order_by(ResumeBlock.display_order.desc()))
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
            role_title=role_title,
            organisation=organisation,
            content=content,
            display_order=10 if order is None else order.display_order + 10,
            ai_edit_enabled=ai_edit_enabled,
            ai_edit_mode="block" if ai_edit_enabled else "none",
            policy_json=policy.to_json(),
        )
        self.session.add(block)
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
        order = self.session.scalar(select(ResumeBullet).where(ResumeBullet.block_id == block_id).order_by(ResumeBullet.display_order.desc()))
        bullet = ResumeBullet(
            block_id=block_id,
            text=text,
            display_order=10 if order is None else order.display_order + 10,
            ai_edit_enabled=ai_edit_enabled,
            fact_link_required=fact_link_required,
        )
        self.session.add(bullet)
        self.session.flush()
        for fact_id in fact_ids or []:
            self.session.add(ResumeBulletFactLink(bullet_id=bullet.id, fact_id=fact_id))
        self.session.commit()
        return bullet
