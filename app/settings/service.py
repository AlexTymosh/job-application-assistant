from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import AppSetting

DEFAULT_SETTINGS: dict[str, Any] = {
    "exports": {"markdown": False, "html": False, "pdf": True, "docx": True},
    "ai_policy_defaults": {
        "fact_links_required": True,
        "allow_new_bullets": True,
        "allow_hide_bullets": False,
        "allow_title_edits": False,
    },
    "locale": "en",
    "llm_mode": "fake",
}


@dataclass(frozen=True)
class EffectiveSettings:
    exports: dict[str, bool]
    ai_policy_defaults: dict[str, bool]
    locale: str
    llm_mode: str


class SettingsService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def ensure_defaults(self) -> None:
        for key, value in DEFAULT_SETTINGS.items():
            if self.session.get(AppSetting, key) is None:
                self.session.add(AppSetting(key=key, value_json=value))
        self.session.commit()

    def get(self, key: str, default: Any = None) -> Any:
        setting = self.session.get(AppSetting, key)
        return default if setting is None else setting.value_json

    def set(self, key: str, value: Any) -> None:
        setting = self.session.get(AppSetting, key)
        if setting is None:
            self.session.add(AppSetting(key=key, value_json=value))
        else:
            setting.value_json = value
        self.session.commit()

    def effective(self) -> EffectiveSettings:
        self.ensure_defaults()
        return EffectiveSettings(
            exports=dict(self.get("exports", DEFAULT_SETTINGS["exports"])),
            ai_policy_defaults=dict(self.get("ai_policy_defaults", DEFAULT_SETTINGS["ai_policy_defaults"])),
            locale=str(self.get("locale", DEFAULT_SETTINGS["locale"])),
            llm_mode=str(self.get("llm_mode", DEFAULT_SETTINGS["llm_mode"])),
        )
