from __future__ import annotations

import re
import sqlite3
import uuid
from pathlib import Path

import yaml
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_project_root, load_profile_config
from app.core.paths import build_profile_paths
from app.profiles.repository import (
    DuplicateProfileNameError,
    ManagedProfileRepository,
)
from app.profiles.schema import (
    ManagedProfileRecord,
    ManagedProfileType,
    ProfileValidationResult,
)
from app.settings.schema import (
    SETTING_DEFAULT_PROFILE_DATA_DIR,
    SETTING_DEFAULT_PROFILE_NAME,
)
from app.settings.service import AppSettingsService
from app.storage.location import normalise_app_data_root

_PROFILE_NAME_PATTERN = re.compile(r"[^a-z0-9_.-]+")
_EXPECTED_PROFILE_CONFIG_EXCEPTIONS = (
    FileNotFoundError,
    ValueError,
    ValidationError,
    OSError,
    sqlite3.DatabaseError,
    SQLAlchemyError,
    yaml.YAMLError,
)


class ManagedProfileError(ValueError):
    pass


class ManagedProfileService:
    def __init__(
        self,
        repository: ManagedProfileRepository,
        *,
        app_settings_service: AppSettingsService | None = None,
    ) -> None:
        self._repository = repository
        self._app_settings_service = app_settings_service

    def create_file_based_profile(
        self,
        *,
        name: str,
        display_name: str | None,
        data_dir: str | Path,
        make_active: bool = False,
    ) -> ManagedProfileRecord:
        normalised_name = normalise_profile_name(name)
        normalised_display_name = _normalise_optional_text(display_name)
        profile_dir = normalise_app_data_root(data_dir)
        self.validate_file_based_profile_folder(
            profile_name=normalised_name,
            data_dir=profile_dir,
        )
        existing_profiles = self._repository.list_profiles()
        should_make_active = make_active or not existing_profiles
        try:
            record = self._repository.create_profile(
                profile_id=str(uuid.uuid4()),
                name=normalised_name,
                display_name=normalised_display_name,
                profile_type=ManagedProfileType.FILE_BASED,
                data_dir=profile_dir,
                is_active=should_make_active,
            )
        except DuplicateProfileNameError as exc:
            raise ManagedProfileError(str(exc)) from exc
        if record.is_active:
            self._sync_default_profile_bridge(record)
        return record

    def list_profiles(self) -> list[ManagedProfileRecord]:
        return self._repository.list_profiles()

    def get_active_profile(self) -> ManagedProfileRecord | None:
        return self._repository.get_active_profile()

    def set_active_profile(self, profile_id: str) -> ManagedProfileRecord:
        record = self._repository.get_profile(profile_id)
        if record is None:
            raise ManagedProfileError("Managed profile was not found.")
        self.validate_file_based_profile_folder(
            profile_name=record.name,
            data_dir=record.data_dir,
        )
        active_record = self._repository.set_active_profile(profile_id)
        self._sync_default_profile_bridge(active_record)
        return active_record

    def validate_profile(self, record: ManagedProfileRecord) -> ProfileValidationResult:
        try:
            self.validate_file_based_profile_folder(
                profile_name=record.name,
                data_dir=record.data_dir,
            )
        except ManagedProfileError as exc:
            return ProfileValidationResult(ok=False, message=str(exc))
        return ProfileValidationResult(ok=True, message="Profile folder is valid.")

    def validate_file_based_profile_folder(
        self,
        *,
        profile_name: str,
        data_dir: Path,
    ) -> None:
        repo_root = get_project_root().resolve()
        resolved_dir = normalise_app_data_root(data_dir)
        if resolved_dir == repo_root or resolved_dir.is_relative_to(repo_root):
            raise ManagedProfileError(
                "Choose a profile folder outside this repository so private data is "
                "not committed."
            )
        if not resolved_dir.exists() or not resolved_dir.is_dir():
            raise ManagedProfileError(
                "Profile data folder must exist and be a directory."
            )

        config_file = resolved_dir / _config_filename(profile_name)
        cv_dir = resolved_dir / "cv"
        variants_dir = cv_dir / "variants"
        fact_bank = cv_dir / _fact_bank_filename(profile_name)
        missing = [
            path.name
            if path.parent == resolved_dir
            else path.relative_to(resolved_dir).as_posix()
            for path in (config_file, cv_dir, variants_dir, fact_bank)
            if not path.exists()
        ]
        if missing:
            raise ManagedProfileError(
                "Profile folder is missing required file-based profile paths: "
                + ", ".join(missing)
            )

        try:
            config = load_profile_config(config_file)
            config_profile_dir = normalise_app_data_root(
                build_profile_paths(config).profile_dir
            )
        except _EXPECTED_PROFILE_CONFIG_EXCEPTIONS as exc:
            raise ManagedProfileError(f"Profile config is not readable: {exc}") from exc

        config_profile_name = normalise_profile_name(config.app.profile_name)
        if config_profile_name != profile_name:
            raise ManagedProfileError(
                "Profile config app.profile_name must match the managed profile "
                f"name: expected {profile_name!r}, found {config.app.profile_name!r}."
            )
        if config_profile_dir != resolved_dir:
            raise ManagedProfileError(
                "Profile config app.data_dir must resolve to the selected profile "
                f"folder: expected {resolved_dir}, found {config_profile_dir}."
            )

    def _sync_default_profile_bridge(self, record: ManagedProfileRecord) -> None:
        if self._app_settings_service is None:
            return
        self._app_settings_service.set_setting(
            SETTING_DEFAULT_PROFILE_NAME, record.name
        )
        self._app_settings_service.set_setting(
            SETTING_DEFAULT_PROFILE_DATA_DIR,
            record.data_dir,
        )


def build_managed_profile_service(
    session_factory: sessionmaker[Session],
    *,
    app_settings_service: AppSettingsService | None = None,
) -> ManagedProfileService:
    return ManagedProfileService(
        ManagedProfileRepository(session_factory),
        app_settings_service=app_settings_service,
    )


def normalise_profile_name(name: str) -> str:
    stripped = name.strip().lower()
    if not stripped:
        raise ManagedProfileError("Profile name must not be blank.")
    normalised = _PROFILE_NAME_PATTERN.sub("-", stripped).strip("-._")
    if not normalised:
        raise ManagedProfileError("Profile name must include letters or numbers.")
    return normalised


def _normalise_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _config_filename(profile_name: str) -> str:
    return "config.example.yaml" if profile_name == "example" else "config.yaml"


def _fact_bank_filename(profile_name: str) -> str:
    return "fact_bank.example.yaml" if profile_name == "example" else "fact_bank.yaml"
