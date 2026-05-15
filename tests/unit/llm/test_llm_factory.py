from __future__ import annotations

from pathlib import Path

import pytest

from app.core.config import ProjectConfig, load_profile_config
from app.llm import factory
from app.llm.openai_client import OpenAIJobExtractionClient
from app.secrets.openai_key import OpenAISecretService


class FakeKeyring:
    def __init__(self, value: str | None = None) -> None:
        self.value = value

    def get_password(self, service_name: str, username: str) -> str | None:
        return self.value

    def set_password(self, service_name: str, username: str, password: str) -> None:
        self.value = password

    def delete_password(self, service_name: str, username: str) -> None:
        self.value = None


def _openai_config() -> ProjectConfig:
    config = load_profile_config(Path("profiles/example/config.example.yaml"))
    data = config.model_dump()
    data["llm"] = data["llm"] | {
        "extraction_mode": "openai",
        "model_extract": "gpt-test",
    }
    return ProjectConfig.model_validate(data)


def test_openai_factory_passes_resolved_keyring_api_key_without_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, str | None] = {}

    def fake_init(
        self: OpenAIJobExtractionClient,
        model: str,
        client: object | None = None,
        api_key: str | None = None,
    ) -> None:
        captured["model"] = model
        captured["api_key"] = api_key

    monkeypatch.setattr(OpenAIJobExtractionClient, "__init__", fake_init)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    secret_service = OpenAISecretService(keyring_backend=FakeKeyring("sk-keyring"))

    client = factory.build_job_extraction_client(
        _openai_config(),
        openai_secret_service=secret_service,
    )

    assert isinstance(client, OpenAIJobExtractionClient)
    assert captured == {"model": "gpt-test", "api_key": "sk-keyring"}


def test_openai_factory_falls_back_to_environment_key_without_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, str | None] = {}

    def fake_init(
        self: OpenAIJobExtractionClient,
        model: str,
        client: object | None = None,
        api_key: str | None = None,
    ) -> None:
        captured["api_key"] = api_key

    monkeypatch.setattr(OpenAIJobExtractionClient, "__init__", fake_init)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-env")
    secret_service = OpenAISecretService(keyring_backend=FakeKeyring())

    factory.build_job_extraction_client(
        _openai_config(),
        openai_secret_service=secret_service,
    )

    assert captured["api_key"] == "sk-env"
