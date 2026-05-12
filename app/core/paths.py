from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.core.config import ProjectConfig, get_project_root


@dataclass(frozen=True)
class ProfilePaths:
    root: Path
    profile_dir: Path
    config_file: Path
    blacklist_file: Path
    cv_dir: Path
    master_cv: Path
    fact_bank: Path
    variants_dir: Path
    applications_dir: Path
    database_file: Path


def build_profile_paths(config: ProjectConfig) -> ProfilePaths:
    root = get_project_root()
    profile_dir = root / config.app.data_dir

    config_filename = (
        "config.example.yaml" if config.app.profile_name == "example" else "config.yaml"
    )

    cv_dir = profile_dir / "cv"

    return ProfilePaths(
        root=root,
        profile_dir=profile_dir,
        config_file=profile_dir / config_filename,
        blacklist_file=profile_dir
        / (
            "blacklist.example.txt"
            if config.app.profile_name == "example"
            else "blacklist.txt"
        ),
        cv_dir=cv_dir,
        master_cv=cv_dir
        / (
            "master.example.md" if config.app.profile_name == "example" else "master.md"
        ),
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
