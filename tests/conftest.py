from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


class MemorySecretService:
    def __init__(self) -> None:
        self.value: str | None = None

    def get_api_key(self) -> str | None:
        return self.value

    def set_api_key(self, value: str) -> None:
        self.value = value

    def delete_api_key(self) -> None:
        self.value = None


@pytest.fixture
def app_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("APP_DATA_DIR", str(tmp_path / "data"))
    app = create_app(openai_secret_service=MemorySecretService())
    with TestClient(app) as client:
        yield client


@pytest.fixture
def session(app_client: TestClient):
    factory = app_client.app.state.session_factory
    with factory() as db_session:
        yield db_session
