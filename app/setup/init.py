from __future__ import annotations

import sqlite3
from dataclasses import dataclass

import yaml
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import ProjectConfig
from app.core.paths import ProfilePaths, build_profile_paths
from app.secrets.openai_key import OpenAISecretService
from app.settings.service import load_effective_project_config
from app.setup.checks import SetupStatus
from app.setup.service import SetupStatusService
from app.storage.app_dirs import AppDataPaths

_EXPECTED_CONFIG_EXCEPTIONS = (
    FileNotFoundError,
    ValueError,
    ValidationError,
    OSError,
    sqlite3.DatabaseError,
    SQLAlchemyError,
    yaml.YAMLError,
)


@dataclass(frozen=True)
class SetupInitialisation:
    status: SetupStatus
    config: ProjectConfig | None
    profile_paths: ProfilePaths | None


def initialise_setup_state(
    *,
    app_data_paths: AppDataPaths,
    config: ProjectConfig | None = None,
    openai_secret_service: OpenAISecretService | None = None,
) -> SetupInitialisation:
    service = SetupStatusService(
        app_data_paths=app_data_paths,
        openai_secret_service=openai_secret_service,
    )
    status = service.build_status(config=config)
    resolved_config = _load_available_config(config, app_data_paths=app_data_paths)
    profile_paths = _build_available_profile_paths(resolved_config)

    return SetupInitialisation(
        status=status,
        config=resolved_config,
        profile_paths=profile_paths,
    )


def _load_available_config(
    config: ProjectConfig | None,
    *,
    app_data_paths: AppDataPaths,
) -> ProjectConfig | None:
    if config is not None:
        return config

    try:
        return load_effective_project_config(app_data_paths)
    except _EXPECTED_CONFIG_EXCEPTIONS:
        return None


def _build_available_profile_paths(config: ProjectConfig | None) -> ProfilePaths | None:
    if config is None:
        return None

    try:
        profile_paths = build_profile_paths(config)
    except _EXPECTED_CONFIG_EXCEPTIONS:
        return None

    if not profile_paths.profile_dir.is_dir():
        return None

    return profile_paths
