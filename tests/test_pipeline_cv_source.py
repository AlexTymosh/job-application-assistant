from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from app.core.config import ProjectConfig, load_profile_config
from app.core.paths import build_profile_paths
from app.cv.models import AllowedClaimLevel, CvSectionName, FactCategory
from app.cv.section_parser import REQUIRED_SECTION_MARKERS, parse_cv_sections
from app.managed_cv.repository import ManagedCvRepository
from app.pipeline.cv_source import CvSourceError, PipelineCvSourceLoader
from app.profiles.repository import ManagedProfileRepository
from app.profiles.schema import ManagedProfileType
from app.settings.migrations import migrate_app_settings_database
from app.settings.session import create_settings_engine, create_settings_session_factory
from app.storage.app_dirs import AppDataPaths, build_app_data_paths


def _app_data_paths(tmp_path: Path) -> AppDataPaths:
    root = tmp_path / "app_data"
    root.mkdir()
    for child in ("profiles", "logs", "backups"):
        (root / child).mkdir()
    migrate_app_settings_database(root / "app.sqlite3")
    return build_app_data_paths(root)


def _settings_repositories(paths: AppDataPaths):  # type: ignore[no-untyped-def]
    engine = create_settings_engine(paths.database_file)
    session_factory = create_settings_session_factory(engine)
    return (
        ManagedProfileRepository(session_factory),
        ManagedCvRepository(session_factory),
    )


def _file_config(tmp_path: Path) -> tuple[ProjectConfig, Path]:
    base_config = load_profile_config()
    profile_dir = tmp_path / "example"
    profile_dir.mkdir(parents=True)
    shutil.copytree(Path("profiles/example/cv"), profile_dir / "cv")
    (profile_dir / "blacklist.example.txt").write_text(
        "BlockedCorp\n", encoding="utf-8"
    )
    config_data = base_config.model_dump()
    config_data["app"] = {"profile_name": "example", "data_dir": profile_dir}
    return ProjectConfig.model_validate(config_data), profile_dir


def _loader(
    tmp_path: Path, paths: AppDataPaths | None = None
) -> PipelineCvSourceLoader:
    config, _profile_dir = _file_config(tmp_path)
    return PipelineCvSourceLoader(
        config=config,
        profile_paths=build_profile_paths(config),
        app_data_paths=paths,
    )


def _active_profile(
    paths: AppDataPaths, profile_dir: Path, *, profile_id: str = "profile-1"
) -> tuple[str, ManagedCvRepository]:
    profile_repository, cv_repository = _settings_repositories(paths)
    profile_repository.create_profile(
        profile_id=profile_id,
        name="example",
        display_name="Example",
        profile_type=ManagedProfileType.FILE_BASED,
        data_dir=profile_dir,
        is_active=True,
    )
    return profile_id, cv_repository


def _managed_variant(
    cv_repository: ManagedCvRepository,
    profile_id: str,
    *,
    name: str = "backend_developer",
) -> str:
    variant = cv_repository.create_cv_variant(
        profile_id=profile_id,
        name=name,
        display_name="Backend Developer",
    )
    section_data = [
        (CvSectionName.PROJECTS, 30, "## Project\n\n- Built FastAPI tooling."),
        (CvSectionName.SUMMARY, 0, "Managed summary."),
        (CvSectionName.EXPERIENCE, 20, "## Example Company\n\n- Built services."),
        (CvSectionName.SKILLS, 10, "- FastAPI\n- Python"),
    ]
    for section_name, order, content in section_data:
        section = cv_repository.create_cv_section(
            variant_id=variant.id,
            section_key=section_name.value,
            title=section_name.value.title(),
            display_order=order,
            is_required=True,
        )
        cv_repository.create_cv_block(
            section_id=section.id,
            block_key="disabled",
            content_markdown="SHOULD NOT APPEAR",
            display_order=0,
            is_enabled=False,
        )
        cv_repository.create_cv_block(
            section_id=section.id,
            block_key="enabled",
            content_markdown=content,
            display_order=1,
            is_enabled=True,
        )
    return variant.id


def _managed_fact(
    cv_repository: ManagedCvRepository,
    profile_id: str,
    *,
    fact_key: str = "fact-fastapi",
    is_active: bool = True,
) -> str:
    fact = cv_repository.create_fact(
        profile_id=profile_id,
        fact_key=fact_key,
        category=FactCategory.SKILL,
        name="FastAPI",
        allowed_claim_level=AllowedClaimLevel.PRACTICAL,
        evidence="Built FastAPI services in verified projects.",
        is_active=is_active,
    )
    return fact.id


def test_managed_source_loads_cv_markdown_and_active_facts(tmp_path: Path) -> None:
    paths = _app_data_paths(tmp_path)
    config, profile_dir = _file_config(tmp_path)
    profile_id, cv_repository = _active_profile(paths, profile_dir)
    _managed_variant(cv_repository, profile_id)
    fact_id = _managed_fact(cv_repository, profile_id)
    _managed_fact(cv_repository, profile_id, fact_key="inactive", is_active=False)

    source = PipelineCvSourceLoader(
        config=config,
        profile_paths=build_profile_paths(config),
        app_data_paths=paths,
    ).load(selected_variant="backend_developer")

    assert source.metadata.source_type == "managed"
    assert source.loaded_cv.path.as_posix() == "managed_cv/backend_developer.md"
    assert "SHOULD NOT APPEAR" not in source.loaded_cv.markdown
    assert source.loaded_cv.markdown.index(
        "SUMMARY_START"
    ) < source.loaded_cv.markdown.index("SKILLS_START")
    assert source.loaded_cv.markdown.index(
        "SKILLS_START"
    ) < source.loaded_cv.markdown.index("EXPERIENCE_START")
    assert source.loaded_cv.markdown.index(
        "EXPERIENCE_START"
    ) < source.loaded_cv.markdown.index("PROJECTS_START")
    assert (
        parse_cv_sections(source.loaded_cv.markdown).keys()
        == REQUIRED_SECTION_MARKERS.keys()
    )
    assert [fact.id for fact in source.fact_bank.facts] == ["fact-fastapi"]
    assert source.fact_bank.facts[0].id != fact_id


def test_file_based_fallback_is_used_without_active_managed_profile(
    tmp_path: Path,
) -> None:
    source = _loader(tmp_path).load(selected_variant="backend_developer")

    assert source.metadata.source_type == "file_based"
    assert source.loaded_cv.path.name == "backend_developer.example.md"


def test_file_based_fallback_is_used_when_active_profile_has_no_managed_variants(
    tmp_path: Path,
) -> None:
    paths = _app_data_paths(tmp_path)
    config, profile_dir = _file_config(tmp_path)
    _active_profile(paths, profile_dir)

    source = PipelineCvSourceLoader(
        config=config,
        profile_paths=build_profile_paths(config),
        app_data_paths=paths,
    ).load(selected_variant="backend_developer")

    assert source.metadata.source_type == "file_based"


def test_selected_variant_missing_fails_when_managed_variants_exist(
    tmp_path: Path,
) -> None:
    paths = _app_data_paths(tmp_path)
    config, profile_dir = _file_config(tmp_path)
    profile_id, cv_repository = _active_profile(paths, profile_dir)
    _managed_variant(cv_repository, profile_id, name="other")
    _managed_fact(cv_repository, profile_id)

    with pytest.raises(CvSourceError, match="Selected managed CV variant"):
        PipelineCvSourceLoader(
            config=config,
            profile_paths=build_profile_paths(config),
            app_data_paths=paths,
        ).load(selected_variant="backend_developer")


def test_missing_required_managed_section_fails_clearly(tmp_path: Path) -> None:
    paths = _app_data_paths(tmp_path)
    config, profile_dir = _file_config(tmp_path)
    profile_id, cv_repository = _active_profile(paths, profile_dir)
    variant = cv_repository.create_cv_variant(
        profile_id=profile_id, name="backend_developer"
    )
    section = cv_repository.create_cv_section(
        variant_id=variant.id,
        section_key=CvSectionName.SUMMARY.value,
        title="Summary",
        display_order=0,
        is_required=True,
    )
    cv_repository.create_cv_block(
        section_id=section.id,
        block_key="summary",
        content_markdown="Summary.",
        display_order=0,
    )
    _managed_fact(cv_repository, profile_id)

    with pytest.raises(CvSourceError, match="missing required sections"):
        PipelineCvSourceLoader(
            config=config,
            profile_paths=build_profile_paths(config),
            app_data_paths=paths,
        ).load(selected_variant="backend_developer")


def test_no_active_managed_facts_fails_when_managed_source_selected(
    tmp_path: Path,
) -> None:
    paths = _app_data_paths(tmp_path)
    config, profile_dir = _file_config(tmp_path)
    profile_id, cv_repository = _active_profile(paths, profile_dir)
    _managed_variant(cv_repository, profile_id)
    _managed_fact(cv_repository, profile_id, is_active=False)

    with pytest.raises(CvSourceError, match="no active managed facts"):
        PipelineCvSourceLoader(
            config=config,
            profile_paths=build_profile_paths(config),
            app_data_paths=paths,
        ).load(selected_variant="backend_developer")


def test_block_link_to_inactive_fact_is_rejected(tmp_path: Path) -> None:
    paths = _app_data_paths(tmp_path)
    config, profile_dir = _file_config(tmp_path)
    profile_id, cv_repository = _active_profile(paths, profile_dir)
    variant_id = _managed_variant(cv_repository, profile_id)
    active_fact_id = _managed_fact(cv_repository, profile_id)
    inactive_fact_id = _managed_fact(
        cv_repository, profile_id, fact_key="inactive", is_active=False
    )
    first_section = cv_repository.list_cv_sections(variant_id)[0]
    first_block = cv_repository.list_cv_blocks(first_section.id)[1]
    cv_repository.link_block_to_fact(block_id=first_block.id, fact_id=active_fact_id)
    cv_repository.link_block_to_fact(block_id=first_block.id, fact_id=inactive_fact_id)

    with pytest.raises(CvSourceError, match="inactive fact"):
        PipelineCvSourceLoader(
            config=config,
            profile_paths=build_profile_paths(config),
            app_data_paths=paths,
        ).load(selected_variant="backend_developer")


def test_managed_source_does_not_call_file_based_cv_or_fact_loaders(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = _app_data_paths(tmp_path)
    config, profile_dir = _file_config(tmp_path)
    profile_id, cv_repository = _active_profile(paths, profile_dir)
    _managed_variant(cv_repository, profile_id)
    _managed_fact(cv_repository, profile_id)

    def fail_file_loader(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("file-based loader should not be called")

    monkeypatch.setattr("app.pipeline.cv_source.select_cv_variant", fail_file_loader)
    monkeypatch.setattr("app.pipeline.cv_source.load_markdown_file", fail_file_loader)
    monkeypatch.setattr("app.pipeline.cv_source.load_fact_bank", fail_file_loader)

    source = PipelineCvSourceLoader(
        config=config,
        profile_paths=build_profile_paths(config),
        app_data_paths=paths,
    ).load(selected_variant="backend_developer")

    assert source.metadata.source_type == "managed"


def test_managed_source_selects_active_variant_by_alias(tmp_path: Path) -> None:
    paths = _app_data_paths(tmp_path)
    config, profile_dir = _file_config(tmp_path)
    profile_id, cv_repository = _active_profile(paths, profile_dir)
    variant_id = _managed_variant(cv_repository, profile_id, name="managed_backend")
    cv_repository.add_variant_alias(variant_id=variant_id, alias="backend_developer")
    _managed_fact(cv_repository, profile_id)

    source = PipelineCvSourceLoader(
        config=config,
        profile_paths=build_profile_paths(config),
        app_data_paths=paths,
    ).load(selected_variant="backend_developer")

    assert source.metadata.source_type == "managed"
    assert source.metadata.variant_name == "managed_backend"


def test_active_managed_profile_name_mismatch_is_rejected(
    tmp_path: Path,
) -> None:
    paths = _app_data_paths(tmp_path)
    config, profile_dir = _file_config(tmp_path)
    profile_repository, cv_repository = _settings_repositories(paths)

    profile_repository.create_profile(
        profile_id="profile-other",
        name="other",
        display_name="Other",
        profile_type=ManagedProfileType.FILE_BASED,
        data_dir=profile_dir,
        is_active=True,
    )
    _managed_variant(cv_repository, "profile-other")
    _managed_fact(cv_repository, "profile-other")

    with pytest.raises(CvSourceError, match="active managed profile does not match"):
        PipelineCvSourceLoader(
            config=config,
            profile_paths=build_profile_paths(config),
            app_data_paths=paths,
        ).load(selected_variant="backend_developer")


def test_active_managed_profile_data_dir_mismatch_is_rejected(
    tmp_path: Path,
) -> None:
    paths = _app_data_paths(tmp_path)
    config, profile_dir = _file_config(tmp_path)
    other_profile_dir = tmp_path / "other-profile"
    other_profile_dir.mkdir()

    profile_repository, cv_repository = _settings_repositories(paths)
    profile_repository.create_profile(
        profile_id="profile-other-dir",
        name="example",
        display_name="Example with wrong dir",
        profile_type=ManagedProfileType.FILE_BASED,
        data_dir=other_profile_dir,
        is_active=True,
    )
    _managed_variant(cv_repository, "profile-other-dir")
    _managed_fact(cv_repository, "profile-other-dir")

    with pytest.raises(CvSourceError, match="active managed profile does not match"):
        PipelineCvSourceLoader(
            config=config,
            profile_paths=build_profile_paths(config),
            app_data_paths=paths,
        ).load(selected_variant="backend_developer")
