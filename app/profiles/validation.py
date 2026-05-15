from __future__ import annotations

import re
from pathlib import Path

from app.core.config import ProjectConfig
from app.core.paths import build_profile_paths
from app.storage.location import normalise_app_data_root

_PROFILE_NAME_PATTERN = re.compile(r"[^a-z0-9_.-]+")


def normalise_profile_name(name: str) -> str:
    stripped = name.strip().lower()
    if not stripped:
        raise ValueError("Profile name must not be blank.")

    normalised = _PROFILE_NAME_PATTERN.sub("-", stripped).strip("-._")
    if not normalised:
        raise ValueError("Profile name must include letters or numbers.")

    return normalised


def validate_profile_config_identity(
    config: ProjectConfig,
    *,
    expected_profile_name: str,
    expected_data_dir: Path,
) -> None:
    expected_name = normalise_profile_name(expected_profile_name)
    actual_name = normalise_profile_name(config.app.profile_name)

    if actual_name != expected_name:
        raise ValueError(
            "Profile config app.profile_name must match the managed profile "
            f"name: expected {expected_name!r}, found {config.app.profile_name!r}."
        )

    expected_dir = normalise_app_data_root(expected_data_dir)
    config_profile_dir = normalise_app_data_root(
        build_profile_paths(config).profile_dir
    )

    if config_profile_dir != expected_dir:
        raise ValueError(
            "Profile config app.data_dir must resolve to the selected profile "
            f"folder: expected {expected_dir}, found {config_profile_dir}."
        )
