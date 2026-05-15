from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from app.core.config import ProjectConfig
from app.core.paths import ProfilePaths
from app.cv.fact_bank import load_fact_bank
from app.cv.markdown_loader import load_markdown_file
from app.cv.models import CvSectionName, Fact, FactBank, LoadedCv
from app.cv.section_parser import REQUIRED_SECTION_MARKERS, parse_cv_sections
from app.cv.selector import select_cv_variant
from app.managed_cv.repository import ManagedCvRepository
from app.managed_cv.schema import (
    ManagedCvBlockRecord,
    ManagedCvSectionRecord,
    ManagedCvVariantRecord,
    ManagedFactRecord,
)
from app.profiles.repository import ManagedProfileRepository
from app.profiles.schema import ManagedProfileRecord
from app.settings.init import initialise_app_settings_storage
from app.storage.app_dirs import AppDataPaths

CvSourceType = Literal["managed", "file_based"]


class CvSourceError(ValueError):
    """Raised when pipeline CV/fact source selection cannot complete safely."""


@dataclass(frozen=True)
class CvSourceMetadata:
    source_type: CvSourceType
    variant_name: str
    profile_name: str
    message: str


@dataclass(frozen=True)
class LoadedCvSource:
    loaded_cv: LoadedCv
    fact_bank: FactBank
    metadata: CvSourceMetadata


class PipelineCvSourceLoader:
    """Resolve pipeline-compatible CV and fact data from managed or file sources."""

    def __init__(
        self,
        *,
        config: ProjectConfig,
        profile_paths: ProfilePaths,
        app_data_paths: AppDataPaths | None = None,
    ) -> None:
        self._config = config
        self._profile_paths = profile_paths
        self._app_data_paths = app_data_paths

    def load(self, *, selected_variant: str) -> LoadedCvSource:
        selected_variant = _clean_selected_variant(selected_variant)
        managed_context = self._managed_context()
        if managed_context is not None:
            managed_source = self._load_managed_if_available(
                managed_context=managed_context,
                selected_variant=selected_variant,
            )
            if managed_source is not None:
                return managed_source

        return self._load_file_based(selected_variant=selected_variant)

    def check_readiness(self, *, selected_variant: str) -> CvSourceMetadata:
        return self.load(selected_variant=selected_variant).metadata

    def _active_profile_matches_runtime(
        self,
        active_profile: ManagedProfileRecord,
    ) -> bool:
        if active_profile.name != self._config.app.profile_name:
            return False

        return _normalise_path(active_profile.data_dir) == _normalise_path(
            self._profile_paths.profile_dir
        )

    def _managed_context(self) -> _ManagedContext | None:
        if self._app_data_paths is None:
            return None

        settings_service = initialise_app_settings_storage(self._app_data_paths)
        session_factory = settings_service.session_factory
        active_profile = ManagedProfileRepository(session_factory).get_active_profile()
        if active_profile is None:
            return None

        if not self._active_profile_matches_runtime(active_profile):
            raise CvSourceError(
                "The active managed profile does not match the current runtime "
                "profile. Select the matching active profile or update the runtime "
                "profile settings before running the local pipeline."
            )

        return _ManagedContext(
            active_profile=active_profile,
            repository=ManagedCvRepository(session_factory),
        )

    def _active_profile_matches_runtime(
        self,
        active_profile: ManagedProfileRecord,
    ) -> bool:
        if active_profile.name != self._config.app.profile_name:
            return False

        return _normalise_path(active_profile.data_dir) == _normalise_path(
            self._profile_paths.profile_dir
        )

    def _load_managed_if_available(
        self,
        *,
        managed_context: _ManagedContext,
        selected_variant: str,
    ) -> LoadedCvSource | None:
        repository = managed_context.repository
        all_variants = repository.list_cv_variants(managed_context.active_profile.id)
        if not all_variants:
            return None

        active_variants = [variant for variant in all_variants if variant.is_active]
        variant = self._select_active_managed_variant(
            repository=repository,
            active_variants=active_variants,
            selected_variant=selected_variant,
        )
        if variant is None:
            raise CvSourceError(
                "Selected managed CV variant is not available for the active profile. "
                "Choose an active managed variant or import it before running the "
                "local pipeline."
            )

        active_facts = [
            fact
            for fact in repository.list_facts(managed_context.active_profile.id)
            if fact.is_active
        ]
        if not active_facts:
            raise CvSourceError(
                "Managed CV storage is selected, but the active profile has no active "
                "managed facts. Add or reactivate verified facts before running the "
                "local pipeline."
            )

        markdown = self._compose_managed_markdown(
            repository=repository,
            variant=variant,
            profile_id=managed_context.active_profile.id,
            active_facts_by_id={fact.id: fact for fact in active_facts},
        )
        sections = parse_cv_sections(markdown)
        return LoadedCvSource(
            loaded_cv=LoadedCv(
                path=Path("managed_cv") / f"{variant.name}.md",
                markdown=markdown,
                sections=sections,
            ),
            fact_bank=FactBank(
                facts=[_managed_fact_to_fact(fact) for fact in active_facts]
            ),
            metadata=CvSourceMetadata(
                source_type="managed",
                variant_name=variant.name,
                profile_name=managed_context.active_profile.name,
                message="Managed CV/fact storage was used for this pipeline run.",
            ),
        )

    def _select_active_managed_variant(
        self,
        *,
        repository: ManagedCvRepository,
        active_variants: list[ManagedCvVariantRecord],
        selected_variant: str,
    ) -> ManagedCvVariantRecord | None:
        for variant in active_variants:
            if variant.name == selected_variant:
                return variant

        for variant in active_variants:
            aliases = repository.list_variant_aliases(variant.id)
            if any(alias.alias == selected_variant for alias in aliases):
                return variant

        return None

    def _compose_managed_markdown(
        self,
        *,
        repository: ManagedCvRepository,
        variant: ManagedCvVariantRecord,
        profile_id: str,
        active_facts_by_id: dict[str, ManagedFactRecord],
    ) -> str:
        sections = repository.list_cv_sections(variant.id)
        sections_by_key = {section.section_key: section for section in sections}
        missing_sections = [
            section_name.value
            for section_name in REQUIRED_SECTION_MARKERS
            if section_name.value not in sections_by_key
        ]
        if missing_sections:
            raise CvSourceError(
                "Selected managed CV variant is missing required sections: "
                + ", ".join(missing_sections)
                + "."
            )

        chunks = [f"# {variant.display_name or variant.name}"]
        for section in sections:
            enabled_blocks = [
                block
                for block in repository.list_cv_blocks(section.id)
                if block.is_enabled
            ]
            if _required_section_name(section.section_key) is not None:
                self._validate_required_section_blocks(section, enabled_blocks)
            self._validate_block_fact_links(
                repository=repository,
                blocks=enabled_blocks,
                profile_id=profile_id,
                active_facts_by_id=active_facts_by_id,
            )
            chunks.append(_render_section(section, enabled_blocks))

        return "\n\n".join(chunk for chunk in chunks if chunk.strip()).strip() + "\n"

    def _validate_required_section_blocks(
        self,
        section: ManagedCvSectionRecord,
        enabled_blocks: list[ManagedCvBlockRecord],
    ) -> None:
        if not enabled_blocks:
            raise CvSourceError(
                "Selected managed CV variant has no enabled blocks for required "
                f"section {section.section_key!r}."
            )
        if not any(block.content_markdown.strip() for block in enabled_blocks):
            raise CvSourceError(
                "Selected managed CV variant has no content in enabled blocks for "
                f"required section {section.section_key!r}."
            )

    def _validate_block_fact_links(
        self,
        *,
        repository: ManagedCvRepository,
        blocks: list[ManagedCvBlockRecord],
        profile_id: str,
        active_facts_by_id: dict[str, ManagedFactRecord],
    ) -> None:
        for block in blocks:
            for link in repository.list_block_fact_links(block.id):
                linked_fact = repository.get_fact(link.fact_id)
                if linked_fact is None:
                    raise CvSourceError(
                        "Selected managed CV variant has a block linked to a missing "
                        "fact. Remove the stale link before running the local pipeline."
                    )
                if linked_fact.profile_id != profile_id:
                    raise CvSourceError(
                        "Selected managed CV variant has a block linked to a fact from "
                        "another profile. Remove the invalid link before running the "
                        "local pipeline."
                    )
                if link.fact_id not in active_facts_by_id:
                    raise CvSourceError(
                        "Selected managed CV variant has a block linked to an inactive "
                        "fact. Reactivate the fact or remove the link before running "
                        "the local pipeline."
                    )

    def _load_file_based(self, *, selected_variant: str) -> LoadedCvSource:
        selected_cv = select_cv_variant(
            cv_dir=self._profile_paths.cv_dir,
            variant_name=selected_variant,
            is_example_profile=self._config.app.profile_name == "example",
        )
        loaded_cv = LoadedCv(
            path=selected_cv.path,
            markdown=load_markdown_file(selected_cv.path),
            sections=parse_cv_sections(selected_cv.markdown),
        )
        return LoadedCvSource(
            loaded_cv=loaded_cv,
            fact_bank=load_fact_bank(self._profile_paths.fact_bank),
            metadata=CvSourceMetadata(
                source_type="file_based",
                variant_name=selected_cv.variant_name,
                profile_name=self._config.app.profile_name,
                message="File-based CV/fact fallback was used for this pipeline run.",
            ),
        )


@dataclass(frozen=True)
class _ManagedContext:
    active_profile: ManagedProfileRecord
    repository: ManagedCvRepository


def _clean_selected_variant(selected_variant: str) -> str:
    cleaned = selected_variant.strip()
    if not cleaned:
        raise CvSourceError("Selected CV variant must not be empty.")
    return cleaned


def _normalise_path(path: Path) -> Path:
    return path.expanduser().resolve(strict=False)


def _managed_fact_to_fact(fact: ManagedFactRecord) -> Fact:
    return Fact(
        id=fact.fact_key,
        category=fact.category,
        name=fact.name,
        allowed_claim_level=fact.allowed_claim_level,
        evidence=fact.evidence,
    )


def _render_section(
    section: ManagedCvSectionRecord,
    enabled_blocks: list[ManagedCvBlockRecord],
) -> str:
    content = "\n\n".join(
        block.content_markdown.strip()
        for block in enabled_blocks
        if block.content_markdown.strip()
    )
    section_name = _required_section_name(section.section_key)
    if section_name is None:
        heading = f"## {section.title.strip()}"
        return f"{heading}\n\n{content}" if content else heading

    start_marker, end_marker = REQUIRED_SECTION_MARKERS[section_name]
    return f"{start_marker}\n{content}\n{end_marker}"


def _required_section_name(section_key: str) -> CvSectionName | None:
    for section_name in REQUIRED_SECTION_MARKERS:
        if section_name.value == section_key:
            return section_name
    return None
