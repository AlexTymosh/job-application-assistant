from __future__ import annotations

from pathlib import Path

import pytest

from app.cv.models import AllowedClaimLevel, FactCategory
from app.managed_cv.editor_service import (
    ManagedCvEditorError,
    build_managed_cv_editor_service,
)
from app.managed_cv.form_models import CvBlockEditForm, FactCreateForm, FactEditForm
from app.managed_cv.repository import CrossProfileFactLinkError, ManagedCvRepository
from app.profiles.repository import ManagedProfileRepository
from app.profiles.schema import ManagedProfileType
from app.settings.migrations import migrate_app_settings_database
from app.settings.session import create_settings_engine, create_settings_session_factory


@pytest.fixture
def editor_environment(tmp_path: Path):  # type: ignore[no-untyped-def]
    database_file = tmp_path / "app.sqlite3"
    migrate_app_settings_database(database_file)
    engine = create_settings_engine(database_file)
    session_factory = create_settings_session_factory(engine)
    return (
        build_managed_cv_editor_service(session_factory),
        ManagedCvRepository(session_factory),
        ManagedProfileRepository(session_factory),
    )


def _profile(
    repository: ManagedProfileRepository, profile_id: str, *, active: bool
) -> str:
    repository.create_profile(
        profile_id=profile_id,
        name=profile_id,
        display_name=None,
        profile_type=ManagedProfileType.FILE_BASED,
        data_dir=Path(f"/tmp/{profile_id}"),
        is_active=active,
    )
    return profile_id


def _variant_with_block(cv_repository: ManagedCvRepository, profile_id: str):  # type: ignore[no-untyped-def]
    variant = cv_repository.create_cv_variant(profile_id=profile_id, name="backend")
    section = cv_repository.create_cv_section(
        variant_id=variant.id, section_key="summary", title="Summary", display_order=0
    )
    block = cv_repository.create_cv_block(
        section_id=section.id,
        block_key="intro",
        content_markdown="Original content",
        display_order=0,
    )
    return variant, section, block


def _fact(cv_repository: ManagedCvRepository, profile_id: str, key: str):
    return cv_repository.create_fact(
        profile_id=profile_id,
        fact_key=key,
        category=FactCategory.SKILL,
        name=f"Fact {key}",
        allowed_claim_level=AllowedClaimLevel.PRACTICAL,
        evidence="Verified fake evidence for testing.",
    )


def test_index_handles_missing_active_profile(editor_environment) -> None:  # type: ignore[no-untyped-def]
    service, _cv_repository, _profile_repository = editor_environment

    state = service.load_index()

    assert state.active_profile is None
    assert state.variants == []
    assert state.facts == []


def test_variant_detail_lists_sections_and_blocks_in_order(editor_environment) -> None:  # type: ignore[no-untyped-def]
    service, cv_repository, profile_repository = editor_environment
    profile_id = _profile(profile_repository, "profile-a", active=True)
    variant = cv_repository.create_cv_variant(profile_id=profile_id, name="backend")
    later = cv_repository.create_cv_section(
        variant_id=variant.id,
        section_key="projects",
        title="Projects",
        display_order=20,
    )
    earlier = cv_repository.create_cv_section(
        variant_id=variant.id, section_key="summary", title="Summary", display_order=10
    )
    cv_repository.create_cv_block(
        section_id=earlier.id, block_key="b", content_markdown="B", display_order=20
    )
    cv_repository.create_cv_block(
        section_id=earlier.id, block_key="a", content_markdown="A", display_order=10
    )
    cv_repository.create_cv_block(
        section_id=later.id, block_key="c", content_markdown="C", display_order=10
    )

    detail = service.load_variant_detail(variant.id)

    assert [item.section.section_key for item in detail.sections] == [
        "summary",
        "projects",
    ]
    assert [block.block_key for block in detail.sections[0].blocks] == ["a", "b"]


def test_block_update_changes_content_flags_and_links_same_profile_fact(
    editor_environment,
) -> None:  # type: ignore[no-untyped-def]
    service, cv_repository, profile_repository = editor_environment
    profile_id = _profile(profile_repository, "profile-a", active=True)
    _variant, _section, block = _variant_with_block(cv_repository, profile_id)
    fact = _fact(cv_repository, profile_id, "python")

    updated = service.update_block(
        block.id,
        CvBlockEditForm(
            content_markdown="Updated content",
            display_order=5,
            is_enabled=False,
            selected_fact_ids=(fact.id,),
        ),
    )

    assert updated.content_markdown == "Updated content"
    assert updated.display_order == 5
    assert updated.is_enabled is False
    assert [link.fact_id for link in cv_repository.list_block_fact_links(block.id)] == [
        fact.id
    ]


def test_block_update_rejects_cross_profile_fact(editor_environment) -> None:  # type: ignore[no-untyped-def]
    service, cv_repository, profile_repository = editor_environment
    active_profile_id = _profile(profile_repository, "profile-a", active=True)
    other_profile_id = _profile(profile_repository, "profile-b", active=False)
    _variant, _section, block = _variant_with_block(cv_repository, active_profile_id)
    other_fact = _fact(cv_repository, other_profile_id, "python")

    with pytest.raises(CrossProfileFactLinkError):
        service.update_block(
            block.id,
            CvBlockEditForm(
                content_markdown="Updated content",
                display_order=0,
                is_enabled=True,
                selected_fact_ids=(other_fact.id,),
            ),
        )


def test_create_fact_rejects_duplicate_key(editor_environment) -> None:  # type: ignore[no-untyped-def]
    service, cv_repository, profile_repository = editor_environment
    profile_id = _profile(profile_repository, "profile-a", active=True)
    _fact(cv_repository, profile_id, "python")

    with pytest.raises(ManagedCvEditorError):
        service.create_fact(
            FactCreateForm(
                fact_key="python",
                category=FactCategory.SKILL,
                name="Python",
                allowed_claim_level=AllowedClaimLevel.STRONG,
                evidence="Verified fake evidence.",
                is_active=True,
            )
        )


def test_edit_fact_updates_mutable_fields(editor_environment) -> None:  # type: ignore[no-untyped-def]
    service, cv_repository, profile_repository = editor_environment
    profile_id = _profile(profile_repository, "profile-a", active=True)
    fact = _fact(cv_repository, profile_id, "python")

    updated = service.update_fact(
        fact.id,
        FactEditForm(
            category=FactCategory.PROJECT,
            name="API platform",
            allowed_claim_level=AllowedClaimLevel.STRONG,
            evidence="Verified project evidence.",
            is_active=False,
        ),
    )

    assert updated.fact_key == "python"
    assert updated.category == FactCategory.PROJECT
    assert updated.name == "API platform"
    assert updated.allowed_claim_level == AllowedClaimLevel.STRONG
    assert updated.evidence == "Verified project evidence."
    assert updated.is_active is False
