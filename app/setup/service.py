from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from app.db.models import AppSetting, PersonProfile, Resume, ResumeBlock, ResumeSection
from app.settings.service import SettingsService


@dataclass(frozen=True)
class SetupCheck:
    code: str
    label: str
    ok: bool
    message: str
    action_hint: str = ""


@dataclass(frozen=True)
class SetupStatus:
    checks: list[SetupCheck]

    @property
    def is_complete(self) -> bool:
        return all(check.ok for check in self.checks)


class SetupStatusService:
    def __init__(self, session: Session, app_data_root: Path, key_available: bool) -> None:
        self.session = session
        self.app_data_root = app_data_root
        self.key_available = key_available

    def evaluate(self) -> SetupStatus:
        SettingsService(self.session).ensure_defaults()
        inspector = inspect(self.session.bind)
        checks = [
            SetupCheck(
                "app_data_folder",
                "App data folder",
                self.app_data_root.exists(),
                f"Using {self.app_data_root}",
            ),
            SetupCheck(
                "database",
                "SQLite database",
                inspector.has_table("person_profiles"),
                "SQL-first schema is initialised.",
            ),
            SetupCheck(
                "settings",
                "App settings",
                self.session.get(AppSetting, "exports") is not None,
                "Settings are readable.",
            ),
            SetupCheck(
                "keyring",
                "OpenAI keyring",
                True,
                "Keyring status is safe; raw secrets are never displayed.",
            ),
            SetupCheck(
                "profile",
                "Person profile",
                self.session.scalar(select(PersonProfile.id).limit(1)) is not None,
                "Create at least one person profile.",
                "Open Profiles.",
            ),
            SetupCheck(
                "resume",
                "Resume",
                self.session.scalar(select(Resume.id).limit(1)) is not None,
                "Create at least one resume.",
                "Open Resume Builder.",
            ),
            SetupCheck(
                "resume_content",
                "Resume content",
                self.session.scalar(select(ResumeSection.id).limit(1)) is not None and self.session.scalar(select(ResumeBlock.id).limit(1)) is not None,
                "Add at least one section and block.",
                "Open a resume and add structured content.",
            ),
            SetupCheck(
                "fact_policy",
                "Fact policy",
                self.session.get(AppSetting, "ai_policy_defaults") is not None,
                "Default fact-link policy is configured.",
            ),
        ]
        return SetupStatus(checks)
