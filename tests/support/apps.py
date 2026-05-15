from __future__ import annotations

import shutil
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import ProjectConfig, load_profile_config
from app.db.session import create_all_tables
from app.main import create_app
from app.secrets.openai_key import OpenAISecretService
from tests.support.fakes import FakeKeyring


def build_example_client(
    tmp_path: Path,
    *,
    require_human_approval_before_export: bool | None = None,
) -> TestClient:
    base_config = load_profile_config()
    profile_dir = tmp_path / "example"
    profile_dir.mkdir(parents=True)

    source_cv_dir = Path("profiles/example/cv")
    shutil.copytree(source_cv_dir, profile_dir / "cv")

    (profile_dir / "blacklist.example.txt").write_text(
        "BlockedCorp\n",
        encoding="utf-8",
    )

    config_data = base_config.model_dump()
    config_data["app"] = {"profile_name": "example", "data_dir": profile_dir}

    if require_human_approval_before_export is not None:
        config_data["workflow"] = config_data["workflow"] | {
            "require_human_approval_before_export": (
                require_human_approval_before_export
            )
        }

    config = ProjectConfig.model_validate(config_data)
    app = create_app(
        config,
        openai_secret_service=OpenAISecretService(keyring_backend=FakeKeyring()),
    )
    create_all_tables(app.state.engine)
    return TestClient(app)


def long_job_text(extra: str = "") -> str:
    return (
        "We need a backend developer to build reliable API services, write tests, "
        "work with databases, review code, document decisions, and collaborate with "
        "product stakeholders. The role values clear communication, maintainable "
        "Python services, and careful delivery. "
        f"{extra}"
    )
