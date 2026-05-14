from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import ProjectConfig, load_profile_config
from app.db.session import create_all_tables
from app.main import create_app


def build_complete_client(tmp_path: Path, monkeypatch) -> TestClient:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("APP_DATA_DIR", str(tmp_path / "app-data"))
    profile_dir = tmp_path / "example"
    shutil.copytree(Path("profiles/example"), profile_dir)
    base_config = load_profile_config(Path("profiles/example/config.example.yaml"))
    config_data = base_config.model_dump()
    config_data["app"] = {"profile_name": "example", "data_dir": profile_dir}
    config = ProjectConfig.model_validate(config_data)
    app = create_app(config)
    create_all_tables(app.state.engine)
    return TestClient(app)


def build_incomplete_client(tmp_path: Path, monkeypatch) -> TestClient:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("APP_DATA_DIR", str(tmp_path / "app-data"))
    monkeypatch.setenv("PROFILE_NAME", "missing")
    monkeypatch.setenv("PROFILE_DATA_DIR", str(tmp_path / "missing-profile"))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    return TestClient(create_app())


def test_app_can_start_when_config_or_profile_setup_is_missing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = build_incomplete_client(tmp_path, monkeypatch)

    response = client.get("/setup")

    assert response.status_code == 200
    assert "Setup required" in response.text


def test_setup_returns_200_and_renders_setup_status(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = build_incomplete_client(tmp_path, monkeypatch)

    response = client.get("/setup")

    assert response.status_code == 200
    assert "Setup checks" in response.text
    assert "Profile config" in response.text
    assert "App settings database" in response.text


def test_incomplete_setup_redirects_home_to_setup(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = build_incomplete_client(tmp_path, monkeypatch)

    response = client.get("/", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/setup"


def test_incomplete_setup_redirects_dashboard_before_db_dependency(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = build_incomplete_client(tmp_path, monkeypatch)

    response = client.get("/dashboard", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/setup"


def test_incomplete_setup_redirects_new_application(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = build_incomplete_client(tmp_path, monkeypatch)

    response = client.get("/applications/new", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/setup"


def test_setup_does_not_redirect_to_itself(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    client = build_incomplete_client(tmp_path, monkeypatch)

    response = client.get("/setup", follow_redirects=False)

    assert response.status_code == 200
    assert "Setup required" in response.text


def test_health_routes_remain_available(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    client = build_incomplete_client(tmp_path, monkeypatch)

    assert client.get("/health/live").status_code == 200
    assert client.get("/health/ready").status_code == 200


def test_complete_setup_allows_home_and_dashboard_to_render(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = build_complete_client(tmp_path, monkeypatch)

    home_response = client.get("/")
    dashboard_response = client.get("/dashboard")

    assert home_response.status_code == 200
    assert "Active profile" in home_response.text
    assert dashboard_response.status_code == 200
    assert "Dashboard" in dashboard_response.text


def test_fresh_app_data_initialises_app_settings_database(
    tmp_path: Path,
    monkeypatch,
) -> None:
    app_data_dir = tmp_path / "fresh-app-data"
    monkeypatch.setenv("APP_DATA_DIR", str(app_data_dir))
    monkeypatch.setenv("PROFILE_NAME", "missing")
    monkeypatch.setenv("PROFILE_DATA_DIR", str(tmp_path / "missing-profile"))

    client = TestClient(create_app())

    assert client.get("/health/live").status_code == 200
    assert (app_data_dir / "app.sqlite3").is_file()


def test_corrupt_app_settings_database_leaves_setup_incomplete(
    tmp_path: Path,
    monkeypatch,
) -> None:
    app_data_dir = tmp_path / "corrupt-app-data"
    app_data_dir.mkdir()
    (app_data_dir / "app.sqlite3").write_bytes(b"not a sqlite database")
    monkeypatch.setenv("APP_DATA_DIR", str(app_data_dir))
    monkeypatch.setenv("PROFILE_NAME", "missing")
    monkeypatch.setenv("PROFILE_DATA_DIR", str(tmp_path / "missing-profile"))

    client = TestClient(create_app())

    response = client.get("/setup")
    assert response.status_code == 200
    assert "App settings database" in response.text
    assert "unreadable" in response.text


def test_unexpected_app_settings_startup_error_is_not_hidden(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("APP_DATA_DIR", str(tmp_path / "app-data"))

    def fail_with_programming_error(_app_data_paths):  # type: ignore[no-untyped-def]
        raise RuntimeError("programming error")

    monkeypatch.setattr(
        "app.main.initialise_app_settings_storage",
        fail_with_programming_error,
    )

    with pytest.raises(RuntimeError, match="programming error"):
        create_app()


def test_unexpected_effective_config_startup_error_is_not_hidden(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("APP_DATA_DIR", str(tmp_path / "app-data"))

    def fail_with_programming_error(_app_data_paths):  # type: ignore[no-untyped-def]
        raise RuntimeError("overlay programming error")

    monkeypatch.setattr(
        "app.main.load_effective_project_config",
        fail_with_programming_error,
    )

    with pytest.raises(RuntimeError, match="overlay programming error"):
        create_app()
