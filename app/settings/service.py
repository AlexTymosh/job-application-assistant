from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AppSetting, PersonProfile, PromptTemplate

DEFAULT_SETTINGS: dict[str, Any] = {
    "exports": {"markdown": False, "html": False, "pdf": True, "docx": True},
    "ai_policy_defaults": {
        "use_master_cv": True,
        "allow_new_bullets": True,
        "allow_hide_bullets": False,
        "allow_title_edits": False,
    },
    "locale": "en",
    "llm_mode": "fake",
    "active_profile_id": None,
    "openai_model_default": os.getenv("OPENAI_MODEL", "gpt-5.4-mini"),
    "openai_model_qa": os.getenv("OPENAI_MODEL_QA", "gpt-5.4-mini"),
    "openai_model_extract": os.getenv("OPENAI_MODEL_EXTRACT", "gpt-5.4-nano"),
    "openai_model_tailor": os.getenv("OPENAI_MODEL_TAILOR", "gpt-5.4-mini"),
}

PROMPT_TEMPLATE_TYPES = [
    "summary",
    "skills",
    "work_experience_bullets",
    "education_achievements",
    "cover_letter",
    "fit_analysis",
]

DEFAULT_USER_PROMPTS: dict[str, str] = {
    "summary": "Rewrite the summary conservatively for the selected job.",
    "skills": (
        "Refine hard and soft skills using only the resume variant and Master CV."
    ),
    "work_experience_bullets": (
        "Improve key bullets without changing employers, dates, or roles."
    ),
    "education_achievements": (
        "Improve achievement bullets without changing institution, specialisation, "
        "or dates."
    ),
    "cover_letter": "Draft a concise cover letter from the tailored resume content.",
    "fit_analysis": (
        "Compare the selected resume content with the pasted job description. Write "
        "a concise fit analysis for the user, including strong matches, weak/missing "
        "areas, and suggested positioning. Do not use a fake numeric ATS score."
    ),
}

INTERNAL_GUARDRAILS = (
    "Internal guardrails are applied in code and are not user-editable."
)
PROMPT_SCOPES = {"global", "profile", "resume", "section"}


@dataclass(frozen=True)
class EffectiveSettings:
    exports: dict[str, bool]
    ai_policy_defaults: dict[str, bool]
    locale: str
    llm_mode: str
    active_profile_id: int | None
    openai_model_default: str
    openai_model_qa: str
    openai_model_extract: str
    openai_model_tailor: str


class SettingsService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def ensure_defaults(self) -> None:
        for key, value in DEFAULT_SETTINGS.items():
            if self.session.get(AppSetting, key) is None:
                self.session.add(AppSetting(key=key, value_json=value))
        self.ensure_prompt_templates(commit=False)
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
            ai_policy_defaults=dict(
                self.get("ai_policy_defaults", DEFAULT_SETTINGS["ai_policy_defaults"])
            ),
            locale=str(self.get("locale", DEFAULT_SETTINGS["locale"])),
            llm_mode=str(self.get("llm_mode", DEFAULT_SETTINGS["llm_mode"])),
            active_profile_id=self.get_active_profile_id(),
            openai_model_default=str(
                self.get(
                    "openai_model_default", DEFAULT_SETTINGS["openai_model_default"]
                )
            ),
            openai_model_qa=str(
                self.get("openai_model_qa", DEFAULT_SETTINGS["openai_model_qa"])
            ),
            openai_model_extract=str(
                self.get(
                    "openai_model_extract", DEFAULT_SETTINGS["openai_model_extract"]
                )
            ),
            openai_model_tailor=str(
                self.get("openai_model_tailor", DEFAULT_SETTINGS["openai_model_tailor"])
            ),
        )

    def get_active_profile_id(self) -> int | None:
        raw_value = self.get("active_profile_id")
        try:
            profile_id = int(raw_value) if raw_value is not None else None
        except (TypeError, ValueError):
            self.set("active_profile_id", None)
            return None
        if profile_id is None:
            return None
        if self.session.get(PersonProfile, profile_id) is None:
            self.set("active_profile_id", None)
            return None
        return profile_id

    def get_active_profile(self) -> PersonProfile | None:
        profile_id = self.get_active_profile_id()
        return (
            self.session.get(PersonProfile, profile_id)
            if profile_id is not None
            else None
        )

    def require_active_profile(self) -> PersonProfile:
        from app.core.errors import ActiveProfileRequiredError

        profile = self.get_active_profile()
        if profile is None:
            raise ActiveProfileRequiredError(
                "Select an active profile before using this workspace."
            )
        return profile

    def set_active_profile(self, profile_id: int | None) -> None:
        if (
            profile_id is not None
            and self.session.get(PersonProfile, profile_id) is None
        ):
            raise ValueError("Profile not found.")
        self.set("active_profile_id", profile_id)

    def list_profiles(self) -> list[PersonProfile]:
        return list(
            self.session.scalars(
                select(PersonProfile).order_by(PersonProfile.display_name)
            )
        )

    def model_settings(self) -> dict[str, str]:
        effective = self.effective()
        return {
            "llm_mode": effective.llm_mode,
            "openai_model_default": effective.openai_model_default,
            "openai_model_qa": effective.openai_model_qa,
            "openai_model_extract": effective.openai_model_extract,
            "openai_model_tailor": effective.openai_model_tailor,
        }

    def set_model_settings(self, values: dict[str, str]) -> None:
        for key in [
            "openai_model_default",
            "openai_model_qa",
            "openai_model_extract",
            "openai_model_tailor",
        ]:
            if key in values:
                self.set(key, values[key].strip())

    def set_llm_mode(self, value: str) -> None:
        self.set("llm_mode", value if value in {"fake", "openai"} else "fake")

    def ensure_prompt_templates(self, *, commit: bool = True) -> None:
        existing = {
            template.block_type
            for template in self.session.scalars(select(PromptTemplate))
            if template.block_type
        }
        for block_type in PROMPT_TEMPLATE_TYPES:
            if block_type not in existing:
                self.session.add(
                    PromptTemplate(
                        scope="global",
                        block_type=block_type,
                        section_type=block_type,
                        name=block_type.replace("_", " ").title(),
                        system_prompt=INTERNAL_GUARDRAILS,
                        user_prompt_template=DEFAULT_USER_PROMPTS[block_type],
                        is_active=True,
                    )
                )
        if commit:
            self.session.commit()

    def list_prompt_templates(self) -> list[PromptTemplate]:
        self.ensure_prompt_templates()
        return list(
            self.session.scalars(
                select(PromptTemplate).order_by(PromptTemplate.block_type)
            )
        )

    def update_prompt_template(
        self, template_id: int, user_prompt_template: str
    ) -> None:
        template = self.session.get(PromptTemplate, template_id)
        if template is None:
            raise ValueError("Prompt template not found.")
        template.user_prompt_template = user_prompt_template.strip()
        self.session.commit()

    def get_prompt_instruction(
        self,
        block_type: str,
        *,
        profile_id: int | None = None,
        resume_id: int | None = None,
        section_id: int | None = None,
    ) -> str:
        template = self.resolve_prompt_template(
            block_type,
            profile_id=profile_id,
            resume_id=resume_id,
            section_id=section_id,
        )
        return (
            template.user_prompt_template
            if template
            else DEFAULT_USER_PROMPTS.get(block_type, "")
        )

    def resolve_prompt_template(
        self,
        block_type: str,
        *,
        profile_id: int | None = None,
        resume_id: int | None = None,
        section_id: int | None = None,
    ) -> PromptTemplate | None:
        self.ensure_prompt_templates()
        candidates = list(
            self.session.scalars(
                select(PromptTemplate).where(
                    PromptTemplate.block_type == block_type,
                    PromptTemplate.is_active.is_(True),
                )
            )
        )
        for scope, p_id, r_id, s_id in [
            ("section", None, None, section_id),
            ("resume", None, resume_id, None),
            ("profile", profile_id, None, None),
            ("global", None, None, None),
        ]:
            for template in candidates:
                if (
                    template.scope == scope
                    and template.profile_id == p_id
                    and template.resume_id == r_id
                    and template.section_id == s_id
                ):
                    return template
        return None

    def upsert_scoped_prompt_template(
        self,
        *,
        scope: str,
        block_type: str,
        user_prompt_template: str,
        profile_id: int | None = None,
        resume_id: int | None = None,
        section_id: int | None = None,
    ) -> PromptTemplate:
        scope, profile_id, resume_id, section_id = _normalise_prompt_scope(
            scope, profile_id=profile_id, resume_id=resume_id, section_id=section_id
        )
        template = self.session.scalar(
            select(PromptTemplate).where(
                PromptTemplate.scope == scope,
                PromptTemplate.block_type == block_type,
                PromptTemplate.profile_id == profile_id,
                PromptTemplate.resume_id == resume_id,
                PromptTemplate.section_id == section_id,
            )
        )
        if template is None:
            template = PromptTemplate(
                scope=scope,
                block_type=block_type,
                section_type=block_type,
                name=f"{scope.title()} {block_type.replace('_', ' ').title()}",
                user_prompt_template=user_prompt_template.strip(),
                system_prompt=INTERNAL_GUARDRAILS,
                profile_id=profile_id,
                resume_id=resume_id,
                section_id=section_id,
            )
            self.session.add(template)
        else:
            template.user_prompt_template = user_prompt_template.strip()
        self.session.commit()
        return template


def _normalise_prompt_scope(
    scope: str,
    *,
    profile_id: int | None,
    resume_id: int | None,
    section_id: int | None,
) -> tuple[str, int | None, int | None, int | None]:
    """Drop irrelevant ids so stored overrides match resolution rules."""
    if scope not in PROMPT_SCOPES:
        scope = "global"
    if scope == "global":
        return scope, None, None, None
    if scope == "profile":
        return scope, profile_id, None, None
    if scope == "resume":
        return scope, None, resume_id, None
    return scope, None, None, section_id
