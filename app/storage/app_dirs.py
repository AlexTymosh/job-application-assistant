from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import platformdirs

APP_DATA_DIR_ENV_VAR = "APP_DATA_DIR"
APP_DATA_FOLDER_NAME = "JobApplicationAssistant"


@dataclass(frozen=True)
class AppDataPaths:
    root: Path
    profiles_dir: Path
    logs_dir: Path
    backups_dir: Path
    database_file: Path
    readme_file: Path


def build_app_data_paths(root: Path) -> AppDataPaths:
    return AppDataPaths(
        root=root,
        profiles_dir=root / "profiles",
        logs_dir=root / "logs",
        backups_dir=root / "backups",
        database_file=root / "app.sqlite3",
        readme_file=root / "README.txt",
    )


def resolve_default_app_data_root() -> Path:
    documents_dir = Path(platformdirs.user_documents_dir())
    return documents_dir / APP_DATA_FOLDER_NAME


def resolve_effective_app_data_root() -> Path:
    configured_root = os.getenv(APP_DATA_DIR_ENV_VAR)
    if configured_root is not None and configured_root.strip():
        return Path(configured_root).expanduser()

    return resolve_default_app_data_root()


def resolve_app_data_paths() -> AppDataPaths:
    return build_app_data_paths(resolve_effective_app_data_root())
