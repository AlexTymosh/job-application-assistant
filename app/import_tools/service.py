from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from uuid import uuid4

import yaml
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import ProjectConfig, load_profile_config
from app.import_tools.cv_import import (
    load_markdown_variants,
    planned_variant_from_loaded,
)
from app.import_tools.fact_import import load_planned_facts
from app.import_tools.models import (
    ImportAction,
    ImportApplyResult,
    ImportPreview,
    ImportTotals,
    PlannedCvBlock,
    PlannedCvSection,
    PlannedCvVariant,
    PlannedFact,
)
from app.managed_cv.models import (
    ManagedCvBlock,
    ManagedCvSection,
    ManagedCvVariant,
    ManagedFact,
)
from app.profiles.repository import ManagedProfileRepository
from app.profiles.schema import ManagedProfileRecord, ManagedProfileType
from app.profiles.service import ManagedProfileError, ManagedProfileService


class ImportToolsError(ValueError):
    """Base error for file-based profile import tools."""


class ImportApplyBlockedError(ImportToolsError):
    pass


_EXPECTED_IMPORT_EXCEPTIONS = (
    FileNotFoundError,
    OSError,
    ValueError,
    ValidationError,
    yaml.YAMLError,
)


class ManagedCvImportService:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory
        self._profile_service = ManagedProfileService(
            ManagedProfileRepository(session_factory)
        )

    def preview_import(self) -> ImportPreview:
        profile = self._load_active_file_based_profile()
        config = self._load_validated_profile_config(profile)
        try:
            loaded_variants = load_markdown_variants(profile.data_dir, config)
            loaded_facts = load_planned_facts(profile.name, profile.data_dir)
        except _EXPECTED_IMPORT_EXCEPTIONS as exc:
            message = _safe_exception_message(exc, profile.data_dir)
            raise ImportToolsError(
                f"Import source could not be loaded: {message}"
            ) from exc

        planned_variants = [
            planned_variant_from_loaded(variant) for variant in loaded_variants
        ]
        with self._session_factory() as session:
            cv_variants = [
                self._classify_variant(session, profile.id, variant)
                for variant in planned_variants
            ]
            facts = [
                self._classify_fact(session, profile.id, fact) for fact in loaded_facts
            ]

        conflicts = _collect_conflicts(cv_variants, facts)
        return ImportPreview(
            source_profile_id=profile.id,
            source_profile_name=profile.name,
            source_profile_path=profile.data_dir,
            source_profile_path_label=_safe_profile_path_label(profile.data_dir),
            cv_variants=cv_variants,
            facts=facts,
            conflicts=conflicts,
            apply_allowed=not conflicts,
            totals=_build_totals(cv_variants, facts),
        )

    def apply_import(self) -> ImportApplyResult:
        preview = self.preview_import()
        if not preview.apply_allowed:
            raise ImportApplyBlockedError(
                "Import has conflicts. Review the preview and resolve conflicts "
                "before applying."
            )

        created_variants = 0
        created_sections = 0
        created_blocks = 0
        created_facts = 0
        with self._session_factory() as session, session.begin():
            for variant in preview.cv_variants:
                variant_row = session.scalar(
                    select(ManagedCvVariant).where(
                        ManagedCvVariant.profile_id == preview.source_profile_id,
                        ManagedCvVariant.name == variant.name,
                    )
                )
                if variant_row is None:
                    variant_row = ManagedCvVariant(
                        id=_new_id(),
                        profile_id=preview.source_profile_id,
                        name=variant.name,
                        display_name=variant.display_name,
                        is_active=True,
                    )
                    session.add(variant_row)
                    session.flush()
                    created_variants += 1
                for section in variant.sections:
                    section_row = session.scalar(
                        select(ManagedCvSection).where(
                            ManagedCvSection.variant_id == variant_row.id,
                            ManagedCvSection.section_key == section.section_key,
                        )
                    )
                    if section_row is None:
                        section_row = ManagedCvSection(
                            id=_new_id(),
                            variant_id=variant_row.id,
                            section_key=section.section_key,
                            title=section.title,
                            display_order=section.display_order,
                            is_required=section.is_required,
                        )
                        session.add(section_row)
                        session.flush()
                        created_sections += 1
                    for block in section.blocks:
                        block_row = session.scalar(
                            select(ManagedCvBlock).where(
                                ManagedCvBlock.section_id == section_row.id,
                                ManagedCvBlock.block_key == block.block_key,
                            )
                        )
                        if block_row is None:
                            session.add(
                                ManagedCvBlock(
                                    id=_new_id(),
                                    section_id=section_row.id,
                                    block_key=block.block_key,
                                    content_markdown=block.content_markdown,
                                    display_order=block.display_order,
                                    is_enabled=block.is_enabled,
                                )
                            )
                            created_blocks += 1
            for fact in preview.facts:
                fact_row = session.scalar(
                    select(ManagedFact).where(
                        ManagedFact.profile_id == preview.source_profile_id,
                        ManagedFact.fact_key == fact.fact_key,
                    )
                )
                if fact_row is None:
                    session.add(
                        ManagedFact(
                            id=_new_id(),
                            profile_id=preview.source_profile_id,
                            fact_key=fact.fact_key,
                            category=fact.category.value,
                            name=fact.name,
                            allowed_claim_level=fact.allowed_claim_level.value,
                            evidence=fact.evidence,
                            is_active=fact.is_active,
                        )
                    )
                    created_facts += 1

        refreshed_preview = self.preview_import()
        return ImportApplyResult(
            preview=refreshed_preview,
            created_variants=created_variants,
            created_sections=created_sections,
            created_blocks=created_blocks,
            created_facts=created_facts,
        )

    def _load_active_file_based_profile(self) -> ManagedProfileRecord:
        try:
            profile = self._profile_service.get_active_profile()
        except ManagedProfileError as exc:
            raise ImportToolsError(str(exc)) from exc
        if profile is None:
            raise ImportToolsError("No active managed profile is configured.")
        if profile.profile_type is not ManagedProfileType.FILE_BASED:
            raise ImportToolsError("The active managed profile is not file-based.")
        return profile

    def _load_validated_profile_config(
        self, profile: ManagedProfileRecord
    ) -> ProjectConfig:
        try:
            validation = self._profile_service.validate_profile(profile)
        except ManagedProfileError as exc:
            raise ImportToolsError(
                _safe_exception_message(exc, profile.data_dir)
            ) from exc
        if not validation.ok:
            raise ImportToolsError(
                _safe_error_text(validation.message, profile.data_dir)
            )
        config_file = profile.data_dir / _config_filename(profile.name)
        try:
            return load_profile_config(config_file)
        except _EXPECTED_IMPORT_EXCEPTIONS as exc:
            message = _safe_exception_message(exc, profile.data_dir)
            raise ImportToolsError(
                f"Profile config could not be loaded: {message}"
            ) from exc

    def _classify_variant(
        self, session: Session, profile_id: str, planned: PlannedCvVariant
    ) -> PlannedCvVariant:
        existing = session.scalar(
            select(ManagedCvVariant).where(
                ManagedCvVariant.profile_id == profile_id,
                ManagedCvVariant.name == planned.name,
            )
        )
        if existing is None:
            return planned

        variant_conflicts = []
        if existing.display_name != planned.display_name or not bool(
            existing.is_active
        ):
            variant_conflicts.append("managed CV variant metadata differs")
        sections = [
            self._classify_section(session, existing.id, section)
            for section in planned.sections
        ]
        section_conflicts = [
            section.message
            for section in sections
            if section.action is ImportAction.CONFLICT and section.message
        ]
        if variant_conflicts or section_conflicts:
            return planned.model_copy(
                update={
                    "action": ImportAction.CONFLICT,
                    "message": "; ".join(variant_conflicts + section_conflicts),
                    "sections": sections,
                }
            )
        return planned.model_copy(
            update={
                "action": ImportAction.SKIP,
                "message": "Managed CV variant already exists with matching imported "
                "content.",
                "sections": sections,
            }
        )

    def _classify_section(
        self, session: Session, variant_id: str, planned: PlannedCvSection
    ) -> PlannedCvSection:
        existing = session.scalar(
            select(ManagedCvSection).where(
                ManagedCvSection.variant_id == variant_id,
                ManagedCvSection.section_key == planned.section_key,
            )
        )
        if existing is None:
            return planned

        conflicts = []
        if (
            existing.title != planned.title
            or existing.display_order != planned.display_order
            or bool(existing.is_required) != planned.is_required
        ):
            conflicts.append(f"section {planned.section_key!r} metadata differs")
        blocks = [
            self._classify_block(session, existing.id, block)
            for block in planned.blocks
        ]
        block_conflicts = [
            block.message
            for block in blocks
            if block.action is ImportAction.CONFLICT and block.message
        ]
        if conflicts or block_conflicts:
            return planned.model_copy(
                update={
                    "action": ImportAction.CONFLICT,
                    "message": "; ".join(conflicts + block_conflicts),
                    "blocks": blocks,
                }
            )
        return planned.model_copy(
            update={
                "action": ImportAction.SKIP,
                "message": f"Section {planned.section_key!r} already exists with "
                "matching imported content.",
                "blocks": blocks,
            }
        )

    def _classify_block(
        self, session: Session, section_id: str, planned: PlannedCvBlock
    ) -> PlannedCvBlock:
        existing = session.scalar(
            select(ManagedCvBlock).where(
                ManagedCvBlock.section_id == section_id,
                ManagedCvBlock.block_key == planned.block_key,
            )
        )
        if existing is None:
            return planned
        if (
            existing.content_markdown != planned.content_markdown
            or existing.display_order != planned.display_order
            or bool(existing.is_enabled) != planned.is_enabled
        ):
            return planned.model_copy(
                update={
                    "action": ImportAction.CONFLICT,
                    "message": f"block {planned.block_key!r} content or metadata "
                    "differs",
                }
            )
        return planned.model_copy(
            update={
                "action": ImportAction.SKIP,
                "message": f"Block {planned.block_key!r} already exists with "
                "matching content.",
            }
        )

    def _classify_fact(
        self, session: Session, profile_id: str, planned: PlannedFact
    ) -> PlannedFact:
        existing = session.scalar(
            select(ManagedFact).where(
                ManagedFact.profile_id == profile_id,
                ManagedFact.fact_key == planned.fact_key,
            )
        )
        if existing is None:
            return planned
        if (
            existing.category != planned.category.value
            or existing.name != planned.name
            or existing.allowed_claim_level != planned.allowed_claim_level.value
            or existing.evidence != planned.evidence
            or bool(existing.is_active) != planned.is_active
        ):
            return planned.model_copy(
                update={
                    "action": ImportAction.CONFLICT,
                    "message": f"fact {planned.fact_key!r} content or metadata differs",
                }
            )
        return planned.model_copy(
            update={
                "action": ImportAction.SKIP,
                "message": f"Fact {planned.fact_key!r} already exists with "
                "matching content.",
            }
        )


def _collect_conflicts(
    variants: Sequence[PlannedCvVariant], facts: Sequence[PlannedFact]
) -> list[str]:
    conflicts: list[str] = []
    for variant in variants:
        if variant.action is ImportAction.CONFLICT and variant.message:
            conflicts.append(f"CV variant {variant.name}: {variant.message}")
        for section in variant.sections:
            if section.action is ImportAction.CONFLICT and section.message:
                conflicts.append(
                    "CV variant "
                    f"{variant.name}, section {section.section_key}: "
                    f"{section.message}"
                )
            for block in section.blocks:
                if block.action is ImportAction.CONFLICT and block.message:
                    conflicts.append(
                        "CV variant "
                        f"{variant.name}, section {section.section_key}, "
                        f"block {block.block_key}: "
                        f"{block.message}"
                    )
    for fact in facts:
        if fact.action is ImportAction.CONFLICT and fact.message:
            conflicts.append(f"Fact {fact.fact_key}: {fact.message}")
    return conflicts


def _build_totals(
    variants: Sequence[PlannedCvVariant], facts: Sequence[PlannedFact]
) -> ImportTotals:
    totals = {
        "variants_create": 0,
        "variants_skip": 0,
        "sections_create": 0,
        "sections_skip": 0,
        "blocks_create": 0,
        "blocks_skip": 0,
        "facts_create": 0,
        "facts_skip": 0,
        "conflicts": 0,
    }
    for variant in variants:
        _count_action(totals, "variants", variant.action)
        for section in variant.sections:
            _count_action(totals, "sections", section.action)
            for block in section.blocks:
                _count_action(totals, "blocks", block.action)
    for fact in facts:
        _count_action(totals, "facts", fact.action)
    return ImportTotals(**totals)


def _count_action(totals: dict[str, int], prefix: str, action: ImportAction) -> None:
    if action is ImportAction.CREATE:
        totals[f"{prefix}_create"] += 1
    elif action is ImportAction.SKIP:
        totals[f"{prefix}_skip"] += 1
    elif action is ImportAction.CONFLICT:
        totals["conflicts"] += 1


def _safe_profile_path_label(path: Path) -> str:
    return path.name or "connected profile folder"


def _safe_exception_message(exc: BaseException, private_root: Path) -> str:
    message = str(exc).strip() or exc.__class__.__name__
    return _safe_error_text(message, private_root)


def _safe_error_text(message: str, private_root: Path) -> str:
    safe_message = message
    private_path_labels = {str(private_root), private_root.as_posix()}
    try:
        resolved_root = private_root.resolve()
    except OSError:
        resolved_root = private_root
    private_path_labels.update({str(resolved_root), resolved_root.as_posix()})
    for private_path_label in sorted(private_path_labels, key=len, reverse=True):
        if private_path_label:
            safe_message = safe_message.replace(
                private_path_label, "connected profile folder"
            )
    return safe_message


def _config_filename(profile_name: str) -> str:
    return "config.example.yaml" if profile_name == "example" else "config.yaml"


def _new_id() -> str:
    return str(uuid4())
