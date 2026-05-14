from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.core.config import ProjectConfig, resolve_project_path


@dataclass(frozen=True)
class ProfilePaths:
    profile_dir: Path
    config_file: Path
    blacklist_file: Path
    cv_dir: Path
    fact_bank: Path
    variants_dir: Path
    applications_dir: Path
    database_file: Path


def build_profile_paths(config: ProjectConfig) -> ProfilePaths:
    profile_dir = resolve_project_path(config.app.data_dir)

    config_filename = (
        "config.example.yaml" if config.app.profile_name == "example" else "config.yaml"
    )

    cv_dir = profile_dir / "cv"

    return ProfilePaths(
        profile_dir=profile_dir,
        config_file=profile_dir / config_filename,
        blacklist_file=profile_dir
        / (
            "blacklist.example.txt"
            if config.app.profile_name == "example"
            else "blacklist.txt"
        ),
        cv_dir=cv_dir,
        fact_bank=cv_dir
        / (
            "fact_bank.example.yaml"
            if config.app.profile_name == "example"
            else "fact_bank.yaml"
        ),
        variants_dir=cv_dir / "variants",
        applications_dir=profile_dir / "applications",
        database_file=profile_dir / "applications.sqlite3",
    )
