from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base


class SectionType(StrEnum):
    HEADER = "header"
    SUMMARY = "summary"
    SKILLS = "skills"
    WORK_EXPERIENCE = "work_experience"
    EDUCATION = "education"
    LANGUAGES = "languages"
    CERTIFICATES = "certificates"
    REFERENCES = "references"
    CUSTOM = "custom"


class BlockType(StrEnum):
    HEADER = "header"
    SUMMARY = "summary"
    SKILLS = "skills"
    WORK_EXPERIENCE = "work_experience"
    EDUCATION = "education"
    LANGUAGE = "language"
    CERTIFICATE = "certificate"
    REFERENCE = "reference"
    CUSTOM = "custom"


class ClaimStrength(StrEnum):
    MENTION_ONLY = "mention_only"
    NORMAL = "normal"
    STRONG = "strong"
    DO_NOT_CLAIM = "do_not_claim"


class ApplicationStatus(StrEnum):
    JOB_SAVED = "job_saved"
    TAILORED = "tailored"
    EXPORTED = "exported"
    LIKELY_APPLIED = "likely_applied"
    MANUALLY_MARKED_APPLIED = "manually_marked_applied"


def utc_now_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now_naive, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now_naive,
        onupdate=utc_now_naive,
        server_default=func.now(),
        nullable=False,
    )


class AppSetting(Base, TimestampMixin):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(120), primary_key=True)
    value_json: Mapped[Any] = mapped_column(JSON, nullable=False)


class PersonProfile(Base, TimestampMixin):
    __tablename__ = "person_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    first_name: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    surname: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    preferred_name: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    location: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    contact: Mapped[ProfileContact | None] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )
    master_cv: Mapped[MasterCV | None] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )
    resumes: Mapped[list[Resume]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )
    applications: Mapped[list[Application]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )


class ProfileContact(Base, TimestampMixin):
    __tablename__ = "profile_contacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("person_profiles.id", ondelete="CASCADE"), unique=True
    )
    first_name: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    surname: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    location: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    phone: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    email: Mapped[str] = mapped_column(String(254), default="", nullable=False)
    linkedin_url: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    github_url: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    extra_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    address_line: Mapped[str] = mapped_column(String(240), default="", nullable=False)
    city: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    country: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    links_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    visibility_json: Mapped[Any] = mapped_column(JSON, default=dict, nullable=False)

    profile: Mapped[PersonProfile] = relationship(back_populates="contact")


class MasterCV(Base, TimestampMixin):
    __tablename__ = "master_cvs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("person_profiles.id", ondelete="CASCADE"), unique=True, index=True
    )
    title: Mapped[str] = mapped_column(String(160), default="Master CV", nullable=False)

    profile: Mapped[PersonProfile] = relationship(back_populates="master_cv")
    entries: Mapped[list[MasterCVEntry]] = relationship(
        back_populates="master_cv",
        cascade="all, delete-orphan",
        order_by="MasterCVEntry.display_order",
    )


class MasterCVEntry(Base, TimestampMixin):
    __tablename__ = "master_cv_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    master_cv_id: Mapped[int] = mapped_column(
        ForeignKey("master_cvs.id", ondelete="CASCADE"), index=True
    )
    category: Mapped[str] = mapped_column(
        String(80), default="work_experience", nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    content: Mapped[str] = mapped_column(Text, default="", nullable=False)
    keywords_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    allowed_wording: Mapped[str] = mapped_column(Text, default="", nullable=False)
    forbidden_wording: Mapped[str] = mapped_column(Text, default="", nullable=False)
    inference_notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    claim_strength: Mapped[str] = mapped_column(
        String(40), default=ClaimStrength.NORMAL.value, nullable=False
    )
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    master_cv: Mapped[MasterCV] = relationship(back_populates="entries")


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
    optional_extra_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    optional_extra_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    content: Mapped[str] = mapped_column(Text, default="", nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    ai_edit_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    metadata_json: Mapped[Any] = mapped_column(JSON, default=dict, nullable=False)

    section: Mapped[ResumeSection] = relationship(back_populates="blocks")


class PromptTemplate(Base, TimestampMixin):
    __tablename__ = "prompt_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    resume_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    section_type: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    block_type: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    user_prompt_template: Mapped[str] = mapped_column(Text, default="", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    scope: Mapped[str] = mapped_column(String(80), default="global", nullable=False)
    system_prompt: Mapped[str] = mapped_column(Text, default="", nullable=False)
    section_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)


class ResumeUpload(Base):
    __tablename__ = "resume_uploads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    resume_id: Mapped[int] = mapped_column(
        ForeignKey("resumes.id", ondelete="CASCADE"), index=True
    )
    original_filename: Mapped[str] = mapped_column(String(240), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(240), nullable=False)
    relative_path: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[str] = mapped_column(String(160), default="", nullable=False)
    extraction_status: Mapped[str] = mapped_column(
        String(160), default="manual import required", nullable=False
    )
    extracted_preview: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now_naive, server_default=func.now(), nullable=False
    )


class Application(Base, TimestampMixin):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("person_profiles.id", ondelete="CASCADE"), index=True
    )
    base_resume_id: Mapped[int] = mapped_column(
        ForeignKey("resumes.id", ondelete="CASCADE"), index=True
    )
    tailored_resume_id: Mapped[int | None] = mapped_column(
        ForeignKey("tailored_resumes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
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

    profile: Mapped[PersonProfile] = relationship(back_populates="applications")
    base_resume: Mapped[Resume] = relationship()
    tailored_resume: Mapped[TailoredResume | None] = relationship(
        primaryjoin="Application.tailored_resume_id == TailoredResume.id",
        foreign_keys="Application.tailored_resume_id",
        post_update=True,
    )
    events: Mapped[list[ApplicationEvent]] = relationship(
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="ApplicationEvent.created_at",
    )


class TailoredResume(Base, TimestampMixin):
    __tablename__ = "tailored_resumes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True
    )
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("person_profiles.id", ondelete="CASCADE"), index=True
    )
    base_resume_id: Mapped[int] = mapped_column(
        ForeignKey("resumes.id", ondelete="CASCADE"), index=True
    )
    content_json: Mapped[Any] = mapped_column(JSON, nullable=False)
    rendered_markdown: Mapped[str] = mapped_column(Text, nullable=False)


class ApplicationEvent(Base):
    __tablename__ = "application_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True
    )
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    message: Mapped[str] = mapped_column(Text, default="", nullable=False)
    metadata_json: Mapped[Any] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now_naive, server_default=func.now(), nullable=False
    )

    application: Mapped[Application] = relationship(back_populates="events")


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
        DateTime, default=utc_now_naive, server_default=func.now(), nullable=False
    )
