from __future__ import annotations

from app.storage.app_dirs import AppDataPaths, resolve_app_data_paths


def bootstrap_app_data_dirs() -> AppDataPaths:
    paths = resolve_app_data_paths()

    paths.root.mkdir(parents=True, exist_ok=True)
    paths.profiles_dir.mkdir(parents=True, exist_ok=True)
    paths.logs_dir.mkdir(parents=True, exist_ok=True)
    paths.backups_dir.mkdir(parents=True, exist_ok=True)

    return paths
