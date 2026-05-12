from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from app.preflight.blacklist import find_blacklist_matches, load_blacklist_entries
from app.preflight.duplicate_detection import find_duplicate_by_job_text_hash
from app.preflight.prompt_injection import detect_prompt_injection_phrases


@dataclass(frozen=True)
class PreflightResult:
    prompt_injection_phrases: list[str]
    blacklist_matches: list[str]
    duplicate_application_id: str | None

    @property
    def has_warnings(self) -> bool:
        return bool(
            self.prompt_injection_phrases
            or self.blacklist_matches
            or self.duplicate_application_id
        )


class PreflightService:
    def __init__(self, session: Session, blacklist_path: Path) -> None:
        self._session = session
        self._blacklist_path = blacklist_path

    def check(
        self,
        *,
        profile_name: str,
        job_text: str,
        job_text_hash: str | None,
        exclude_application_id: UUID | None = None,
    ) -> PreflightResult:
        blacklist_entries = load_blacklist_entries(self._blacklist_path)
        duplicate = find_duplicate_by_job_text_hash(
            session=self._session,
            profile_name=profile_name,
            job_text_hash=job_text_hash,
            exclude_application_id=exclude_application_id,
        )

        return PreflightResult(
            prompt_injection_phrases=detect_prompt_injection_phrases(job_text),
            blacklist_matches=find_blacklist_matches(
                text=job_text,
                entries=blacklist_entries,
            ),
            duplicate_application_id=str(duplicate.id) if duplicate else None,
        )
