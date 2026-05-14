from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path

import pytest

from app.core.config import LlmExtractionMode, validate_llm_runtime_config
from app.settings.init import initialise_app_settings_storage
from app.settings.schema import (
    SETTING_DEFAULT_PROFILE_DATA_DIR,
    SETTING_DEFAULT_PROFILE_NAME,
    SETTING_EXPORT_DOCX,
    SETTING_EXPORT_HTML,
    SETTING_EXPORT_MARKDOWN,
    SETTING_EXPORT_PDF,
    SETTING_LLM_EXTRACTION_MODE,
    SETTING_REQUIRE_HUMAN_APPROVAL,
)
from app.settings.service import load_effective_project_config
from app.setup.service import SetupStatusService
from app.storage.app_dirs import build_app_data_paths


def copy_example_profile(tmp_path: Path) -> Path:
    profile_dir = tmp_path / "example"
    shutil.copytree(Path("profiles/example"), profile_dir)
    config_path = profile_dir / "config.example.yaml"
    content = config_path.read_text(encoding="utf-8")
    content = content.replace(
        'data_dir: "profiles/example"', f'data_dir: "{profile_dir}"'
    )
    config_path.write_text(content, encoding="utf-8")
    return profile_dir


def test_managed_runtime_settings_override_yaml_defaults(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile_dir = copy_example_profile(tmp_path)
    paths = build_app_data_paths(tmp_path / "app-data")
    service = initialise_app_settings_storage(paths)
    monkeypatch.setenv("PROFILE_NAME", "example")
    monkeypatch.setenv("PROFILE_DATA_DIR", str(profile_dir))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    service.set_setting(SETTING_LLM_EXTRACTION_MODE, "openai")
    service.set_setting(SETTING_REQUIRE_HUMAN_APPROVAL, False)
    service.set_setting(SETTING_EXPORT_MARKDOWN, False)
    service.set_setting(SETTING_EXPORT_HTML, False)
    service.set_setting(SETTING_EXPORT_PDF, False)
    service.set_setting(SETTING_EXPORT_DOCX, False)

    config = load_effective_project_config(paths)

    assert config.llm.extraction_mode is LlmExtractionMode.OPENAI
    assert config.workflow.require_human_approval_before_export is False
    assert config.exports.markdown is False
    assert config.exports.html is False
    assert config.exports.pdf is False
    assert config.exports.docx is False


def test_missing_managed_settings_preserve_yaml_defaults(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile_dir = copy_example_profile(tmp_path)
    paths = build_app_data_paths(tmp_path / "app-data")
    initialise_app_settings_storage(paths)
    monkeypatch.setenv("PROFILE_NAME", "example")
    monkeypatch.setenv("PROFILE_DATA_DIR", str(profile_dir))

    config = load_effective_project_config(paths)

    assert config.llm.extraction_mode is LlmExtractionMode.FAKE
    assert config.workflow.require_human_approval_before_export is True
    assert config.exports.markdown is True


def test_profile_selection_overlay_locates_file_based_profile_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile_dir = copy_example_profile(tmp_path)
    paths = build_app_data_paths(tmp_path / "app-data")
    service = initialise_app_settings_storage(paths)
    monkeypatch.setenv("PROFILE_NAME", "missing")
    monkeypatch.setenv("PROFILE_DATA_DIR", str(tmp_path / "missing"))
    service.set_setting(SETTING_DEFAULT_PROFILE_NAME, "example")
    service.set_setting(SETTING_DEFAULT_PROFILE_DATA_DIR, profile_dir)

    config = load_effective_project_config(paths)

    assert Path(config.app.data_dir) == profile_dir


def test_invalid_stored_managed_setting_fails_setup_check(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile_dir = copy_example_profile(tmp_path)
    paths = build_app_data_paths(tmp_path / "app-data")
    initialise_app_settings_storage(paths)
    monkeypatch.setenv("PROFILE_NAME", "example")
    monkeypatch.setenv("PROFILE_DATA_DIR", str(profile_dir))
    with sqlite3.connect(paths.database_file) as connection:
        connection.execute(
            "INSERT INTO app_settings (key, value_json) VALUES (?, ?)",
            (SETTING_EXPORT_HTML, '"not-a-boolean"'),
        )

    status = SetupStatusService(app_data_paths=paths).build_status()

    check = next(
        check for check in status.checks if check.code == "app_settings_database"
    )
    assert check.ok is False
    assert "must be a boolean" in check.message


def test_fake_mode_still_works_without_openai_api_key(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile_dir = copy_example_profile(tmp_path)
    paths = build_app_data_paths(tmp_path / "app-data")
    initialise_app_settings_storage(paths)
    monkeypatch.setenv("PROFILE_NAME", "example")
    monkeypatch.setenv("PROFILE_DATA_DIR", str(profile_dir))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    config = load_effective_project_config(paths)

    validate_llm_runtime_config(config)


def test_openai_mode_from_managed_settings_requires_runtime_credentials(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile_dir = copy_example_profile(tmp_path)
    paths = build_app_data_paths(tmp_path / "app-data")
    service = initialise_app_settings_storage(paths)
    service.set_setting(SETTING_LLM_EXTRACTION_MODE, "openai")
    monkeypatch.setenv("PROFILE_NAME", "example")
    monkeypatch.setenv("PROFILE_DATA_DIR", str(profile_dir))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    status = SetupStatusService(app_data_paths=paths).build_status()

    check = next(check for check in status.checks if check.code == "llm_mode")
    assert check.ok is False
    assert "OpenAI extraction mode requires" in check.message
