from __future__ import annotations

import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import yaml
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import (
    ProjectConfig,
    get_default_config_path,
    validate_llm_runtime_config,
)
from app.core.paths import ProfilePaths, build_profile_paths
from app.cv.fact_bank import load_fact_bank
from app.cv.selector import select_default_cv_variant

# Import models so SQLAlchemy metadata is populated for readiness checks.
from app.db import models  # noqa: F401
from app.db.base import Base
from app.secrets.openai_key import (
    OpenAISecretService,
    SecretStorageError,
    get_environment_openai_api_key,
)
from app.settings.init import initialise_app_settings_storage
from app.settings.migrations import is_app_settings_schema_current
from app.settings.service import load_effective_project_config
from app.setup.checks import SetupCheck, SetupStatus
from app.storage.app_dirs import AppDataPaths

_EXPECTED_SETUP_EXCEPTIONS = (
    FileNotFoundError,
    ValueError,
    ValidationError,
    OSError,
    sqlite3.DatabaseError,
    SQLAlchemyError,
    yaml.YAMLError,
)


class SetupStatusService:
    """Evaluate local setup readiness without creating private profile data."""

    def __init__(
        self,
        *,
        app_data_paths: AppDataPaths,
        openai_secret_service: OpenAISecretService | None = None,
    ) -> None:
        self._app_data_paths = app_data_paths
        self._openai_secret_service = openai_secret_service

    def build_status(
        self,
        *,
        config: ProjectConfig | None = None,
    ) -> SetupStatus:
        checks: list[SetupCheck] = []
        checks.extend(self._check_app_data_dirs())
        checks.append(self._check_app_settings_database())

        loaded_config: ProjectConfig | None = config
        config_check, loaded_config = self._check_profile_config(config=loaded_config)
        checks.append(config_check)

        profile_paths: ProfilePaths | None = None
        if loaded_config is not None:
            profile_check, profile_paths = self._check_active_profile(loaded_config)
            checks.append(profile_check)
            checks.append(self._check_sqlite_database(profile_paths))
            checks.append(self._check_llm_mode(loaded_config))
            checks.append(self._check_cv_source(loaded_config, profile_paths))
            checks.append(self._check_fact_bank(profile_paths))
        else:
            checks.extend(
                [
                    _failed_dependency_check(
                        code="active_profile",
                        label="Active file-based profile",
                        dependency="profile config",
                    ),
                    _failed_dependency_check(
                        code="sqlite_database",
                        label="SQLite database",
                        dependency="profile config",
                    ),
                    _failed_dependency_check(
                        code="llm_mode",
                        label="LLM mode",
                        dependency="profile config",
                    ),
                    _failed_dependency_check(
                        code="cv_source",
                        label="CV source",
                        dependency="profile config",
                    ),
                    _failed_dependency_check(
                        code="fact_bank",
                        label="Fact bank",
                        dependency="profile config",
                    ),
                ]
            )

        return SetupStatus(checks=checks)

    def load_valid_config_and_paths(
        self,
        *,
        config: ProjectConfig | None = None,
    ) -> tuple[ProjectConfig, ProfilePaths] | None:
        status = self.build_status(config=config)
        if not status.is_complete:
            return None

        resolved_config = (
            config
            if config is not None
            else load_effective_project_config(self._app_data_paths)
        )
        return resolved_config, build_profile_paths(resolved_config)

    def _check_app_data_dirs(self) -> list[SetupCheck]:
        return [
            self._path_check(
                code="app_data_root",
                label="App data root",
                path=self._app_data_paths.root,
            ),
            self._path_check(
                code="app_data_profiles_dir",
                label="App data profiles directory",
                path=self._app_data_paths.profiles_dir,
            ),
            self._path_check(
                code="app_data_logs_dir",
                label="App data logs directory",
                path=self._app_data_paths.logs_dir,
            ),
            self._path_check(
                code="app_data_backups_dir",
                label="App data backups directory",
                path=self._app_data_paths.backups_dir,
            ),
        ]

    def _path_check(self, *, code: str, label: str, path: Path) -> SetupCheck:
        if path.is_dir():
            return SetupCheck(
                code=code,
                label=label,
                ok=True,
                message="Directory exists.",
            )

        return SetupCheck(
            code=code,
            label=label,
            ok=False,
            message="Required directory is missing.",
            action_hint="Restart the app so the approved app data bootstrap can run.",
        )

    def _check_app_settings_database(self) -> SetupCheck:
        ok, message = is_app_settings_schema_current(self._app_data_paths.database_file)
        if not ok:
            return SetupCheck(
                code="app_settings_database",
                label="App settings database",
                ok=False,
                message=message,
                action_hint=(
                    "Restart the app so app settings storage can be initialised."
                ),
            )

        try:
            service = initialise_app_settings_storage(self._app_data_paths)
            service.get_managed_settings()
        except _EXPECTED_SETUP_EXCEPTIONS as exc:
            return SetupCheck(
                code="app_settings_database",
                label="App settings database",
                ok=False,
                message=str(exc),
                action_hint="Fix or reset app.sqlite3 in the app data folder.",
            )

        return SetupCheck(
            code="app_settings_database",
            label="App settings database",
            ok=True,
            message=message,
        )

    def _check_profile_config(
        self,
        *,
        config: ProjectConfig | None,
    ) -> tuple[SetupCheck, ProjectConfig | None]:
        if config is not None:
            return (
                SetupCheck(
                    code="profile_config",
                    label="Profile config",
                    ok=True,
                    message="Project config was provided explicitly.",
                ),
                config,
            )

        config_path = get_default_config_path()
        return _check_expected(
            code="profile_config",
            label="Profile config",
            action=lambda: load_effective_project_config(self._app_data_paths),
            success_message=f"Loaded profile config from {config_path.name}.",
            failure_hint=(
                "Create or connect a file-based profile config, then set "
                "PROFILE_NAME and PROFILE_DATA_DIR if needed."
            ),
        )

    def _check_active_profile(
        self, config: ProjectConfig
    ) -> tuple[SetupCheck, ProfilePaths | None]:
        try:
            profile_paths = build_profile_paths(config)
            if not profile_paths.profile_dir.is_dir():
                raise FileNotFoundError(
                    f"Profile directory not found: {profile_paths.profile_dir}"
                )
            if not profile_paths.cv_dir.is_dir():
                raise FileNotFoundError(
                    f"CV directory not found: {profile_paths.cv_dir}"
                )
            if not profile_paths.variants_dir.is_dir():
                raise FileNotFoundError(
                    f"CV variants directory not found: {profile_paths.variants_dir}"
                )
        except _EXPECTED_SETUP_EXCEPTIONS as exc:
            return (
                SetupCheck(
                    code="active_profile",
                    label="Active file-based profile",
                    ok=False,
                    message=str(exc),
                    action_hint=(
                        "Check PROFILE_DATA_DIR and the profile folder structure."
                    ),
                ),
                None,
            )

        return (
            SetupCheck(
                code="active_profile",
                label="Active file-based profile",
                ok=True,
                message="Profile directory and CV folders exist.",
            ),
            profile_paths,
        )

    def _check_sqlite_database(self, profile_paths: ProfilePaths | None) -> SetupCheck:
        if profile_paths is None:
            return _failed_dependency_check(
                code="sqlite_database",
                label="SQLite database",
                dependency="active profile",
            )

        database_file = profile_paths.database_file
        if not database_file.is_file():
            return SetupCheck(
                code="sqlite_database",
                label="SQLite database",
                ok=False,
                message="Profile database file is missing.",
                action_hint="Run alembic upgrade head for the selected profile.",
            )

        try:
            table_names = _read_sqlite_table_names(database_file)
            missing_tables = sorted(set(Base.metadata.tables) - table_names)
            if missing_tables:
                raise ValueError(
                    "Database is missing expected tables: " + ", ".join(missing_tables)
                )
            missing_columns = _read_missing_sqlite_columns(database_file)
            if missing_columns:
                raise ValueError(
                    "Database tables are missing expected columns: "
                    + ", ".join(missing_columns)
                )
        except _EXPECTED_SETUP_EXCEPTIONS as exc:
            return SetupCheck(
                code="sqlite_database",
                label="SQLite database",
                ok=False,
                message=str(exc),
                action_hint="Run alembic upgrade head for the selected profile.",
            )

        return SetupCheck(
            code="sqlite_database",
            label="SQLite database",
            ok=True,
            message="Database file and expected tables exist.",
        )

    def _check_llm_mode(self, config: ProjectConfig) -> SetupCheck:
        if not str(config.llm.extraction_mode).strip():
            return SetupCheck(
                code="llm_mode",
                label="LLM mode",
                ok=False,
                message="LLM extraction mode is not selected.",
                action_hint="Set llm.extraction_mode to fake or openai.",
            )

        key_status = _OpenAIKeyStatus(
            has_effective_key=False,
            message="Fake extraction mode does not require an OpenAI API key.",
        )
        if config.llm.extraction_mode.value == "openai":
            key_status = self._openai_key_status()

        try:
            validate_llm_runtime_config(
                config,
                has_openai_api_key=key_status.has_effective_key,
            )
        except _EXPECTED_SETUP_EXCEPTIONS as exc:
            hint = (
                "Use fake mode, or configure llm.model_extract and an OpenAI API key."
            )
            if config.llm.model_extract and not key_status.has_effective_key:
                hint = (
                    "Store an OpenAI API key in Settings, set OPENAI_API_KEY as a "
                    "developer fallback, or use fake extraction mode."
                )
            return SetupCheck(
                code="llm_mode",
                label="LLM mode",
                ok=False,
                message=str(exc),
                action_hint=hint,
            )

        return SetupCheck(
            code="llm_mode",
            label="LLM mode",
            ok=True,
            message=(
                f"LLM extraction mode is valid for this runtime. {key_status.message}"
            ),
        )

    def _openai_key_status(self) -> _OpenAIKeyStatus:
        if self._openai_secret_service is not None:
            try:
                if self._openai_secret_service.is_configured():
                    return _OpenAIKeyStatus(
                        has_effective_key=True,
                        message="OpenAI API key configured in keyring.",
                    )
            except SecretStorageError as exc:
                if get_environment_openai_api_key() is not None:
                    return _OpenAIKeyStatus(
                        has_effective_key=True,
                        message="OpenAI API key available from environment fallback.",
                    )
                return _OpenAIKeyStatus(
                    has_effective_key=False,
                    message=str(exc),
                )

        if get_environment_openai_api_key() is not None:
            return _OpenAIKeyStatus(
                has_effective_key=True,
                message="OpenAI API key available from environment fallback.",
            )

        return _OpenAIKeyStatus(
            has_effective_key=False,
            message="OpenAI API key not configured.",
        )

    def _check_cv_source(
        self, config: ProjectConfig, profile_paths: ProfilePaths | None
    ) -> SetupCheck:
        if profile_paths is None:
            return _failed_dependency_check(
                code="cv_source",
                label="CV source",
                dependency="active profile",
            )

        try:
            select_default_cv_variant(
                cv_dir=profile_paths.cv_dir,
                default_variant=config.cv.default_variant,
                available_variants=config.cv.variants,
                is_example_profile=config.app.profile_name == "example",
            )
        except _EXPECTED_SETUP_EXCEPTIONS as exc:
            return SetupCheck(
                code="cv_source",
                label="CV source",
                ok=False,
                message=str(exc),
                action_hint=(
                    "Configure a default CV variant and ensure the Markdown variant "
                    "file exists."
                ),
            )

        return SetupCheck(
            code="cv_source",
            label="CV source",
            ok=True,
            message="Default CV variant is configured and readable.",
        )

    def _check_fact_bank(self, profile_paths: ProfilePaths | None) -> SetupCheck:
        if profile_paths is None:
            return _failed_dependency_check(
                code="fact_bank",
                label="Fact bank",
                dependency="active profile",
            )

        try:
            load_fact_bank(profile_paths.fact_bank)
        except _EXPECTED_SETUP_EXCEPTIONS as exc:
            return SetupCheck(
                code="fact_bank",
                label="Fact bank",
                ok=False,
                message=str(exc),
                action_hint="Create a valid fact_bank.yaml with at least one fact.",
            )

        return SetupCheck(
            code="fact_bank",
            label="Fact bank",
            ok=True,
            message="Fact bank exists and validates.",
        )


@dataclass(frozen=True)
class _OpenAIKeyStatus:
    has_effective_key: bool
    message: str


def _check_expected[T](
    *,
    code: str,
    label: str,
    action: Callable[[], T],
    success_message: str,
    failure_hint: str,
) -> tuple[SetupCheck, T | None]:
    try:
        value = action()
    except _EXPECTED_SETUP_EXCEPTIONS as exc:
        return (
            SetupCheck(
                code=code,
                label=label,
                ok=False,
                message=str(exc),
                action_hint=failure_hint,
            ),
            None,
        )

    return (
        SetupCheck(
            code=code,
            label=label,
            ok=True,
            message=success_message,
        ),
        value,
    )


def _failed_dependency_check(*, code: str, label: str, dependency: str) -> SetupCheck:
    return SetupCheck(
        code=code,
        label=label,
        ok=False,
        message=f"Cannot check until {dependency} is valid.",
        action_hint="Fix earlier setup checks first.",
    )


def _read_sqlite_table_names(database_file: Path) -> set[str]:
    with sqlite3.connect(f"file:{database_file}?mode=ro", uri=True) as connection:
        rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    return {str(row[0]) for row in rows}


def _read_missing_sqlite_columns(database_file: Path) -> list[str]:
    missing_columns: list[str] = []
    with sqlite3.connect(f"file:{database_file}?mode=ro", uri=True) as connection:
        for table_name, table in sorted(Base.metadata.tables.items()):
            rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
            actual_columns = {str(row[1]) for row in rows}
            expected_columns = {column.name for column in table.columns}
            for column_name in sorted(expected_columns - actual_columns):
                missing_columns.append(f"{table_name}.{column_name}")
    return missing_columns
