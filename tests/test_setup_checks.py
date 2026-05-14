from __future__ import annotations

import shutil
from pathlib import Path

from app.core.config import ProjectConfig, load_profile_config
from app.db.session import create_all_tables, create_sqlite_engine
from app.setup.service import SetupStatusService
from app.storage.app_dirs import build_app_data_paths, resolve_app_data_paths
from app.storage.bootstrap import bootstrap_app_data_dirs


def build_service(tmp_path: Path) -> SetupStatusService:
    app_data_root = tmp_path / "app-data"
    app_data_paths = build_app_data_paths(app_data_root)
    app_data_paths.root.mkdir(parents=True)
    app_data_paths.profiles_dir.mkdir()
    app_data_paths.logs_dir.mkdir()
    app_data_paths.backups_dir.mkdir()
    return SetupStatusService(app_data_paths=app_data_paths)


def copy_example_profile(tmp_path: Path) -> tuple[Path, ProjectConfig]:
    profile_dir = tmp_path / "example"
    shutil.copytree(Path("profiles/example"), profile_dir)
    base_config = load_profile_config(Path("profiles/example/config.example.yaml"))
    config_data = base_config.model_dump()
    config_data["app"] = {"profile_name": "example", "data_dir": profile_dir}
    return profile_dir, ProjectConfig.model_validate(config_data)


def create_profile_database(config: ProjectConfig) -> None:
    database_file = Path(config.app.data_dir) / "applications.sqlite3"
    engine = create_sqlite_engine(database_file)
    create_all_tables(engine)
    engine.dispose()


def check_by_code(status, code: str):  # type: ignore[no-untyped-def]
    return next(check for check in status.checks if check.code == code)


def test_missing_config_does_not_raise_and_setup_is_incomplete(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("PROFILE_NAME", "missing")
    monkeypatch.setenv("PROFILE_DATA_DIR", str(tmp_path / "missing-profile"))
    service = build_service(tmp_path)

    status = service.build_status()

    assert status.is_complete is False
    assert check_by_code(status, "profile_config").ok is False


def test_app_data_dirs_check_uses_app_data_dir_override(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("APP_DATA_DIR", str(tmp_path / "custom-app-data"))

    app_data_paths = bootstrap_app_data_dirs()
    service = SetupStatusService(app_data_paths=resolve_app_data_paths())
    status = service.build_status(config=None)

    assert app_data_paths.root == tmp_path / "custom-app-data"
    assert check_by_code(status, "app_data_root").ok is True
    assert check_by_code(status, "app_data_profiles_dir").ok is True
    assert check_by_code(status, "app_data_logs_dir").ok is True
    assert check_by_code(status, "app_data_backups_dir").ok is True


def test_complete_example_style_temporary_profile_can_be_complete(
    tmp_path: Path,
) -> None:
    _, config = copy_example_profile(tmp_path)
    create_profile_database(config)
    service = build_service(tmp_path)

    status = service.build_status(config=config)

    assert status.is_complete is True
    assert all(check.ok for check in status.checks)


def test_missing_fact_bank_makes_setup_incomplete(tmp_path: Path) -> None:
    profile_dir, config = copy_example_profile(tmp_path)
    create_profile_database(config)
    (profile_dir / "cv" / "fact_bank.example.yaml").unlink()
    service = build_service(tmp_path)

    status = service.build_status(config=config)

    assert status.is_complete is False
    assert check_by_code(status, "fact_bank").ok is False


def test_missing_default_cv_variant_makes_setup_incomplete(tmp_path: Path) -> None:
    _, config = copy_example_profile(tmp_path)
    create_profile_database(config)
    config_data = config.model_dump()
    config_data["cv"] = config_data["cv"] | {"default_variant": "missing_variant"}
    invalid_config = ProjectConfig.model_validate(config_data)
    service = build_service(tmp_path)

    status = service.build_status(config=invalid_config)

    assert status.is_complete is False
    assert check_by_code(status, "cv_source").ok is False


def test_openai_mode_without_api_key_or_model_makes_setup_incomplete(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _, config = copy_example_profile(tmp_path)
    create_profile_database(config)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    config_data = config.model_dump()
    config_data["llm"] = config_data["llm"] | {
        "extraction_mode": "openai",
        "model_extract": None,
    }
    openai_config = ProjectConfig.model_validate(config_data)
    service = build_service(tmp_path)

    status = service.build_status(config=openai_config)

    assert status.is_complete is False
    assert check_by_code(status, "llm_mode").ok is False


def test_setup_checks_do_not_create_private_profile_files_or_database_tables(
    tmp_path: Path,
) -> None:
    profile_dir, config = copy_example_profile(tmp_path)
    (profile_dir / "applications.sqlite3").unlink(missing_ok=True)
    (profile_dir / "cv" / "fact_bank.example.yaml").unlink()
    service = build_service(tmp_path)

    status = service.build_status(config=config)

    assert status.is_complete is False
    assert not (profile_dir / "applications.sqlite3").exists()
    assert not (profile_dir / "cv" / "fact_bank.example.yaml").exists()
