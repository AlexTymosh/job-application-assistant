from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base


class SectionType(StrEnum):
    SUMMARY = "summary"
    SKILLS = "skills"
    WORK_EXPERIENCE = "work_experience"
    EDUCATION = "education"
    PROJECTS = "projects"
    CERTIFICATIONS = "certifications"
    LANGUAGES = "languages"
    REFERENCES = "references"
    CUSTOM = "custom"


class BlockType(StrEnum):
    SUMMARY = "summary"
    SKILLS = "skills"
    WORK_EXPERIENCE = "work_experience"
    EDUCATION = "education"
    PROJECT = "project"
    DESCRIPTION = "description"
    TITLE = "title"
    CUSTOM = "custom"


class ClaimLevel(StrEnum):
    DO_NOT_CLAIM = "do_not_claim"
    MENTION_ONLY = "mention_only"
    PRACTICAL = "practical"
    STRONG = "strong"


class ProposalStatus(StrEnum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class ProposalOperation(StrEnum):
    REWRITE = "rewrite"
    CREATE = "create"
    HIDE = "hide"
    REORDER = "reorder"
    UPDATE_TITLE = "update_title"
    UPDATE_SKILLS_SET = "update_skills_set"


class ApplicationStatus(StrEnum):
    DRAFT = "draft"
    JOB_SAVED = "job_saved"
    REQUIREMENTS_EXTRACTED = "requirements_extracted"
    TAILORING_READY = "tailoring_ready"
    TAILORING_PROPOSED = "tailoring_proposed"
    REVIEW_IN_PROGRESS = "review_in_progress"
    CHANGES_APPROVED = "changes_approved"
    EXPORTED = "exported"
    COVER_LETTER_GENERATED = "cover_letter_generated"
    QA_WARNING = "qa_warning"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )


class AppSetting(Base, TimestampMixin):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(120), primary_key=True)
    value_json: Mapped[Any] = mapped_column(JSON, nullable=False)


class PersonProfile(Base, TimestampMixin):
    __tablename__ = "person_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    preferred_name: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    location: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    contact: Mapped[ProfileContact | None] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )
    resumes: Mapped[list[Resume]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )
    facts: Mapped[list[Fact]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )


class ProfileContact(Base, TimestampMixin):
    __tablename__ = "profile_contacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("person_profiles.id", ondelete="CASCADE"), unique=True
    )
    email: Mapped[str] = mapped_column(String(254), default="", nullable=False)
    phone: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    address_line: Mapped[str] = mapped_column(String(240), default="", nullable=False)
    city: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    country: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    links_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    visibility_json: Mapped[Any] = mapped_column(JSON, default=dict, nullable=False)

    profile: Mapped[PersonProfile] = relationship(back_populates="contact")


class Resume(Base, TimestampMixin):
    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("person_profiles.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    target_role: Mapped[str] = mapped_column(String(160), default="", nullable=False)
    language: Mapped[str] = mapped_column(String(32), default="en", nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    profile: Mapped[PersonProfile] = relationship(back_populates="resumes")
    sections: Mapped[list[ResumeSection]] = relationship(
        back_populates="resume",
        cascade="all, delete-orphan",
        order_by="ResumeSection.display_order",
    )


class ResumeSection(Base, TimestampMixin):
    __tablename__ = "resume_sections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    resume_id: Mapped[int] = mapped_column(
        ForeignKey("resumes.id", ondelete="CASCADE"), index=True
    )
    section_type: Mapped[str] = mapped_column(String(60), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    ai_edit_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    ai_prompt_key: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    policy_json: Mapped[Any] = mapped_column(JSON, default=dict, nullable=False)

    resume: Mapped[Resume] = relationship(back_populates="sections")
    blocks: Mapped[list[ResumeBlock]] = relationship(
        back_populates="section",
        cascade="all, delete-orphan",
        order_by="ResumeBlock.display_order",
    )


class ResumeBlock(Base, TimestampMixin):
    __tablename__ = "resume_blocks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    section_id: Mapped[int] = mapped_column(
        ForeignKey("resume_sections.id", ondelete="CASCADE"), index=True
    )
    block_type: Mapped[str] = mapped_column(String(60), nullable=False)
    title: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    subtitle: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    organisation: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    role_title: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    location: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    start_date: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    end_date: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    content: Mapped[str] = mapped_column(Text, default="", nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    ai_edit_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    ai_edit_mode: Mapped[str] = mapped_column(
        String(80), default="none", nullable=False
    )
    metadata_json: Mapped[Any] = mapped_column(JSON, default=dict, nullable=False)
    policy_json: Mapped[Any] = mapped_column(JSON, default=dict, nullable=False)

    section: Mapped[ResumeSection] = relationship(back_populates="blocks")
    bullets: Mapped[list[ResumeBullet]] = relationship(
        back_populates="block",
        cascade="all, delete-orphan",
        order_by="ResumeBullet.display_order",
    )
    fact_links: Mapped[list[ResumeBlockFactLink]] = relationship(
        back_populates="block", cascade="all, delete-orphan"
    )


class ResumeBullet(Base, TimestampMixin):
    __tablename__ = "resume_bullets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    block_id: Mapped[int] = mapped_column(
        ForeignKey("resume_blocks.id", ondelete="CASCADE"), index=True
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    ai_edit_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    fact_link_required: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )

    block: Mapped[ResumeBlock] = relationship(back_populates="bullets")
    fact_links: Mapped[list[ResumeBulletFactLink]] = relationship(
        back_populates="bullet", cascade="all, delete-orphan"
    )


class SkillItem(Base, TimestampMixin):
    __tablename__ = "skill_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    block_id: Mapped[int] = mapped_column(
        ForeignKey("resume_blocks.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class Fact(Base, TimestampMixin):
    __tablename__ = "facts"
    __table_args__ = (
        UniqueConstraint("profile_id", "fact_key", name="uq_profile_fact_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("person_profiles.id", ondelete="CASCADE"), index=True
    )
    fact_key: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    claim: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[str] = mapped_column(Text, default="", nullable=False)
    source: Mapped[str] = mapped_column(String(240), default="", nullable=False)
    allowed_claim_level: Mapped[str] = mapped_column(
        String(40), default=ClaimLevel.MENTION_ONLY.value, nullable=False
    )
    confidence: Mapped[str] = mapped_column(
        String(40), default="medium", nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    profile: Mapped[PersonProfile] = relationship(back_populates="facts")


class ResumeBulletFactLink(Base):
    __tablename__ = "resume_bullet_fact_links"
    __table_args__ = (UniqueConstraint("bullet_id", "fact_id", name="uq_bullet_fact"),)

    bullet_id: Mapped[int] = mapped_column(
        ForeignKey("resume_bullets.id", ondelete="CASCADE"), primary_key=True
    )
    fact_id: Mapped[int] = mapped_column(
        ForeignKey("facts.id", ondelete="CASCADE"), primary_key=True
    )

    bullet: Mapped[ResumeBullet] = relationship(back_populates="fact_links")
    fact: Mapped[Fact] = relationship()


class ResumeBlockFactLink(Base):
    __tablename__ = "resume_block_fact_links"
    __table_args__ = (UniqueConstraint("block_id", "fact_id", name="uq_block_fact"),)

    block_id: Mapped[int] = mapped_column(
        ForeignKey("resume_blocks.id", ondelete="CASCADE"), primary_key=True
    )
    fact_id: Mapped[int] = mapped_column(
        ForeignKey("facts.id", ondelete="CASCADE"), primary_key=True
    )

    block: Mapped[ResumeBlock] = relationship(back_populates="fact_links")
    fact: Mapped[Fact] = relationship()


class PromptTemplate(Base, TimestampMixin):
    __tablename__ = "prompt_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scope: Mapped[str] = mapped_column(String(80), nullable=False)
    block_type: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    section_type: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    user_prompt_template: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Application(Base, TimestampMixin):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("person_profiles.id", ondelete="CASCADE"), index=True
    )
    resume_id: Mapped[int] = mapped_column(
        ForeignKey("resumes.id", ondelete="CASCADE"), index=True
    )
    application_number: Mapped[int] = mapped_column(
        Integer, nullable=False, unique=True
    )
    job_title: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    company_name: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    source_url: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    raw_job_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(60), default=ApplicationStatus.JOB_SAVED.value, nullable=False
    )

    profile: Mapped[PersonProfile] = relationship()
    resume: Mapped[Resume] = relationship()
    requirements: Mapped[list[ExtractedJobRequirement]] = relationship(
        back_populates="application", cascade="all, delete-orphan"
    )


class ExtractedJobRequirement(Base):
    __tablename__ = "extracted_job_requirements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True
    )
    requirement_type: Mapped[str] = mapped_column(String(80), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    keywords_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    application: Mapped[Application] = relationship(back_populates="requirements")


class TailoringRun(Base):
    __tablename__ = "tailoring_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True
    )
    resume_id: Mapped[int] = mapped_column(
        ForeignKey("resumes.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(60), default="proposed", nullable=False)
    model: Mapped[str] = mapped_column(
        String(120), default="fake-deterministic", nullable=False
    )
    warnings_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)

    proposals: Mapped[list[AiChangeProposal]] = relationship(
        back_populates="tailoring_run", cascade="all, delete-orphan"
    )


class AiChangeProposal(Base):
    __tablename__ = "ai_change_proposals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tailoring_run_id: Mapped[int] = mapped_column(
        ForeignKey("tailoring_runs.id", ondelete="CASCADE"), index=True
    )
    target_type: Mapped[str] = mapped_column(String(80), nullable=False)
    target_id: Mapped[int] = mapped_column(Integer, nullable=False)
    operation: Mapped[str] = mapped_column(String(60), nullable=False)
    before_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    after_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    reason: Mapped[str] = mapped_column(Text, default="", nullable=False)
    risk_level: Mapped[str] = mapped_column(String(40), default="low", nullable=False)
    requirement_ids_json: Mapped[Any] = mapped_column(
        JSON, default=list, nullable=False
    )
    fact_ids_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    warning_codes_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[str] = mapped_column(
        String(40), default=ProposalStatus.PROPOSED.value, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime)

    tailoring_run: Mapped[TailoringRun] = relationship(back_populates="proposals")


class TailoredResumeSnapshot(Base):
    __tablename__ = "tailored_resume_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True
    )
    resume_id: Mapped[int] = mapped_column(
        ForeignKey("resumes.id", ondelete="CASCADE"), index=True
    )
    tailoring_run_id: Mapped[int] = mapped_column(
        ForeignKey("tailoring_runs.id", ondelete="CASCADE"), index=True
    )
    content_json: Mapped[Any] = mapped_column(JSON, nullable=False)
    rendered_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class CoverLetter(Base, TimestampMixin):
    __tablename__ = "cover_letters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True
    )
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("person_profiles.id", ondelete="CASCADE"), index=True
    )
    resume_id: Mapped[int] = mapped_column(
        ForeignKey("resumes.id", ondelete="CASCADE"), index=True
    )
    prompt_version: Mapped[str] = mapped_column(
        String(80), default="cover-letter-v1", nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="draft", nullable=False)


class Artifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True
    )
    artifact_type: Mapped[str] = mapped_column(String(40), nullable=False)
    relative_path: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
