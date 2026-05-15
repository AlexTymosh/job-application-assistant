from __future__ import annotations

from pathlib import Path

from app.storage import app_dirs, location

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def patch_user_locations(monkeypatch, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
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
    monkeypatch.delenv("PROFILE_NAME", raising=False)
    monkeypatch.delenv("PROFILE_DATA_DIR", raising=False)
