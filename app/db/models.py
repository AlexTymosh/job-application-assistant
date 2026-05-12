from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UuidPrimaryKeyMixin


class ApplicationStatus(StrEnum):
    DRAFT = "draft"
    URL_READ_FAILED = "url_read_failed"
    JOB_EXTRACTED = "job_extracted"
    BLOCKED_BLACKLIST = "blocked_blacklist"
    DUPLICATE_WARNING = "duplicate_warning"
    READY_FOR_TAILORING = "ready_for_tailoring"
    TAILORED = "tailored"
    QA_FAILED = "qa_failed"
    QA_WARNING = "qa_warning"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    EXPORTED = "exported"
    APPLIED = "applied"
    FOLLOW_UP_DUE = "follow_up_due"
    INTERVIEW = "interview"
    REJECTED = "rejected"
    IGNORED = "ignored"
    WITHDRAWN = "withdrawn"


class WarningLevel(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class Application(Base, UuidPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "applications"

    profile_name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50),
        default=ApplicationStatus.DRAFT.value,
        nullable=False,
        index=True,
    )

    job_title: Mapped[str | None] = mapped_column(String(255))
    company_name: Mapped[str | None] = mapped_column(String(255))
    company_domain: Mapped[str | None] = mapped_column(String(255), index=True)
    source_url: Mapped[str | None] = mapped_column(Text)
    normalized_url: Mapped[str | None] = mapped_column(Text)
    job_text_hash: Mapped[str | None] = mapped_column(String(64), index=True)

    selected_cv_variant: Mapped[str | None] = mapped_column(String(100))
    notes: Mapped[str | None] = mapped_column(Text)

    artifacts: Mapped[list[Artifact]] = relationship(
        back_populates="application",
        cascade="all, delete-orphan",
    )
    events: Mapped[list[ApplicationEvent]] = relationship(
        back_populates="application",
        cascade="all, delete-orphan",
    )
    warnings: Mapped[list[ApplicationWarning]] = relationship(
        back_populates="application",
        cascade="all, delete-orphan",
    )


class Artifact(Base, UuidPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "artifacts"

    application_id: Mapped[UUID] = mapped_column(
        ForeignKey("applications.id"),
        nullable=False,
        index=True,
    )
    artifact_type: Mapped[str] = mapped_column(String(100), nullable=False)
    path: Mapped[str] = mapped_column(Text, nullable=False)

    application: Mapped[Application] = relationship(back_populates="artifacts")


class ApplicationEvent(Base, UuidPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "application_events"

    application_id: Mapped[UUID] = mapped_column(
        ForeignKey("applications.id"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    message: Mapped[str | None] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    application: Mapped[Application] = relationship(back_populates="events")


class ApplicationWarning(Base, UuidPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "application_warnings"

    application_id: Mapped[UUID] = mapped_column(
        ForeignKey("applications.id"),
        nullable=False,
        index=True,
    )
    level: Mapped[str] = mapped_column(
        String(50),
        default=WarningLevel.WARNING.value,
        nullable=False,
    )
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    application: Mapped[Application] = relationship(back_populates="warnings")
