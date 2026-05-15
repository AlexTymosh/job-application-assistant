from __future__ import annotations

import shutil
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import ProjectConfig, load_profile_config
from app.db import models as _db_models  # noqa: F401
from app.db.session import create_all_tables, create_sqlite_engine
from app.main import create_app
from app.secrets.openai_key import OpenAISecretService
from app.settings.schema import (
    SETTING_DEFAULT_PROFILE_DATA_DIR,
    SETTING_DEFAULT_PROFILE_NAME,
    SETTING_EXPORT_DOCX,
    SETTING_EXPORT_HTML,
    SETTING_EXPORT_MARKDOWN,
    SETTING_EXPORT_PDF,
    SETTING_LLM_EXTRACTION_MODE,
    SETTING_OPENAI_API_KEY_CONFIGURED,
    SETTING_REQUIRE_HUMAN_APPROVAL,
)


class FakeKeyring:
    def __init__(self) -> None:
        self.value: str | None = None

    def get_password(self, service_name: str, username: str) -> str | None:
        return self.value

    def set_password(self, service_name: str, username: str, password: str) -> None:
        self.value = password

    def delete_password(self, service_name: str, username: str) -> None:
        self.value = None


def _build_secret_service() -> OpenAISecretService:
    return OpenAISecretService(keyring_backend=FakeKeyring())


def _copy_example_profile(tmp_path: Path) -> Path:
    profile_dir = tmp_path / "example"
    shutil.copytree(Path("profiles/example"), profile_dir)

    config_file = profile_dir / "config.example.yaml"
    config_file.write_text(
        config_file.read_text(encoding="utf-8").replace(
            'data_dir: "profiles/example"',
            f'data_dir: "{profile_dir.as_posix()}"',
        ),
        encoding="utf-8",
    )

    database_file = profile_dir / "applications.sqlite3"
    database_file.unlink(missing_ok=True)

    engine = create_sqlite_engine(database_file)
    try:
        create_all_tables(engine)
    finally:
        engine.dispose()

    return profile_dir


def _build_config(profile_dir: Path) -> ProjectConfig:
    base_config = load_profile_config(Path("profiles/example/config.example.yaml"))
    config_data = base_config.model_dump()
    config_data["app"] = {"profile_name": "example", "data_dir": profile_dir}
    return ProjectConfig.model_validate(config_data)


def _build_complete_client(tmp_path: Path, monkeypatch) -> TestClient:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("APP_DATA_DIR", str(tmp_path / "app-data"))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    profile_dir = _copy_example_profile(tmp_path)
    app = create_app(
        _build_config(profile_dir), openai_secret_service=_build_secret_service()
    )
    create_all_tables(app.state.engine)
    return TestClient(app)


def _build_env_client(tmp_path: Path, monkeypatch) -> TestClient:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("APP_DATA_DIR", str(tmp_path / "app-data"))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL_EXTRACT", raising=False)
    profile_dir = _copy_example_profile(tmp_path)
    monkeypatch.setenv("PROFILE_NAME", "example")
    monkeypatch.setenv("PROFILE_DATA_DIR", str(profile_dir))
    app = create_app(openai_secret_service=_build_secret_service())
    create_all_tables(app.state.engine)
    return TestClient(app)


def _build_incomplete_client(tmp_path: Path, monkeypatch) -> TestClient:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("APP_DATA_DIR", str(tmp_path / "app-data"))
    monkeypatch.setenv("PROFILE_NAME", "missing")
    monkeypatch.setenv("PROFILE_DATA_DIR", str(tmp_path / "missing-profile"))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    return TestClient(create_app(openai_secret_service=_build_secret_service()))


def _settings_form(**overrides: str) -> dict[str, str]:
    data = {
        SETTING_LLM_EXTRACTION_MODE: "fake",
        SETTING_REQUIRE_HUMAN_APPROVAL: "true",
        SETTING_EXPORT_MARKDOWN: "true",
        SETTING_EXPORT_HTML: "true",
        SETTING_EXPORT_PDF: "true",
        SETTING_EXPORT_DOCX: "true",
        SETTING_DEFAULT_PROFILE_NAME: "",
        SETTING_DEFAULT_PROFILE_DATA_DIR: "",
    }
    data.update(overrides)
    return data


def test_get_settings_returns_200_when_setup_is_complete(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _build_complete_client(tmp_path, monkeypatch)

    response = client.get("/settings")

    assert response.status_code == 200
    assert "Settings" in response.text
    assert "Effective LLM extraction mode" in response.text


def test_get_settings_returns_200_when_setup_is_incomplete(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _build_incomplete_client(tmp_path, monkeypatch)

    response = client.get("/settings")

    assert response.status_code == 200
    assert "Settings remains available" in response.text


def test_incomplete_setup_does_not_redirect_settings_to_setup(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _build_incomplete_client(tmp_path, monkeypatch)

    response = client.get("/settings", follow_redirects=False)

    assert response.status_code == 200
    assert "Setup required" not in response.text


def test_post_settings_saves_fake_mode_and_redirects(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _build_complete_client(tmp_path, monkeypatch)

    response = client.post(
        "/settings",
        data=_settings_form(**{SETTING_LLM_EXTRACTION_MODE: "fake"}),
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/settings"
    assert (
        client.app.state.app_settings_service.get_setting(SETTING_LLM_EXTRACTION_MODE)
        == "fake"
    )


def test_post_settings_saves_openai_mode_without_openai_api_key(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _build_complete_client(tmp_path, monkeypatch)

    response = client.post(
        "/settings",
        data=_settings_form(**{SETTING_LLM_EXTRACTION_MODE: "openai"}),
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert (
        client.app.state.app_settings_service.get_setting(SETTING_LLM_EXTRACTION_MODE)
        == "openai"
    )


def test_setup_status_reports_openai_runtime_requirements_after_openai_mode_save(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _build_env_client(tmp_path, monkeypatch)

    client.post(
        "/settings",
        data=_settings_form(**{SETTING_LLM_EXTRACTION_MODE: "openai"}),
        follow_redirects=False,
    )
    response = client.get("/settings")

    llm_check = next(
        check
        for check in client.app.state.setup_status.checks
        if check.code == "llm_mode"
    )
    assert llm_check.ok is False
    assert "OpenAI extraction mode requires" in response.text


def test_post_settings_persists_unchecked_export_checkboxes_as_false(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _build_complete_client(tmp_path, monkeypatch)
    data = _settings_form()
    for key in [
        SETTING_EXPORT_MARKDOWN,
        SETTING_EXPORT_HTML,
        SETTING_EXPORT_PDF,
        SETTING_EXPORT_DOCX,
    ]:
        data.pop(key)

    response = client.post("/settings", data=data, follow_redirects=False)

    assert response.status_code == 303
    service = client.app.state.app_settings_service
    assert service.get_setting(SETTING_EXPORT_MARKDOWN) is False
    assert service.get_setting(SETTING_EXPORT_HTML) is False
    assert service.get_setting(SETTING_EXPORT_PDF) is False
    assert service.get_setting(SETTING_EXPORT_DOCX) is False


def test_post_settings_persists_unchecked_human_approval_as_false(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _build_complete_client(tmp_path, monkeypatch)
    data = _settings_form()
    data.pop(SETTING_REQUIRE_HUMAN_APPROVAL)

    response = client.post("/settings", data=data, follow_redirects=False)

    assert response.status_code == 303
    assert (
        client.app.state.app_settings_service.get_setting(
            SETTING_REQUIRE_HUMAN_APPROVAL
        )
        is False
    )


def test_post_settings_saves_default_profile_name_and_data_directory(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _build_complete_client(tmp_path, monkeypatch)
    profile_dir = tmp_path / "profile-choice"

    response = client.post(
        "/settings",
        data=_settings_form(
            **{
                SETTING_DEFAULT_PROFILE_NAME: "example",
                SETTING_DEFAULT_PROFILE_DATA_DIR: str(profile_dir),
            }
        ),
        follow_redirects=False,
    )

    assert response.status_code == 303
    service = client.app.state.app_settings_service
    assert service.get_setting(SETTING_DEFAULT_PROFILE_NAME) == "example"
    assert service.get_setting(SETTING_DEFAULT_PROFILE_DATA_DIR) == profile_dir


def test_post_settings_clears_default_profile_selection_when_both_fields_are_blank(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _build_complete_client(tmp_path, monkeypatch)
    service = client.app.state.app_settings_service
    service.set_setting(SETTING_DEFAULT_PROFILE_NAME, "example")
    service.set_setting(SETTING_DEFAULT_PROFILE_DATA_DIR, tmp_path / "old-profile")

    response = client.post(
        "/settings",
        data=_settings_form(
            **{SETTING_DEFAULT_PROFILE_NAME: " ", SETTING_DEFAULT_PROFILE_DATA_DIR: ""}
        ),
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert service.get_setting(SETTING_DEFAULT_PROFILE_NAME) is None
    assert service.get_setting(SETTING_DEFAULT_PROFILE_DATA_DIR) is None


def test_post_settings_rejects_partial_default_profile_selection(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _build_complete_client(tmp_path, monkeypatch)

    response = client.post(
        "/settings",
        data=_settings_form(**{SETTING_DEFAULT_PROFILE_NAME: "example"}),
    )

    assert response.status_code == 400
    assert "must be provided together" in response.text


def test_settings_post_stores_openai_key_without_storing_it_in_sqlite(
    tmp_path: Path,
    monkeypatch,
) -> None:
    app_data_dir = tmp_path / "app-data"
    client = _build_complete_client(tmp_path, monkeypatch)

    response = client.post(
        "/settings",
        data=_settings_form(openai_api_key="sk-not-a-real-key"),
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert client.app.state.openai_secret_service.get_api_key() == "sk-not-a-real-key"
    assert (
        client.app.state.app_settings_service.get_setting(
            SETTING_OPENAI_API_KEY_CONFIGURED
        )
        is True
    )
    sqlite_bytes = (app_data_dir / "app.sqlite3").read_bytes()
    assert b"sk-not-a-real-key" not in sqlite_bytes


def test_settings_page_never_displays_raw_openai_key(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _build_complete_client(tmp_path, monkeypatch)
    client.post(
        "/settings",
        data=_settings_form(openai_api_key="sk-not-a-real-key"),
        follow_redirects=False,
    )

    response = client.get("/settings")

    assert response.status_code == 200
    assert "OpenAI API key configured in keyring" in response.text
    assert "sk-not-a-real-key" not in response.text


def test_settings_post_clears_openai_key_and_metadata(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _build_complete_client(tmp_path, monkeypatch)
    client.app.state.openai_secret_service.set_api_key("sk-not-a-real-key")
    client.app.state.app_settings_service.set_setting(
        SETTING_OPENAI_API_KEY_CONFIGURED, True
    )

    response = client.post(
        "/settings",
        data=_settings_form(clear_openai_api_key="true"),
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert client.app.state.openai_secret_service.get_api_key() is None
    assert (
        client.app.state.app_settings_service.get_setting(
            SETTING_OPENAI_API_KEY_CONFIGURED
        )
        is False
    )


def test_raw_openai_key_is_not_echoed_after_validation_error(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _build_complete_client(tmp_path, monkeypatch)

    response = client.post(
        "/settings",
        data=_settings_form(
            **{SETTING_DEFAULT_PROFILE_NAME: "example"},
            openai_api_key="sk-not-a-real-key",
        ),
    )

    assert response.status_code == 400
    assert "sk-not-a-real-key" not in response.text


def test_saved_settings_affect_effective_runtime_config(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _build_env_client(tmp_path, monkeypatch)

    response = client.post(
        "/settings",
        data=_settings_form(
            **{
                SETTING_LLM_EXTRACTION_MODE: "fake",
                SETTING_EXPORT_PDF: "false",
            }
        ),
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert client.app.state.config.exports.pdf is False
    assert client.app.state.config.llm.extraction_mode == "fake"


def test_runtime_state_is_refreshed_to_incomplete_when_saved_profile_is_unusable(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _build_env_client(tmp_path, monkeypatch)
    assert hasattr(client.app.state, "session_factory")

    response = client.post(
        "/settings",
        data=_settings_form(
            **{
                SETTING_DEFAULT_PROFILE_NAME: "missing",
                SETTING_DEFAULT_PROFILE_DATA_DIR: str(tmp_path / "missing-profile"),
            }
        ),
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert not hasattr(client.app.state, "session_factory")
    assert client.app.state.setup_status.is_complete is False


def test_post_settings_rejects_unsupported_llm_mode(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _build_complete_client(tmp_path, monkeypatch)

    response = client.post(
        "/settings",
        data=_settings_form(**{SETTING_LLM_EXTRACTION_MODE: "anthropic"}),
    )

    assert response.status_code == 400
    assert "Unsupported LLM extraction mode" in response.text


def test_post_settings_rejects_invalid_boolean_value(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _build_complete_client(tmp_path, monkeypatch)

    response = client.post(
        "/settings",
        data=_settings_form(**{SETTING_EXPORT_HTML: "sometimes"}),
    )

    assert response.status_code == 400
    assert "Invalid boolean value" in response.text
