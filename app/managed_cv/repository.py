from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.cv.models import AllowedClaimLevel, FactCategory
from app.managed_cv.models import (
    ManagedCvBlock,
    ManagedCvBlockFactLink,
    ManagedCvSection,
    ManagedCvVariant,
    ManagedCvVariantAlias,
    ManagedFact,
)
from app.managed_cv.schema import (
    ManagedCvBlockFactLinkRecord,
    ManagedCvBlockRecord,
    ManagedCvSectionRecord,
    ManagedCvVariantAliasRecord,
    ManagedCvVariantRecord,
    ManagedFactRecord,
)


class ManagedCvStorageError(ValueError):
    """Base error for managed CV storage operations."""


class DuplicateCvVariantNameError(ManagedCvStorageError):
    pass


class DuplicateCvVariantAliasError(ManagedCvStorageError):
    pass


class DuplicateManagedFactKeyError(ManagedCvStorageError):
    pass


class DuplicateBlockFactLinkError(ManagedCvStorageError):
    pass


class CrossProfileFactLinkError(ManagedCvStorageError):
    pass


class RelatedManagedCvRecordNotFoundError(ManagedCvStorageError):
    pass


class ManagedCvRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def create_cv_variant(
        self,
        *,
        profile_id: str,
        name: str,
        display_name: str | None = None,
        is_active: bool = True,
    ) -> ManagedCvVariantRecord:
        record = ManagedCvVariantRecord(
            id=_new_id(),
            profile_id=profile_id,
            name=name,
            display_name=display_name,
            is_active=is_active,
        )
        with self._session_factory() as session:
            row = ManagedCvVariant(**record.model_dump())
            session.add(row)
            try:
                session.commit()
            except IntegrityError as exc:
                session.rollback()
                _raise_variant_create_error(session, profile_id, name, exc)
            session.refresh(row)
            return _variant_record(row)

    def list_cv_variants(self, profile_id: str) -> list[ManagedCvVariantRecord]:
        with self._session_factory() as session:
            rows = session.scalars(
                select(ManagedCvVariant)
                .where(ManagedCvVariant.profile_id == profile_id)
                .order_by(ManagedCvVariant.name)
            )
            return [_variant_record(row) for row in rows]

    def get_cv_variant(self, variant_id: str) -> ManagedCvVariantRecord | None:
        with self._session_factory() as session:
            row = session.get(ManagedCvVariant, variant_id)
            return _variant_record(row) if row is not None else None

    def add_variant_alias(
        self, *, variant_id: str, alias: str
    ) -> ManagedCvVariantAliasRecord:
        record = ManagedCvVariantAliasRecord(
            id=_new_id(), variant_id=variant_id, alias=alias
        )
        with self._session_factory() as session:
            _require_row(session, ManagedCvVariant, variant_id, "CV variant")
            row = ManagedCvVariantAlias(**record.model_dump())
            session.add(row)
            try:
                session.commit()
            except IntegrityError as exc:
                session.rollback()
                raise DuplicateCvVariantAliasError(
                    f"Alias {alias!r} already exists for CV variant {variant_id!r}."
                ) from exc
            session.refresh(row)
            return _alias_record(row)

    def list_variant_aliases(
        self, variant_id: str
    ) -> list[ManagedCvVariantAliasRecord]:
        with self._session_factory() as session:
            rows = session.scalars(
                select(ManagedCvVariantAlias)
                .where(ManagedCvVariantAlias.variant_id == variant_id)
                .order_by(ManagedCvVariantAlias.alias)
            )
            return [_alias_record(row) for row in rows]

    def create_cv_section(
        self,
        *,
        variant_id: str,
        section_key: str,
        title: str,
        display_order: int,
        is_required: bool = False,
    ) -> ManagedCvSectionRecord:
        record = ManagedCvSectionRecord(
            id=_new_id(),
            variant_id=variant_id,
            section_key=section_key,
            title=title,
            display_order=display_order,
            is_required=is_required,
        )
        with self._session_factory() as session:
            _require_row(session, ManagedCvVariant, variant_id, "CV variant")
            row = ManagedCvSection(**record.model_dump())
            session.add(row)
            try:
                session.commit()
            except IntegrityError as exc:
                session.rollback()
                raise ManagedCvStorageError(
                    f"Section key {section_key!r} already exists for CV variant "
                    f"{variant_id!r}."
                ) from exc
            session.refresh(row)
            return _section_record(row)

    def list_cv_sections(self, variant_id: str) -> list[ManagedCvSectionRecord]:
        with self._session_factory() as session:
            rows = session.scalars(
                select(ManagedCvSection)
                .where(ManagedCvSection.variant_id == variant_id)
                .order_by(ManagedCvSection.display_order, ManagedCvSection.section_key)
            )
            return [_section_record(row) for row in rows]

    def create_cv_block(
        self,
        *,
        section_id: str,
        block_key: str,
        content_markdown: str,
        display_order: int,
        is_enabled: bool = True,
    ) -> ManagedCvBlockRecord:
        record = ManagedCvBlockRecord(
            id=_new_id(),
            section_id=section_id,
            block_key=block_key,
            content_markdown=content_markdown,
            display_order=display_order,
            is_enabled=is_enabled,
        )
        with self._session_factory() as session:
            _require_row(session, ManagedCvSection, section_id, "CV section")
            row = ManagedCvBlock(**record.model_dump())
            session.add(row)
            try:
                session.commit()
            except IntegrityError as exc:
                session.rollback()
                raise ManagedCvStorageError(
                    f"Block key {block_key!r} already exists for CV section "
                    f"{section_id!r}."
                ) from exc
            session.refresh(row)
            return _block_record(row)

    def list_cv_blocks(self, section_id: str) -> list[ManagedCvBlockRecord]:
        with self._session_factory() as session:
            rows = session.scalars(
                select(ManagedCvBlock)
                .where(ManagedCvBlock.section_id == section_id)
                .order_by(ManagedCvBlock.display_order, ManagedCvBlock.block_key)
            )
            return [_block_record(row) for row in rows]

    def create_fact(
        self,
        *,
        profile_id: str,
        fact_key: str,
        category: FactCategory,
        name: str,
        allowed_claim_level: AllowedClaimLevel,
        evidence: str,
        is_active: bool = True,
    ) -> ManagedFactRecord:
        record = ManagedFactRecord(
            id=_new_id(),
            profile_id=profile_id,
            fact_key=fact_key,
            category=category,
            name=name,
            allowed_claim_level=allowed_claim_level,
            evidence=evidence,
            is_active=is_active,
        )
        with self._session_factory() as session:
            row = ManagedFact(**_fact_row_values(record))
            session.add(row)
            try:
                session.commit()
            except IntegrityError as exc:
                session.rollback()
                _raise_fact_create_error(session, profile_id, fact_key, exc)
            session.refresh(row)
            return _fact_record(row)

    def list_facts(self, profile_id: str) -> list[ManagedFactRecord]:
        with self._session_factory() as session:
            rows = session.scalars(
                select(ManagedFact)
                .where(ManagedFact.profile_id == profile_id)
                .order_by(ManagedFact.fact_key)
            )
            return [_fact_record(row) for row in rows]

    def link_block_to_fact(
        self, *, block_id: str, fact_id: str
    ) -> ManagedCvBlockFactLinkRecord:
        record = ManagedCvBlockFactLinkRecord(block_id=block_id, fact_id=fact_id)
        with self._session_factory() as session:
            block = _require_row(session, ManagedCvBlock, block_id, "CV block")
            fact = _require_row(session, ManagedFact, fact_id, "Fact")
            _validate_block_and_fact_share_profile(session, block, fact)
            row = ManagedCvBlockFactLink(**record.model_dump())
            session.add(row)
            try:
                session.commit()
            except IntegrityError as exc:
                session.rollback()
                raise DuplicateBlockFactLinkError(
                    f"CV block {block_id!r} is already linked to fact {fact_id!r}."
                ) from exc
            return record

    def list_block_fact_links(
        self, block_id: str
    ) -> list[ManagedCvBlockFactLinkRecord]:
        with self._session_factory() as session:
            rows = session.scalars(
                select(ManagedCvBlockFactLink)
                .where(ManagedCvBlockFactLink.block_id == block_id)
                .order_by(ManagedCvBlockFactLink.fact_id)
            )
            return [_link_record(row) for row in rows]


def _new_id() -> str:
    return str(uuid4())


def _require_row[T](session: Session, model: type[T], row_id: str, label: str) -> T:
    row = session.get(model, row_id)
    if row is None:
        raise RelatedManagedCvRecordNotFoundError(f"{label} {row_id!r} was not found.")
    return row


def _validate_block_and_fact_share_profile(
    session: Session, block: ManagedCvBlock, fact: ManagedFact
) -> None:
    section = _require_row(session, ManagedCvSection, block.section_id, "CV section")
    variant = _require_row(session, ManagedCvVariant, section.variant_id, "CV variant")
    if variant.profile_id != fact.profile_id:
        raise CrossProfileFactLinkError(
            "CV block and fact belong to different managed profiles: "
            f"block profile {variant.profile_id!r}, fact profile {fact.profile_id!r}."
        )


def _raise_variant_create_error(
    session: Session, profile_id: str, name: str, exc: IntegrityError
) -> None:
    duplicate = session.scalar(
        select(ManagedCvVariant).where(
            ManagedCvVariant.profile_id == profile_id, ManagedCvVariant.name == name
        )
    )
    if duplicate is not None:
        raise DuplicateCvVariantNameError(
            f"A CV variant named {name!r} already exists for profile {profile_id!r}."
        ) from exc
    raise RelatedManagedCvRecordNotFoundError(
        f"Managed profile {profile_id!r} was not found."
    ) from exc


def _raise_fact_create_error(
    session: Session, profile_id: str, fact_key: str, exc: IntegrityError
) -> None:
    duplicate = session.scalar(
        select(ManagedFact).where(
            ManagedFact.profile_id == profile_id, ManagedFact.fact_key == fact_key
        )
    )
    if duplicate is not None:
        raise DuplicateManagedFactKeyError(
            f"A fact with key {fact_key!r} already exists for profile {profile_id!r}."
        ) from exc
    raise RelatedManagedCvRecordNotFoundError(
        f"Managed profile {profile_id!r} was not found."
    ) from exc


def _variant_record(row: ManagedCvVariant) -> ManagedCvVariantRecord:
    return ManagedCvVariantRecord(
        id=row.id,
        profile_id=row.profile_id,
        name=row.name,
        display_name=row.display_name,
        is_active=bool(row.is_active),
    )


def _alias_record(row: ManagedCvVariantAlias) -> ManagedCvVariantAliasRecord:
    return ManagedCvVariantAliasRecord(
        id=row.id, variant_id=row.variant_id, alias=row.alias
    )


def _section_record(row: ManagedCvSection) -> ManagedCvSectionRecord:
    return ManagedCvSectionRecord(
        id=row.id,
        variant_id=row.variant_id,
        section_key=row.section_key,
        title=row.title,
        display_order=row.display_order,
        is_required=bool(row.is_required),
    )


def _block_record(row: ManagedCvBlock) -> ManagedCvBlockRecord:
    return ManagedCvBlockRecord(
        id=row.id,
        section_id=row.section_id,
        block_key=row.block_key,
        content_markdown=row.content_markdown,
        display_order=row.display_order,
        is_enabled=bool(row.is_enabled),
    )


def _fact_record(row: ManagedFact) -> ManagedFactRecord:
    return ManagedFactRecord(
        id=row.id,
        profile_id=row.profile_id,
        fact_key=row.fact_key,
        category=FactCategory(row.category),
        name=row.name,
        allowed_claim_level=AllowedClaimLevel(row.allowed_claim_level),
        evidence=row.evidence,
        is_active=bool(row.is_active),
    )


def _fact_row_values(record: ManagedFactRecord) -> dict[str, object]:
    values = record.model_dump()
    values["category"] = record.category.value
    values["allowed_claim_level"] = record.allowed_claim_level.value
    return values


def _link_record(row: ManagedCvBlockFactLink) -> ManagedCvBlockFactLinkRecord:
    return ManagedCvBlockFactLinkRecord(block_id=row.block_id, fact_id=row.fact_id)
