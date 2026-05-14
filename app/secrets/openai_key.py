from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol

OPENAI_API_KEY_ENV_VAR = "OPENAI_API_KEY"
OPENAI_KEYRING_SERVICE_NAME = "job-application-assistant"
OPENAI_KEYRING_ACCOUNT_NAME = "openai_api_key"


class SecretStorageError(RuntimeError):
    """Raised when the local secret store cannot complete an expected operation."""


class _UnavailableKeyringError(RuntimeError):
    """Raised by the fallback backend when keyring is not importable."""


class KeyringBackend(Protocol):
    def get_password(self, service_name: str, username: str) -> str | None: ...

    def set_password(self, service_name: str, username: str, password: str) -> None: ...

    def delete_password(self, service_name: str, username: str) -> None: ...


@dataclass(frozen=True)
class OpenAISecretService:
    """Store and resolve the OpenAI API key through the OS keyring boundary."""

    keyring_backend: KeyringBackend
    service_name: str = OPENAI_KEYRING_SERVICE_NAME
    account_name: str = OPENAI_KEYRING_ACCOUNT_NAME

    def get_api_key(self) -> str | None:
        try:
            value = self.keyring_backend.get_password(
                self.service_name,
                self.account_name,
            )
        except _keyring_error_types() as exc:
            raise SecretStorageError(
                "OpenAI API key could not be read from the OS keyring."
            ) from exc

        if value is None or not value.strip():
            return None
        return value.strip()

    def set_api_key(self, value: str) -> None:
        normalised = value.strip()
        if not normalised:
            raise ValueError("OpenAI API key must not be blank.")

        try:
            self.keyring_backend.set_password(
                self.service_name,
                self.account_name,
                normalised,
            )
        except _keyring_error_types() as exc:
            raise SecretStorageError(
                "OpenAI API key could not be saved to the OS keyring."
            ) from exc

    def delete_api_key(self) -> None:
        try:
            self.keyring_backend.delete_password(
                self.service_name,
                self.account_name,
            )
        except _password_delete_error_types():
            return
        except _keyring_error_types() as exc:
            raise SecretStorageError(
                "OpenAI API key could not be removed from the OS keyring."
            ) from exc

    def is_configured(self) -> bool:
        return self.get_api_key() is not None


def build_openai_secret_service() -> OpenAISecretService:
    try:
        import keyring
    except ImportError:
        return OpenAISecretService(keyring_backend=_UnavailableKeyringBackend())

    return OpenAISecretService(keyring_backend=keyring)


def get_environment_openai_api_key() -> str | None:
    value = os.getenv(OPENAI_API_KEY_ENV_VAR)
    if value is None or not value.strip():
        return None
    return value.strip()


class _UnavailableKeyringBackend:
    def get_password(self, service_name: str, username: str) -> str | None:
        raise _UnavailableKeyringError("The keyring package is not installed.")

    def set_password(self, service_name: str, username: str, password: str) -> None:
        raise _UnavailableKeyringError("The keyring package is not installed.")

    def delete_password(self, service_name: str, username: str) -> None:
        raise _UnavailableKeyringError("The keyring package is not installed.")


def _keyring_error_types() -> tuple[type[Exception], ...]:
    try:
        from keyring.errors import KeyringError
    except ImportError:
        return (_UnavailableKeyringError,)
    return (KeyringError, _UnavailableKeyringError)


def _password_delete_error_types() -> tuple[type[Exception], ...]:
    try:
        from keyring.errors import PasswordDeleteError
    except ImportError:
        return ()
    return (PasswordDeleteError,)
