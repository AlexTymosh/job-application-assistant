from __future__ import annotations

from uuid import UUID

from app.db.models import WarningLevel
from app.db.repositories import ApplicationWarningRepository
from app.preflight.service import PreflightResult


def persist_preflight_warnings(
    *,
    warnings: ApplicationWarningRepository,
    application_id: UUID,
    result: PreflightResult,
) -> None:
    for phrase in result.prompt_injection_phrases:
        warnings.create(
            application_id=application_id,
            code="prompt_injection_phrase",
            message=f"Suspicious phrase detected in job text: {phrase}",
            level=WarningLevel.WARNING,
        )

    for match in result.blacklist_matches:
        warnings.create(
            application_id=application_id,
            code="blacklist_match",
            message=f"Blacklist match detected: {match}",
            level=WarningLevel.WARNING,
        )

    if result.duplicate_application_id is not None:
        warnings.create(
            application_id=application_id,
            code="possible_duplicate",
            message=(
                "Possible duplicate application detected: "
                f"{result.duplicate_application_id}"
            ),
            level=WarningLevel.WARNING,
        )
