from __future__ import annotations

import pytest

import app.secrets.openai_key as openai_key_module
from app.secrets.openai_key import OpenAISecretService, SecretStorageError


class FakeKeyringError(RuntimeError):
    pass


class FakePasswordDeleteError(FakeKeyringError):
    pass


@pytest.fixture(autouse=True)
def fake_keyring_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        openai_key_module,
        "_keyring_error_types",
        lambda: (FakeKeyringError,),
    )
    monkeypatch.setattr(
        openai_key_module,
        "_password_delete_error_types",
        lambda: (FakePasswordDeleteError,),
    )


class FakeKeyring:
    def __init__(self) -> None:
        self.value: str | None = None
        self.raise_on: str | None = None

    def get_password(self, service_name: str, username: str) -> str | None:
        if self.raise_on == "get":
            raise FakeKeyringError("backend unavailable")
        return self.value

    def set_password(self, service_name: str, username: str, password: str) -> None:
        if self.raise_on == "set":
            raise FakeKeyringError("backend unavailable")
        self.value = password

    def delete_password(self, service_name: str, username: str) -> None:
        if self.raise_on == "delete":
            raise FakeKeyringError("backend unavailable")
        if self.value is None:
            raise FakePasswordDeleteError("missing")
        self.value = None


def test_openai_api_key_can_be_stored_and_read() -> None:
    keyring = FakeKeyring()
    service = OpenAISecretService(keyring_backend=keyring)

    service.set_api_key("  sk-test-secret  ")

    assert service.get_api_key() == "sk-test-secret"
    assert service.is_configured() is True


def test_openai_api_key_can_be_deleted() -> None:
    keyring = FakeKeyring()
    service = OpenAISecretService(keyring_backend=keyring)
    service.set_api_key("sk-test-secret")

    service.delete_api_key()

    assert service.get_api_key() is None
    assert service.is_configured() is False


def test_blank_openai_api_key_is_rejected() -> None:
    service = OpenAISecretService(keyring_backend=FakeKeyring())

    with pytest.raises(ValueError, match="must not be blank"):
        service.set_api_key("   ")


def test_keyring_errors_are_converted_to_safe_project_errors() -> None:
    keyring = FakeKeyring()
    keyring.raise_on = "get"
    service = OpenAISecretService(keyring_backend=keyring)

    with pytest.raises(SecretStorageError) as exc_info:
        service.get_api_key()

    assert "OS keyring" in str(exc_info.value)
    assert "sk-" not in str(exc_info.value)
