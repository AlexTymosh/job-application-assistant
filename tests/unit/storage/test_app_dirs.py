from pathlib import Path

from app.storage import app_dirs
from app.storage.app_dirs import (
    APP_DATA_FOLDER_NAME,
    build_app_data_paths,
    resolve_default_app_data_root,
    resolve_effective_app_data_root,
)


def test_default_root_is_under_documents(monkeypatch, tmp_path: Path) -> None:
    documents_dir = tmp_path / "Documents"
    monkeypatch.setattr(
        app_dirs.platformdirs,
        "user_documents_dir",
        lambda: str(documents_dir),
    )
    monkeypatch.delenv("APP_DATA_DIR", raising=False)

    assert resolve_default_app_data_root() == documents_dir / APP_DATA_FOLDER_NAME
    assert resolve_effective_app_data_root() == documents_dir / APP_DATA_FOLDER_NAME


def test_app_data_dir_environment_override_wins(monkeypatch, tmp_path: Path) -> None:
    documents_dir = tmp_path / "Documents"
    override_dir = tmp_path / "custom-app-data"
    monkeypatch.setattr(
        app_dirs.platformdirs,
        "user_documents_dir",
        lambda: str(documents_dir),
    )
    monkeypatch.setenv("APP_DATA_DIR", str(override_dir))

    assert resolve_effective_app_data_root() == override_dir


def test_build_app_data_paths_returns_path_objects(tmp_path: Path) -> None:
    root = tmp_path / "JobApplicationAssistant"

    paths = build_app_data_paths(root)

    assert paths.root == root
    assert paths.profiles_dir == root / "profiles"
    assert paths.logs_dir == root / "logs"
    assert paths.backups_dir == root / "backups"
    assert paths.database_file == root / "app.sqlite3"
    assert paths.readme_file == root / "README.txt"
    assert all(isinstance(path, Path) for path in paths.__dict__.values())
