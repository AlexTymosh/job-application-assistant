from __future__ import annotations

import os
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import platformdirs

from app.storage.app_dirs import (
    APP_DATA_DIR_ENV_VAR,
    APP_DATA_FOLDER_NAME,
    AppDataPaths,
    build_app_data_paths,
    resolve_default_app_data_root,
)

POINTER_FILE_NAME = "app-data-root.txt"


class AppDataRootSource(StrEnum):
    ENVIRONMENT = "environment"
    USER_SELECTION = "user_selection"
    DEFAULT = "default"


@dataclass(frozen=True)
class AppDataLocationStatus:
    paths: AppDataPaths
    source: AppDataRootSource
    pointer_file: Path
    environment_override: str | None
    user_selected_root: Path | None

    @property
    def is_environment_override_active(self) -> bool:
        return self.source == AppDataRootSource.ENVIRONMENT


def get_app_data_location_status() -> AppDataLocationStatus:
    pointer_file = get_app_data_pointer_file()
    environment_override = _read_non_blank_env(APP_DATA_DIR_ENV_VAR)
    user_selected_root = read_user_selected_app_data_root(pointer_file=pointer_file)

    if environment_override is not None:
        root = Path(environment_override).expanduser()
        source = AppDataRootSource.ENVIRONMENT
    elif user_selected_root is not None:
        root = user_selected_root
        source = AppDataRootSource.USER_SELECTION
    else:
        root = resolve_default_app_data_root()
        source = AppDataRootSource.DEFAULT

    return AppDataLocationStatus(
        paths=build_app_data_paths(root),
        source=source,
        pointer_file=pointer_file,
        environment_override=environment_override,
        user_selected_root=user_selected_root,
    )


def get_app_data_pointer_file() -> Path:
    config_dir = Path(platformdirs.user_config_dir(APP_DATA_FOLDER_NAME))
    return config_dir / POINTER_FILE_NAME


def read_user_selected_app_data_root(
    *, pointer_file: Path | None = None
) -> Path | None:
    pointer_path = pointer_file or get_app_data_pointer_file()
    try:
        raw_value = pointer_path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None
    if not raw_value:
        return None
    return Path(raw_value).expanduser()


def set_user_selected_app_data_root(
    root: Path, *, pointer_file: Path | None = None
) -> Path:
    pointer_path = pointer_file or get_app_data_pointer_file()
    pointer_path.parent.mkdir(parents=True, exist_ok=True)
    normalised_root = normalise_app_data_root(root)
    pointer_path.write_text(f"{normalised_root.as_posix()}\n", encoding="utf-8")
    return pointer_path


def clear_user_selected_app_data_root(*, pointer_file: Path | None = None) -> None:
    pointer_path = pointer_file or get_app_data_pointer_file()
    try:
        pointer_path.unlink()
    except FileNotFoundError:
        return


def normalise_app_data_root(path: Path | str) -> Path:
    return Path(path).expanduser().resolve(strict=False)


def _read_non_blank_env(name: str) -> str | None:
    value = os.getenv(name)
    if value is None or not value.strip():
        return None
    return value.strip()
