from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session, sessionmaker

from app.cv.models import AllowedClaimLevel, FactCategory
from app.managed_cv.form_models import CvBlockEditForm, FactCreateForm, FactEditForm
from app.managed_cv.repository import (
    DuplicateManagedFactKeyError,
    ManagedCvRepository,
)
from app.managed_cv.schema import (
    ManagedCvBlockRecord,
    ManagedCvSectionRecord,
    ManagedCvVariantRecord,
    ManagedFactRecord,
)
from app.profiles.repository import ManagedProfileRepository
from app.profiles.schema import ManagedProfileRecord


class ManagedCvEditorError(ValueError):
    """Raised when managed CV editor operations cannot be completed safely."""


class ManagedCvEditorState(BaseModel):
    model_config = ConfigDict(frozen=True)

    active_profile: ManagedProfileRecord | None
    variants: list[ManagedCvVariantRecord]
    facts: list[ManagedFactRecord]


class ManagedCvSectionWithBlocks(BaseModel):
    model_config = ConfigDict(frozen=True)

    section: ManagedCvSectionRecord
    blocks: list[ManagedCvBlockRecord]


class ManagedCvVariantDetail(BaseModel):
    model_config = ConfigDict(frozen=True)

    active_profile: ManagedProfileRecord
    variant: ManagedCvVariantRecord
    sections: list[ManagedCvSectionWithBlocks]


class ManagedCvBlockEditState(BaseModel):
    model_config = ConfigDict(frozen=True)

    active_profile: ManagedProfileRecord
    variant: ManagedCvVariantRecord
    section: ManagedCvSectionRecord
    block: ManagedCvBlockRecord
    facts: list[ManagedFactRecord]
    linked_fact_ids: set[str]


class ManagedCvFactsState(BaseModel):
    model_config = ConfigDict(frozen=True)

    active_profile: ManagedProfileRecord | None
    facts: list[ManagedFactRecord]


class ManagedCvEditorService:
    def __init__(
        self,
        cv_repository: ManagedCvRepository,
        profile_repository: ManagedProfileRepository,
    ) -> None:
        self._cv_repository = cv_repository
        self._profile_repository = profile_repository

    def load_index(self) -> ManagedCvEditorState:
        active_profile = self._profile_repository.get_active_profile()
        if active_profile is None:
            return ManagedCvEditorState(active_profile=None, variants=[], facts=[])
        return ManagedCvEditorState(
            active_profile=active_profile,
            variants=self._cv_repository.list_cv_variants(active_profile.id),
            facts=self._cv_repository.list_facts(active_profile.id),
        )

    def load_variant_detail(self, variant_id: str) -> ManagedCvVariantDetail:
        active_profile = self._require_active_profile()
        variant = self._require_variant_for_active_profile(
            variant_id, active_profile.id
        )
        sections = [
            ManagedCvSectionWithBlocks(
                section=section,
                blocks=self._cv_repository.list_cv_blocks(section.id),
            )
            for section in self._cv_repository.list_cv_sections(variant.id)
        ]
        return ManagedCvVariantDetail(
            active_profile=active_profile,
            variant=variant,
            sections=sections,
        )

    def load_block_edit(self, block_id: str) -> ManagedCvBlockEditState:
        active_profile = self._require_active_profile()
        block = self._require_block(block_id)
        section = self._require_section(block.section_id)
        variant = self._require_variant_for_active_profile(
            section.variant_id, active_profile.id
        )
        facts = self._cv_repository.list_facts(active_profile.id)
        linked_fact_ids = {
            link.fact_id for link in self._cv_repository.list_block_fact_links(block.id)
        }
        return ManagedCvBlockEditState(
            active_profile=active_profile,
            variant=variant,
            section=section,
            block=block,
            facts=facts,
            linked_fact_ids=linked_fact_ids,
        )

    def update_block(
        self, block_id: str, form: CvBlockEditForm
    ) -> ManagedCvBlockRecord:
        active_profile = self._require_active_profile()
        block = self._require_block(block_id)
        section = self._require_section(block.section_id)
        self._require_variant_for_active_profile(section.variant_id, active_profile.id)
        return self._cv_repository.update_cv_block(
            block_id=block.id,
            content_markdown=form.content_markdown,
            display_order=form.display_order,
            is_enabled=form.is_enabled,
            fact_ids=list(form.selected_fact_ids),
            expected_profile_id=active_profile.id,
        )

    def load_facts(self) -> ManagedCvFactsState:
        active_profile = self._profile_repository.get_active_profile()
        if active_profile is None:
            return ManagedCvFactsState(active_profile=None, facts=[])
        return ManagedCvFactsState(
            active_profile=active_profile,
            facts=self._cv_repository.list_facts(active_profile.id),
        )

    def get_fact_for_edit(self, fact_id: str) -> ManagedFactRecord:
        active_profile = self._require_active_profile()
        fact = self._cv_repository.get_fact(fact_id)
        if fact is None or fact.profile_id != active_profile.id:
            raise ManagedCvEditorError(
                "Managed fact was not found for the active profile."
            )
        return fact

    def create_fact(self, form: FactCreateForm) -> ManagedFactRecord:
        active_profile = self._require_active_profile()
        try:
            return self._cv_repository.create_fact(
                profile_id=active_profile.id,
                fact_key=form.fact_key,
                category=form.category,
                name=form.name,
                allowed_claim_level=form.allowed_claim_level,
                evidence=form.evidence,
                is_active=form.is_active,
            )
        except DuplicateManagedFactKeyError as exc:
            raise ManagedCvEditorError(str(exc)) from exc

    def update_fact(self, fact_id: str, form: FactEditForm) -> ManagedFactRecord:
        active_profile = self._require_active_profile()
        fact = self.get_fact_for_edit(fact_id)
        return self._cv_repository.update_fact(
            fact_id=fact.id,
            category=form.category,
            name=form.name,
            allowed_claim_level=form.allowed_claim_level,
            evidence=form.evidence,
            is_active=form.is_active,
            expected_profile_id=active_profile.id,
        )

    def _require_active_profile(self) -> ManagedProfileRecord:
        active_profile = self._profile_repository.get_active_profile()
        if active_profile is None:
            raise ManagedCvEditorError(
                "No active managed profile is selected. Choose an active profile first."
            )
        return active_profile

    def _require_variant_for_active_profile(
        self, variant_id: str, active_profile_id: str
    ) -> ManagedCvVariantRecord:
        variant = self._cv_repository.get_cv_variant(variant_id)
        if variant is None or variant.profile_id != active_profile_id:
            raise ManagedCvEditorError(
                "CV variant was not found for the active profile."
            )
        return variant

    def _require_section(self, section_id: str) -> ManagedCvSectionRecord:
        section = self._cv_repository.get_cv_section(section_id)
        if section is None:
            raise ManagedCvEditorError("CV section was not found.")
        return section

    def _require_block(self, block_id: str) -> ManagedCvBlockRecord:
        block = self._cv_repository.get_cv_block(block_id)
        if block is None:
            raise ManagedCvEditorError("CV block was not found.")
        return block


def build_managed_cv_editor_service(
    session_factory: sessionmaker[Session],
) -> ManagedCvEditorService:
    return ManagedCvEditorService(
        cv_repository=ManagedCvRepository(session_factory),
        profile_repository=ManagedProfileRepository(session_factory),
    )


FACT_CATEGORY_OPTIONS = [category for category in FactCategory]
ALLOWED_CLAIM_LEVEL_OPTIONS = [level for level in AllowedClaimLevel]
