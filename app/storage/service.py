from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.core.config import get_project_root
from app.settings.init import initialise_app_settings_storage
from app.settings.migrations import is_app_settings_schema_current
from app.storage.app_dirs import (
    APP_DATA_DIR_ENV_VAR,
    APP_DATA_FOLDER_NAME,
    AppDataPaths,
    build_app_data_paths,
    resolve_default_app_data_root,
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
    repo_root = get_project_root().resolve()
    if root == repo_root or root == repo_root.parent or root.is_relative_to(repo_root):
        raise AppDataFolderError(
            "Choose a folder outside this repository so private data is not committed."
        )

    if root.exists() and not root.is_dir():
        raise AppDataFolderError("Choose a directory path, not an existing file.")

    parent = root.parent
    if not root.exists():
        if root.suffix and not parent.exists():
            raise AppDataFolderError(
                "The path looks like a file path and its parent directory does "
                "not exist. Choose a sensible directory path."
            )
        if root.name != APP_DATA_FOLDER_NAME:
            raise AppDataFolderError(
                f"New data folders must be named {APP_DATA_FOLDER_NAME}."
            )
        return root

    _reject_broad_existing_root(root)
    if _is_recognisable_app_data_folder(root):
        return root
    if root.name == APP_DATA_FOLDER_NAME and _is_empty_directory(root):
        return root
    if not _is_empty_directory(root):
        raise AppDataFolderError(
            "Choose an app-specific data folder. Existing non-empty folders must "
            "already look like a Local Job Application Assistant data folder."
        )
    if root.name != APP_DATA_FOLDER_NAME:
        raise AppDataFolderError(
            f"Empty existing data folders must be named {APP_DATA_FOLDER_NAME}."
        )
    return root


def write_app_data_readme(paths: AppDataPaths) -> bool:
    if paths.readme_file.exists():
        return False
    paths.readme_file.write_text(README_TEXT, encoding="utf-8")
    return True


def _reject_broad_existing_root(root: Path) -> None:
    if root == Path(root.anchor):
        raise AppDataFolderError(
            "Choose an app-specific folder, not a filesystem root."
        )
    home = Path.home().resolve(strict=False)
    if root == home:
        raise AppDataFolderError("Choose an app-specific folder, not your home folder.")
    documents_root = resolve_default_app_data_root().parent.resolve(strict=False)
    if root == documents_root:
        raise AppDataFolderError(
            "Choose an app-specific folder, not your Documents folder."
        )


def _is_recognisable_app_data_folder(root: Path) -> bool:
    readme_file = root / "README.txt"
    if readme_file.is_file() and README_TEXT.splitlines()[0] in readme_file.read_text(
        encoding="utf-8",
        errors="ignore",
    ):
        return True

    database_file = root / "app.sqlite3"
    if database_file.is_file():
        schema_is_current, _ = is_app_settings_schema_current(database_file)
        if schema_is_current:
            return True

    required_directories = ("profiles", "logs", "backups")
    return all((root / directory).is_dir() for directory in required_directories)


def _is_empty_directory(root: Path) -> bool:
    return next(root.iterdir(), None) is None


def _path_status(label: str, path: Path, kind: str) -> AppDataPathStatus:
    return AppDataPathStatus(label=label, path=path, exists=path.exists(), kind=kind)
