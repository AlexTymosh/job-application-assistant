from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AiEditPolicy:
    ai_edit_enabled: bool = False
    use_master_cv: bool = True
    allow_new_bullets: bool = True
    allow_hide_bullets: bool = False
    allow_title_edits: bool = False

    @classmethod
    def from_json(cls, data: dict[str, Any] | None) -> AiEditPolicy:
        data = data or {}
        return cls(
            ai_edit_enabled=bool(data.get("ai_edit_enabled", False)),
            use_master_cv=bool(data.get("use_master_cv", True)),
            allow_new_bullets=bool(data.get("allow_new_bullets", True)),
            allow_hide_bullets=bool(data.get("allow_hide_bullets", False)),
            allow_title_edits=bool(data.get("allow_title_edits", False)),
        )

    def to_json(self) -> dict[str, bool]:
        return {
            "ai_edit_enabled": self.ai_edit_enabled,
            "use_master_cv": self.use_master_cv,
            "allow_new_bullets": self.allow_new_bullets,
            "allow_hide_bullets": self.allow_hide_bullets,
            "allow_title_edits": self.allow_title_edits,
        }
