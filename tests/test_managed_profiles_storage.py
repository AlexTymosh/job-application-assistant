from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from app.profiles.service import ManagedProfileError, build_managed_profile_service
from app.settings.init import initialise_app_settings_storage
from app.settings.migrations import CURRENT_APP_SETTINGS_SCHEMA_VERSION
from app.setup.service import SetupStatusService
from app.storage.app_dirs import build_app_data_paths
from app.storage.bootstrap import bootstrap_app_data_dirs_for_paths

ROOT = Path(__file__).resolve().parents[1]


def _rewrite_profile_config(
    path: Path,
    *,
    name: str = "alex",
    config_profile_name: str | None = None,
    config_data_dir: Path | None = None,
) -> None:
    config_name = "config.example.yaml" if name == "example" else "config.yaml"
    config_profile_name = config_profile_name or name
    config_data_dir = config_data_dir or path

    (path / config_name).write_text(
        f"""
app:
  profile_name: {config_profile_name}
  data_dir: {config_data_dir.as_posix()}
workflow: {{}}
llm:
  extraction_mode: fake
cv:
  default_variant: backend_developer
  variants:
    - backend_developer
exports: {{}}
guardrails: {{}}
job_reader: {{}}
future_integrations: {{}}
""".strip()
        + "\n",
        encoding="utf-8",
    )


def _write_profile(
    path: Path,
    *,
    name: str = "alex",
    marker: str = "Alex",
    config_profile_name: str | None = None,
    config_data_dir: Path | None = None,
) -> None:
    (path / "cv" / "variants").mkdir(parents=True, exist_ok=True)

    fact_name = "fact_bank.example.yaml" if name == "example" else "fact_bank.yaml"
    variant_name = (
        "backend_developer.example.md" if name == "example" else "backend_developer.md"
    )

    _rewrite_profile_config(
        path,
        name=name,
        config_profile_name=config_profile_name,
        config_data_dir=config_data_dir,
    )

    (path / "cv" / fact_name).write_text(
        """
facts:
  - id: fact-1
    category: skill
    name: Backend services
    allowed_claim_level: practical
    evidence: Example evidence.
""".lstrip(),
        encoding="utf-8",
    )

    cv_content = (
        f"# {marker} — Backend Developer CV Variant\n\n"
        "<!-- SECTION: SUMMARY_START -->\n"
        "Backend-focused software developer with practical experience in Python.\n"
        "<!-- SECTION: SUMMARY_END -->\n\n"
        "<!-- SECTION: SKILLS_START -->\n"
        "- Python\n- FastAPI\n"
        "<!-- SECTION: SKILLS_END -->\n\n"
        "<!-- SECTION: EXPERIENCE_START -->\n"
        "## Example Company — Operations Analyst\n\n"
        "- Built small Python automation scripts.\n"
        "<!-- SECTION: EXPERIENCE_END -->\n\n"
        "<!-- SECTION: PROJECTS_START -->\n"
        "## Local FastAPI Portfolio Project\n\n"
        "- Built a local backend application using FastAPI.\n"
        "<!-- SECTION: PROJECTS_END -->\n"
    )

    (path / "cv" / "variants" / variant_name).write_text(
        cv_content,
        encoding="utf-8",
    )


def _service(tmp_path: Path):  # type: ignore[no-untyped-def]
    paths = build_app_data_paths(tmp_path / "JobApplicationAssistant")
    app_settings = initialise_app_settings_storage(paths)
    return (
        build_managed_profile_service(
            app_settings.session_factory,
            app_settings_service=app_settings,
        ),
        app_settings,
        paths,
    )


def _check_by_code(status, code: str):  # type: ignore[no-untyped-def]
    return next(check for check in status.checks if check.code == code)


def test_profile_table_schema_migrates_from_v1_to_v2(tmp_path: Path) -> None:
    database_file = tmp_path / "app.sqlite3"
    with sqlite3.connect(database_file) as connection:
        connection.execute(
            """
            CREATE TABLE app_settings_schema (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute("INSERT INTO app_settings_schema (version) VALUES (1)")
        connection.execute(
            """
            CREATE TABLE app_settings (
                key TEXT PRIMARY KEY,
                value_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

    initialise_app_settings_storage(build_app_data_paths(tmp_path))

    with sqlite3.connect(database_file) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        version = connection.execute(
            "SELECT MAX(version) FROM app_settings_schema"
        ).fetchone()[0]

    assert "profiles" in tables
    assert version == CURRENT_APP_SETTINGS_SCHEMA_VERSION == 3


def test_create_list_duplicate_and_active_profiles(tmp_path: Path) -> None:
    service, _, _ = _service(tmp_path)
    profile_dir = tmp_path / "private" / "alex"
    _write_profile(profile_dir)

    profile = service.create_file_based_profile(
        name=" Alex ",
        display_name="Alex Profile",
        data_dir=profile_dir,
        make_active=True,
    )

    assert profile.name == "alex"
    assert profile.is_active is True
    assert service.list_profiles() == [profile]
    assert service.get_active_profile() == profile

    with pytest.raises(ManagedProfileError, match="already exists"):
        service.create_file_based_profile(
            name="alex",
            display_name=None,
            data_dir=profile_dir,
        )


def test_profile_name_must_match_profile_config(tmp_path: Path) -> None:
    service, _, _ = _service(tmp_path)
    profile_dir = tmp_path / "private" / "sam"
    _write_profile(profile_dir, name="sam", config_profile_name="alex")

    with pytest.raises(ManagedProfileError, match="app.profile_name"):
        service.create_file_based_profile(
            name="sam",
            display_name=None,
            data_dir=profile_dir,
        )


def test_profile_data_dir_must_match_profile_config(tmp_path: Path) -> None:
    service, _, _ = _service(tmp_path)
    profile_dir = tmp_path / "private" / "sam"
    configured_dir = tmp_path / "private" / "other"
    _write_profile(profile_dir, name="sam", config_data_dir=configured_dir)

    with pytest.raises(ManagedProfileError, match="app.data_dir"):
        service.create_file_based_profile(
            name="sam",
            display_name=None,
            data_dir=profile_dir,
        )


def test_matching_profile_identity_connects_successfully(tmp_path: Path) -> None:
    service, _, _ = _service(tmp_path)
    profile_dir = tmp_path / "private" / "sam"
    _write_profile(profile_dir, name="sam")

    profile = service.create_file_based_profile(
        name="sam",
        display_name=None,
        data_dir=profile_dir,
    )

    assert profile.name == "sam"
    assert profile.data_dir == profile_dir


def test_invalid_and_repository_internal_profile_folders_are_rejected(
    tmp_path: Path,
) -> None:
    service, _, _ = _service(tmp_path)

    with pytest.raises(ManagedProfileError, match="must exist"):
        service.create_file_based_profile(
            name="alex",
            display_name=None,
            data_dir=tmp_path / "missing",
        )

    with pytest.raises(ManagedProfileError, match="outside this repository"):
        service.create_file_based_profile(
            name="example",
            display_name=None,
            data_dir=ROOT / "profiles" / "example",
        )


def test_only_one_active_profile_exists(tmp_path: Path) -> None:
    service, _, _ = _service(tmp_path)
    alex_dir = tmp_path / "private" / "alex"
    sam_dir = tmp_path / "private" / "sam"
    _write_profile(alex_dir, name="alex", marker="Alex")
    _write_profile(sam_dir, name="sam", marker="Sam")

    alex = service.create_file_based_profile(
        name="alex",
        display_name=None,
        data_dir=alex_dir,
        make_active=True,
    )
    sam = service.create_file_based_profile(
        name="sam",
        display_name=None,
        data_dir=sam_dir,
    )

    active = service.set_active_profile(sam.id)
    profiles = service.list_profiles()

    assert active.name == "sam"
    assert [profile.name for profile in profiles if profile.is_active] == ["sam"]
    assert alex.id != sam.id


def test_active_managed_profile_drives_effective_config_loading(
    tmp_path: Path,
) -> None:
    service, app_settings, _ = _service(tmp_path)
    profile_dir = tmp_path / "private" / "sam"
    _write_profile(profile_dir, name="sam", marker="Sam")

    service.create_file_based_profile(
        name="sam",
        display_name=None,
        data_dir=profile_dir,
        make_active=True,
    )

    config = app_settings.load_effective_config()

    assert config.app.profile_name == "sam"
    assert config.app.data_dir == profile_dir


def test_no_managed_profile_preserves_file_based_fallback(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _, app_settings, _ = _service(tmp_path)
    profile_dir = tmp_path / "private" / "alex"
    _write_profile(profile_dir, name="alex")
    monkeypatch.setenv("PROFILE_NAME", "alex")
    monkeypatch.setenv("PROFILE_DATA_DIR", str(profile_dir))

    config = app_settings.load_effective_config()

    assert config.app.profile_name == "alex"
    assert config.app.data_dir == profile_dir


def test_profile_management_does_not_create_private_profile_files(
    tmp_path: Path,
) -> None:
    service, _, paths = _service(tmp_path)
    profile_dir = tmp_path / "private" / "alex"
    _write_profile(profile_dir)

    service.create_file_based_profile(
        name="alex",
        display_name=None,
        data_dir=profile_dir,
        make_active=True,
    )

    assert not paths.profiles_dir.exists() or list(paths.profiles_dir.iterdir()) == []
    assert not (paths.root / "applications.sqlite3").exists()
    assert not (profile_dir / "applications.sqlite3").exists()


def test_active_profile_config_name_mismatch_fails_effective_config_and_setup(
    tmp_path: Path,
) -> None:
    service, app_settings, paths = _service(tmp_path)
    bootstrap_app_data_dirs_for_paths(paths)

    profile_dir = tmp_path / "private" / "sam"
    _write_profile(profile_dir, name="sam")

    service.create_file_based_profile(
        name="sam",
        display_name=None,
        data_dir=profile_dir,
        make_active=True,
    )

    _rewrite_profile_config(
        profile_dir,
        name="sam",
        config_profile_name="alex",
    )

    with pytest.raises(ValueError, match="app.profile_name"):
        app_settings.load_effective_config()

    status = SetupStatusService(app_data_paths=paths).build_status()
    profile_config_check = _check_by_code(status, "profile_config")

    assert status.is_complete is False
    assert profile_config_check.ok is False
    assert "app.profile_name" in profile_config_check.message


def test_active_profile_config_data_dir_mismatch_fails_effective_config_and_setup(
    tmp_path: Path,
) -> None:
    service, app_settings, paths = _service(tmp_path)
    bootstrap_app_data_dirs_for_paths(paths)

    profile_dir = tmp_path / "private" / "sam"
    other_dir = tmp_path / "private" / "other"
    _write_profile(profile_dir, name="sam")

    service.create_file_based_profile(
        name="sam",
        display_name=None,
        data_dir=profile_dir,
        make_active=True,
    )

    _rewrite_profile_config(
        profile_dir,
        name="sam",
        config_data_dir=other_dir,
    )

    with pytest.raises(ValueError, match="app.data_dir"):
        app_settings.load_effective_config()

    status = SetupStatusService(app_data_paths=paths).build_status()
    profile_config_check = _check_by_code(status, "profile_config")

    assert status.is_complete is False
    assert profile_config_check.ok is False
    assert "app.data_dir" in profile_config_check.message
