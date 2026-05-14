from pathlib import Path

from app.storage.bootstrap import bootstrap_app_data_dirs

ROOT = Path(__file__).resolve().parents[1]


def test_bootstrap_creates_required_directories(monkeypatch, tmp_path: Path) -> None:
    app_data_root = tmp_path / "external" / "JobApplicationAssistant"
    monkeypatch.setenv("APP_DATA_DIR", str(app_data_root))

    paths = bootstrap_app_data_dirs()

    assert paths.root == app_data_root
    assert paths.root.is_dir()
    assert paths.profiles_dir.is_dir()
    assert paths.logs_dir.is_dir()
    assert paths.backups_dir.is_dir()


def test_bootstrap_is_idempotent(monkeypatch, tmp_path: Path) -> None:
    app_data_root = tmp_path / "JobApplicationAssistant"
    monkeypatch.setenv("APP_DATA_DIR", str(app_data_root))

    first_paths = bootstrap_app_data_dirs()
    existing_file = first_paths.logs_dir / "existing.log"
    existing_file.write_text("keep this file\n", encoding="utf-8")

    second_paths = bootstrap_app_data_dirs()

    assert second_paths == first_paths
    assert existing_file.read_text(encoding="utf-8") == "keep this file\n"


def test_bootstrap_does_not_create_private_profile_files(
    monkeypatch,
    tmp_path: Path,
) -> None:
    app_data_root = tmp_path / "JobApplicationAssistant"
    monkeypatch.setenv("APP_DATA_DIR", str(app_data_root))

    paths = bootstrap_app_data_dirs()

    assert list(paths.profiles_dir.iterdir()) == []
    assert not paths.database_file.exists()
    assert not paths.readme_file.exists()
    assert not (paths.root / "config.yaml").exists()
    assert not (paths.root / "fact_bank.yaml").exists()
    assert not (paths.root / "applications.sqlite3").exists()


def test_bootstrap_paths_can_be_outside_repository(
    monkeypatch,
    tmp_path: Path,
) -> None:
    app_data_root = tmp_path / "outside-repository" / "JobApplicationAssistant"
    monkeypatch.setenv("APP_DATA_DIR", str(app_data_root))

    paths = bootstrap_app_data_dirs()

    assert not paths.root.resolve().is_relative_to(ROOT.resolve())
    assert paths.profiles_dir.is_dir()
    assert paths.logs_dir.is_dir()
    assert paths.backups_dir.is_dir()
