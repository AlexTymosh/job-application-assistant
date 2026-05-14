from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.settings.init import initialise_app_settings_storage
from app.storage.app_dirs import (
    APP_DATA_DIR_ENV_VAR,
    AppDataPaths,
    build_app_data_paths,
)
from app.storage.bootstrap import bootstrap_app_data_dirs_for_paths
from app.storage.location import (
    AppDataLocationStatus,
    get_app_data_location_status,
    normalise_app_data_root,
    set_user_selected_app_data_root,
)

README_TEXT = """Local Job Application Assistant data folder

This is the local data folder for the Local Job Application Assistant.

This folder may contain application-managed data such as:
- profiles/
- logs/
- backups/
- app.sqlite3

Do not commit this folder to a public repository.
Raw OpenAI API keys are not stored here; they are stored through the
operating system keyring when configured.
"""

APPROVED_BOOTSTRAP_CHILDREN = frozenset(
    {"profiles", "logs", "backups", "app.sqlite3", "README.txt"}
)


class AppDataFolderError(ValueError):
    pass


@dataclass(frozen=True)
class AppDataPathStatus:
    label: str
    path: Path
    exists: bool
    kind: str


@dataclass(frozen=True)
class AppDataFolderStatus:
    location: AppDataLocationStatus
    path_statuses: list[AppDataPathStatus]


@dataclass(frozen=True)
class AppDataFolderConnectionResult:
    paths: AppDataPaths
    pointer_file: Path


def get_app_data_folder_status() -> AppDataFolderStatus:
    location = get_app_data_location_status()
    paths = location.paths
    statuses = [
        _path_status("App data root", paths.root, "directory"),
        _path_status("Profiles directory", paths.profiles_dir, "directory"),
        _path_status("Logs directory", paths.logs_dir, "directory"),
        _path_status("Backups directory", paths.backups_dir, "directory"),
        _path_status("App settings database", paths.database_file, "file"),
        _path_status("Data folder README", paths.readme_file, "file"),
    ]
    return AppDataFolderStatus(location=location, path_statuses=statuses)


def bootstrap_or_connect_app_data_root(
    submitted_path: str,
) -> AppDataFolderConnectionResult:
    if get_app_data_location_status().is_environment_override_active:
        raise AppDataFolderError(
            f"The active data folder is controlled by {APP_DATA_DIR_ENV_VAR}. "
            "Unset that environment variable before changing the folder in the UI."
        )

    root = validate_user_selected_app_data_root(submitted_path)
    paths = build_app_data_paths(root)
    bootstrap_app_data_dirs_for_paths(paths)
    write_app_data_readme(paths)
    initialise_app_settings_storage(paths)
    pointer_file = set_user_selected_app_data_root(paths.root)
    return AppDataFolderConnectionResult(paths=paths, pointer_file=pointer_file)


def validate_user_selected_app_data_root(submitted_path: str) -> Path:
    if not submitted_path.strip():
        raise AppDataFolderError("Enter a data folder path.")

    root = normalise_app_data_root(submitted_path)
    repo_root = Path(__file__).resolve().parents[2]
    if root == repo_root or root.is_relative_to(repo_root):
        raise AppDataFolderError(
            "Choose a folder outside this repository so private data is not committed."
        )

    if root.exists() and not root.is_dir():
        raise AppDataFolderError("Choose a directory path, not an existing file.")

    parent = root.parent
    if not root.exists() and root.suffix and not parent.exists():
        raise AppDataFolderError(
            "The path looks like a file path and its parent directory does not exist. "
            "Choose a sensible directory path."
        )

    return root


def write_app_data_readme(paths: AppDataPaths) -> None:
    paths.readme_file.write_text(README_TEXT, encoding="utf-8")


def _path_status(label: str, path: Path, kind: str) -> AppDataPathStatus:
    return AppDataPathStatus(label=label, path=path, exists=path.exists(), kind=kind)
