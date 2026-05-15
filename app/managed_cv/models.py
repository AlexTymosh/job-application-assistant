from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    PrimaryKeyConstraint,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.cv.models import AllowedClaimLevel, FactCategory
from app.settings.base import SettingsBase

_FACT_CATEGORY_VALUES = ", ".join(f"'{category.value}'" for category in FactCategory)
_ALLOWED_CLAIM_LEVEL_VALUES = ", ".join(
    f"'{level.value}'" for level in AllowedClaimLevel
)


class ManagedCvVariant(SettingsBase):
    __tablename__ = "cv_variants"
    __table_args__ = (
        UniqueConstraint("profile_id", "name", name="uq_cv_variants_profile_name"),
        CheckConstraint("is_active IN (0, 1)", name="ck_cv_variants_is_active"),
        Index("ix_cv_variants_profile_id", "profile_id"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    profile_id: Mapped[str] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    aliases: Mapped[list[ManagedCvVariantAlias]] = relationship(
        back_populates="variant", cascade="all, delete-orphan"
    )
    sections: Mapped[list[ManagedCvSection]] = relationship(
        back_populates="variant", cascade="all, delete-orphan"
    )


class ManagedCvVariantAlias(SettingsBase):
    __tablename__ = "cv_variant_aliases"
    __table_args__ = (
        UniqueConstraint("variant_id", "alias", name="uq_cv_variant_aliases_alias"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    variant_id: Mapped[str] = mapped_column(
        ForeignKey("cv_variants.id", ondelete="CASCADE"), nullable=False
    )
    alias: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    variant: Mapped[ManagedCvVariant] = relationship(back_populates="aliases")


class ManagedCvSection(SettingsBase):
    __tablename__ = "cv_sections"
    __table_args__ = (
        UniqueConstraint("variant_id", "section_key", name="uq_cv_sections_key"),
        CheckConstraint("is_required IN (0, 1)", name="ck_cv_sections_is_required"),
        Index("ix_cv_sections_variant_id", "variant_id"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    variant_id: Mapped[str] = mapped_column(
        ForeignKey("cv_variants.id", ondelete="CASCADE"), nullable=False
    )
    section_key: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    display_order: Mapped[int] = mapped_column(nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    variant: Mapped[ManagedCvVariant] = relationship(back_populates="sections")
    blocks: Mapped[list[ManagedCvBlock]] = relationship(
        back_populates="section", cascade="all, delete-orphan"
    )


class ManagedCvBlock(SettingsBase):
    __tablename__ = "cv_blocks"
    __table_args__ = (
        UniqueConstraint("section_id", "block_key", name="uq_cv_blocks_key"),
        CheckConstraint("is_enabled IN (0, 1)", name="ck_cv_blocks_is_enabled"),
        Index("ix_cv_blocks_section_id", "section_id"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    section_id: Mapped[str] = mapped_column(
        ForeignKey("cv_sections.id", ondelete="CASCADE"), nullable=False
    )
    block_key: Mapped[str] = mapped_column(Text, nullable=False)
    content_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    display_order: Mapped[int] = mapped_column(nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    section: Mapped[ManagedCvSection] = relationship(back_populates="blocks")
    fact_links: Mapped[list[ManagedCvBlockFactLink]] = relationship(
        back_populates="block", cascade="all, delete-orphan"
    )


class ManagedFact(SettingsBase):
    __tablename__ = "facts"
    __table_args__ = (
        UniqueConstraint("profile_id", "fact_key", name="uq_facts_profile_key"),
        CheckConstraint(
            f"category IN ({_FACT_CATEGORY_VALUES})", name="ck_facts_category"
        ),
        CheckConstraint(
            f"allowed_claim_level IN ({_ALLOWED_CLAIM_LEVEL_VALUES})",
            name="ck_facts_allowed_claim_level",
        ),
        CheckConstraint("is_active IN (0, 1)", name="ck_facts_is_active"),
        Index("ix_facts_profile_id", "profile_id"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    profile_id: Mapped[str] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
    )
    fact_key: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    allowed_claim_level: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    block_links: Mapped[list[ManagedCvBlockFactLink]] = relationship(
        back_populates="fact", cascade="all, delete-orphan"
    )


class ManagedCvBlockFactLink(SettingsBase):
    __tablename__ = "cv_block_fact_links"
    __table_args__ = (
        PrimaryKeyConstraint("block_id", "fact_id", name="pk_cv_block_fact_links"),
        Index("ix_cv_block_fact_links_fact_id", "fact_id"),
    )

    block_id: Mapped[str] = mapped_column(
        ForeignKey("cv_blocks.id", ondelete="CASCADE"), nullable=False
    )
    fact_id: Mapped[str] = mapped_column(
        ForeignKey("facts.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    block: Mapped[ManagedCvBlock] = relationship(back_populates="fact_links")
    fact: Mapped[ManagedFact] = relationship(back_populates="block_links")
