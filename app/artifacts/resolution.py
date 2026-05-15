from __future__ import annotations

from pathlib import Path, PurePosixPath

from app.artifacts.paths import APPLICATIONS_ARTEFACT_ROOT


class UnsafeArtifactPathError(ValueError):
    """Raised when a database artefact path is not a safe relative path."""


def resolve_artifact_path_under_applications_dir(
    *,
    applications_dir: Path,
    stored_relative_path: str,
) -> Path:
    """Resolve a stored artefact path beneath the active profile applications dir."""
    if not stored_relative_path.strip():
        raise UnsafeArtifactPathError("Artefact path must not be empty.")

    if Path(stored_relative_path).is_absolute() or PurePosixPath(stored_relative_path).is_absolute():
        raise UnsafeArtifactPathError("Absolute artefact paths are not allowed.")

    posix_path = PurePosixPath(stored_relative_path)
    if ".." in posix_path.parts:
        raise UnsafeArtifactPathError("Artefact path traversal is not allowed.")

    parts = posix_path.parts
    if not parts or parts[0] != APPLICATIONS_ARTEFACT_ROOT:
        raise UnsafeArtifactPathError("Artefact paths must be relative to the applications artefact root.")

    relative_inside_applications = Path(*parts[1:])
    candidate_path = (applications_dir / relative_inside_applications).resolve()
    resolved_applications_dir = applications_dir.resolve()

    if candidate_path != resolved_applications_dir and (resolved_applications_dir not in candidate_path.parents):
        raise UnsafeArtifactPathError("Artefact path escapes the applications dir.")

    return candidate_path
