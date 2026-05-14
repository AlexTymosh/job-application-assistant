from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import ValidationError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import ProjectConfig, load_profile_config
from app.profiles.repository import ManagedProfileRepository
from app.settings.repository import AppSettingsRepository
from app.settings.schema import (
    ManagedAppSettings,
    StoredAppSetting,
    key_to_model_field,
    model_field_to_key,
)
from app.storage.app_dirs import AppDataPaths


class AppSettingsService:
    def __init__(self, repository: AppSettingsRepository) -> None:
        self._repository = repository

    def get_setting(self, key: str) -> Any | None:
        return self._repository.get_setting(key)

    def set_setting(self, key: str, value: Any) -> None:
        self._repository.set_setting(key, value)

    def delete_setting(self, key: str) -> None:
        self._repository.delete_setting(key)

    @property
    def session_factory(self) -> sessionmaker[Session]:
        return self._repository.session_factory

    def list_settings(self) -> list[StoredAppSetting]:
        return self._repository.list_settings()

    def get_managed_settings(self) -> ManagedAppSettings:
        values: dict[str, Any] = {}
        for setting in self._repository.list_settings():
            values[key_to_model_field(setting.key)] = setting.value
        return ManagedAppSettings.model_validate(values)

    def save_managed_settings(self, settings: ManagedAppSettings) -> None:
        for field_name, value in settings.model_dump(exclude_none=True).items():
            self._repository.set_setting(model_field_to_key(field_name), value)

    def load_effective_config(self) -> ProjectConfig:
        managed_settings = self.get_managed_settings()
        active_profile = ManagedProfileRepository(
            self.session_factory
        ).get_active_profile()
        if active_profile is not None:
            base_config = load_profile_config(
                _config_path_for_profile(
                    profile_name=active_profile.name,
                    profile_data_dir=active_profile.data_dir,
                )
            )
        else:
            base_config = _load_base_config(managed_settings)
        return overlay_project_config(base_config, managed_settings)


def build_app_settings_service(
    session_factory: sessionmaker[Session],
) -> AppSettingsService:
    return AppSettingsService(AppSettingsRepository(session_factory))


def load_effective_project_config(app_data_paths: AppDataPaths) -> ProjectConfig:
    from app.settings.init import initialise_app_settings_storage

    service = initialise_app_settings_storage(app_data_paths)
    return service.load_effective_config()


def overlay_project_config(
    base_config: ProjectConfig,
    managed_settings: ManagedAppSettings,
) -> ProjectConfig:
    config_data = base_config.model_dump(mode="json")
    if managed_settings.llm_extraction_mode is not None:
        llm_data = dict(config_data["llm"])
        llm_data["extraction_mode"] = managed_settings.llm_extraction_mode.value
        config_data["llm"] = llm_data
    if managed_settings.require_human_approval_before_export is not None:
        workflow_data = dict(config_data["workflow"])
        workflow_data["require_human_approval_before_export"] = (
            managed_settings.require_human_approval_before_export
        )
        config_data["workflow"] = workflow_data

    exports_data = dict(config_data["exports"])
    if managed_settings.export_markdown is not None:
        exports_data["markdown"] = managed_settings.export_markdown
    if managed_settings.export_html is not None:
        exports_data["html"] = managed_settings.export_html
    if managed_settings.export_pdf is not None:
        exports_data["pdf"] = managed_settings.export_pdf
    if managed_settings.export_docx is not None:
        exports_data["docx"] = managed_settings.export_docx
    config_data["exports"] = exports_data

    return ProjectConfig.model_validate(config_data)


def _load_base_config(managed_settings: ManagedAppSettings) -> ProjectConfig:
    if (
        managed_settings.default_profile_name is not None
        and managed_settings.default_profile_data_dir is not None
    ):
        return load_profile_config(
            _config_path_for_profile(
                profile_name=managed_settings.default_profile_name,
                profile_data_dir=managed_settings.default_profile_data_dir,
            )
        )
    return load_profile_config()


def _config_path_for_profile(*, profile_name: str, profile_data_dir: Path) -> Path:
    filename = "config.example.yaml" if profile_name == "example" else "config.yaml"
    return profile_data_dir / filename


def validate_managed_settings_readable(service: AppSettingsService) -> None:
    try:
        service.get_managed_settings()
    except (ValueError, ValidationError) as exc:
        raise ValueError(f"Managed app settings are invalid: {exc}") from exc
