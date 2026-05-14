from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from app.secrets.openai_key import OpenAISecretService
from app.storage import app_dirs, location
from app.storage.app_dirs import APP_DATA_FOLDER_NAME, resolve_effective_app_data_root
from app.storage.location import (
    get_app_data_location_status,
    get_app_data_pointer_file,
    set_user_selected_app_data_root,
)
from app.storage.service import README_TEXT


class FakeKeyring:
    def get_password(self, service_name: str, username: str) -> str | None:
        return None

    def set_password(self, service_name: str, username: str, password: str) -> None:
        raise AssertionError("data folder tests must not write to keyring")

    def delete_password(self, service_name: str, username: str) -> None:
        raise AssertionError("data folder tests must not delete from keyring")


def _secret_service() -> OpenAISecretService:
    return OpenAISecretService(keyring_backend=FakeKeyring())


def _patch_user_locations(monkeypatch, tmp_path: Path) -> tuple[Path, Path]:  # type: ignore[no-untyped-def]
    documents_dir = tmp_path / "Documents"
    config_dir = tmp_path / "config"
    monkeypatch.setattr(
        app_dirs.platformdirs,
        "user_documents_dir",
        lambda: str(documents_dir),
    )
    monkeypatch.setattr(
        location.platformdirs,
        "user_config_dir",
        lambda appname: str(config_dir / appname),
    )
    monkeypatch.delenv("APP_DATA_DIR", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    return documents_dir, config_dir


def _client() -> TestClient:
    return TestClient(create_app(openai_secret_service=_secret_service()))


def test_default_location_uses_documents_without_env_or_pointer(
    monkeypatch,
    tmp_path: Path,
) -> None:
    documents_dir, _ = _patch_user_locations(monkeypatch, tmp_path)

    status = get_app_data_location_status()

    assert status.paths.root == documents_dir / APP_DATA_FOLDER_NAME
    assert resolve_effective_app_data_root() == documents_dir / APP_DATA_FOLDER_NAME
    assert status.source.value == "default"


def test_app_data_dir_override_wins_over_persisted_user_selection(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _patch_user_locations(monkeypatch, tmp_path)
    selected_root = tmp_path / "selected" / "JobApplicationAssistant"
    override_root = tmp_path / "override" / "JobApplicationAssistant"
    set_user_selected_app_data_root(selected_root)
    monkeypatch.setenv("APP_DATA_DIR", str(override_root))

    status = get_app_data_location_status()

    assert status.paths.root == override_root
    assert status.user_selected_root == selected_root.resolve(strict=False)
    assert status.source.value == "environment"


def test_data_folder_page_accessible_while_setup_is_incomplete(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _patch_user_locations(monkeypatch, tmp_path)
    client = _client()

    response = client.get("/data-folder")

    assert response.status_code == 200
    assert "Setup is incomplete" in response.text
    assert "Data Folder" in response.text


def test_data_folder_page_shows_current_root_and_path_statuses(
    monkeypatch,
    tmp_path: Path,
) -> None:
    documents_dir, _ = _patch_user_locations(monkeypatch, tmp_path)
    client = _client()

    response = client.get("/data-folder")

    expected_root = documents_dir / APP_DATA_FOLDER_NAME
    assert response.status_code == 200
    assert str(expected_root) in response.text
    assert "profiles" in response.text
    assert "logs" in response.text
    assert "backups" in response.text
    assert "app.sqlite3" in response.text
    assert "README.txt" in response.text
    assert "default Documents location" in response.text


def test_post_creates_safe_external_folder_and_only_approved_app_data_files(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _patch_user_locations(monkeypatch, tmp_path)
    selected_root = tmp_path / "external" / "JobApplicationAssistant"
    client = _client()

    response = client.post(
        "/data-folder",
        data={"app_data_root": str(selected_root)},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert selected_root.is_dir()
    assert (selected_root / "profiles").is_dir()
    assert (selected_root / "logs").is_dir()
    assert (selected_root / "backups").is_dir()
    assert (selected_root / "app.sqlite3").is_file()
    assert (selected_root / "README.txt").is_file()
    assert sorted(path.name for path in selected_root.iterdir()) == [
        "README.txt",
        "app.sqlite3",
        "backups",
        "logs",
        "profiles",
    ]
    assert list((selected_root / "profiles").iterdir()) == []
    assert not (selected_root / "applications.sqlite3").exists()
    assert not (selected_root / "config.yaml").exists()
    assert not (selected_root / "cv").exists()
    assert "OpenAI API keys are not stored here" in (
        selected_root / "README.txt"
    ).read_text(encoding="utf-8")
    assert "sk-" not in README_TEXT.lower()


def test_post_rejects_blank_path(monkeypatch, tmp_path: Path) -> None:
    _patch_user_locations(monkeypatch, tmp_path)
    client = _client()

    response = client.post("/data-folder", data={"app_data_root": "  "})

    assert response.status_code == 400
    assert "Enter a data folder path" in response.text


def test_post_rejects_obvious_file_path_with_missing_parent(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _patch_user_locations(monkeypatch, tmp_path)
    client = _client()
    file_like_path = tmp_path / "missing-parent" / "app-data.txt"

    response = client.post(
        "/data-folder",
        data={"app_data_root": str(file_like_path)},
    )

    assert response.status_code == 400
    assert "looks like a file path" in response.text
    assert not file_like_path.exists()


def test_post_rejects_repository_internal_path(monkeypatch, tmp_path: Path) -> None:
    _patch_user_locations(monkeypatch, tmp_path)
    client = _client()
    repo_internal_path = Path.cwd() / "private-app-data"

    response = client.post(
        "/data-folder",
        data={"app_data_root": str(repo_internal_path)},
    )

    assert response.status_code == 400
    assert "outside this repository" in response.text
    assert not repo_internal_path.exists()


def test_post_rejects_changes_while_app_data_dir_is_active(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _patch_user_locations(monkeypatch, tmp_path)
    override_root = tmp_path / "override" / "JobApplicationAssistant"
    monkeypatch.setenv("APP_DATA_DIR", str(override_root))
    client = _client()

    response = client.post(
        "/data-folder",
        data={"app_data_root": str(tmp_path / "selected")},
    )

    assert response.status_code == 400
    assert "controlled by APP_DATA_DIR" in response.text
    assert "Unset that environment variable" in response.text


def test_successful_post_persists_pointer_outside_app_data_root(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _patch_user_locations(monkeypatch, tmp_path)
    selected_root = tmp_path / "external" / "JobApplicationAssistant"
    client = _client()

    response = client.post(
        "/data-folder",
        data={"app_data_root": str(selected_root)},
        follow_redirects=False,
    )

    pointer_file = get_app_data_pointer_file()
    assert response.status_code == 303
    assert pointer_file.is_file()
    assert not pointer_file.is_relative_to(selected_root)
    assert pointer_file.read_text(encoding="utf-8").strip() == selected_root.as_posix()


def test_successful_post_refreshes_data_folder_and_setup_state(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _patch_user_locations(monkeypatch, tmp_path)
    selected_root = tmp_path / "external" / "JobApplicationAssistant"
    client = _client()

    client.post(
        "/data-folder",
        data={"app_data_root": str(selected_root)},
        follow_redirects=False,
    )
    data_folder_response = client.get("/data-folder")
    setup_response = client.get("/setup")

    assert client.app.state.app_data_paths.root == selected_root
    assert str(selected_root) in data_folder_response.text
    assert "persisted user selection" in data_folder_response.text
    assert setup_response.status_code == 200
    assert 'data-check-code="app_data_root"' in setup_response.text
    assert 'data-check-code="app_settings_database"' in setup_response.text


def test_raw_openai_api_keys_are_not_written_to_app_data_files(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _patch_user_locations(monkeypatch, tmp_path)
    secret_value = "sk-test-secret"
    selected_root = tmp_path / "external" / "JobApplicationAssistant"
    client = _client()

    client.post(
        "/data-folder",
        data={"app_data_root": str(selected_root)},
        follow_redirects=False,
    )

    leaked_files = [
        path.relative_to(selected_root).as_posix()
        for path in selected_root.rglob("*")
        if path.is_file() and secret_value.encode("utf-8") in path.read_bytes()
    ]
    assert leaked_files == []
