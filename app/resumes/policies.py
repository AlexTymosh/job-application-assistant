from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AiEditPolicy:
    ai_editable: bool = False
    ai_can_rewrite: bool = False
    ai_can_add: bool = False
    ai_can_hide: bool = False
    fact_link_required: bool = True
    prompt_key: str = ""
    review_required: bool = True
    ai_can_edit_title: bool = False

    @classmethod
    def from_json(cls, value: dict[str, object] | None) -> AiEditPolicy:
        data = value or {}
        return cls(
            ai_editable=bool(data.get("ai_editable", False)),
            ai_can_rewrite=bool(data.get("ai_can_rewrite", False)),
            ai_can_add=bool(data.get("ai_can_add", False)),
            ai_can_hide=bool(data.get("ai_can_hide", False)),
            fact_link_required=bool(data.get("fact_link_required", True)),
            prompt_key=str(data.get("prompt_key", "")),
            review_required=bool(data.get("review_required", True)),
            ai_can_edit_title=bool(data.get("ai_can_edit_title", False)),
        )

    def to_json(self) -> dict[str, object]:
        return {
            "ai_editable": self.ai_editable,
            "ai_can_rewrite": self.ai_can_rewrite,
            "ai_can_add": self.ai_can_add,
            "ai_can_hide": self.ai_can_hide,
            "fact_link_required": self.fact_link_required,
            "prompt_key": self.prompt_key,
            "review_required": self.review_required,
            "ai_can_edit_title": self.ai_can_edit_title,
        }
