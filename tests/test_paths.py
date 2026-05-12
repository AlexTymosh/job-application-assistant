from pathlib import Path

from app.core.config import ProjectConfig, load_profile_config
from app.core.paths import build_profile_paths


def test_build_example_profile_paths() -> None:
    config = load_profile_config(Path("profiles/example/config.example.yaml"))

    paths = build_profile_paths(config)

    assert paths.profile_dir.as_posix().endswith("profiles/example")
    assert paths.cv_dir.as_posix().endswith("profiles/example/cv")
    assert paths.master_cv.as_posix().endswith("profiles/example/cv/master.example.md")
    assert paths.fact_bank.as_posix().endswith(
        "profiles/example/cv/fact_bank.example.yaml"
    )
    assert paths.database_file.as_posix().endswith(
        "profiles/example/applications.sqlite3"
    )


def test_profile_paths_do_not_hardcode_alex() -> None:
    config = load_profile_config(Path("profiles/example/config.example.yaml"))

    paths = build_profile_paths(config)

    all_paths = [
        paths.profile_dir,
        paths.cv_dir,
        paths.master_cv,
        paths.fact_bank,
        paths.database_file,
    ]

    assert all("profiles/alex" not in path.as_posix() for path in all_paths)


def test_build_external_profile_paths(tmp_path: Path) -> None:
    external_profile_dir = tmp_path / "job-application-assistant-data" / "alex"

    config = ProjectConfig.model_validate(
        {
            "app": {
                "profile_name": "alex",
                "data_dir": external_profile_dir,
            },
            "workflow": {},
            "llm": {},
            "cv": {
                "default_variant": "backend_developer",
                "variants": ["backend_developer"],
            },
            "exports": {},
            "guardrails": {},
            "job_reader": {},
            "future_integrations": {},
        }
    )

    paths = build_profile_paths(config)

    assert paths.profile_dir == external_profile_dir
    assert paths.config_file == external_profile_dir / "config.yaml"
    assert paths.blacklist_file == external_profile_dir / "blacklist.txt"
    assert paths.cv_dir == external_profile_dir / "cv"
    assert paths.master_cv == external_profile_dir / "cv" / "master.md"
    assert paths.fact_bank == external_profile_dir / "cv" / "fact_bank.yaml"
    assert paths.database_file == external_profile_dir / "applications.sqlite3"
