from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ApplicationWorkflowError
from app.db.models import PromptVariant, PromptVariantTemplate

TASK_TYPES = ("resume_tailoring", "cover_letter", "fit_analysis")
DEFAULT_VARIANT_NAME = "Default Prompt Variant"
DEFAULT_PROMPTS = {
    "resume_tailoring": (
        "Tailor summary, skills, work bullets, and education bullets for the "
        "pasted job description."
    ),
    "cover_letter": (
        "Draft a concise cover letter aligned with the tailored resume and job "
        "description."
    ),
    "fit_analysis": (
        "Provide textual fit analysis with strong matches, weak or missing points, "
        "and positioning advice."
    ),
}


class PromptVariantService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def ensure_default_variant(self) -> PromptVariant:
        existing = self.session.scalar(
            select(PromptVariant).where(PromptVariant.is_builtin.is_(True))
        )
        if existing is not None:
            return existing
        variant = PromptVariant(
            name=DEFAULT_VARIANT_NAME,
            description="Built-in default prompts for Variant 1 tailoring tasks.",
            is_builtin=True,
            is_active=True,
        )
        self.session.add(variant)
        self.session.flush()
        for task in TASK_TYPES:
            self.session.add(
                PromptVariantTemplate(
                    prompt_variant_id=variant.id,
                    task_type=task,
                    user_prompt_template=DEFAULT_PROMPTS[task],
                )
            )
        self.session.flush()
        return variant

    def list_active(self) -> list[PromptVariant]:
        self.ensure_default_variant()
        return list(
            self.session.scalars(
                select(PromptVariant)
                .where(
                    PromptVariant.is_active.is_(True),
                    PromptVariant.profile_id.is_(None),
                )
                .order_by(PromptVariant.is_builtin.desc(), PromptVariant.name)
            )
        )

    def resolve_or_default(self, prompt_variant_id: int | None) -> PromptVariant:
        default = self.ensure_default_variant()
        self.session.flush()
        if prompt_variant_id is None:
            return default
        variant = self.session.get(PromptVariant, prompt_variant_id)
        if variant is None or not variant.is_active:
            raise ApplicationWorkflowError(
                "The selected Prompt Variant is not available. "
                "Choose an active variant and try again."
            )
        return variant

    def prompts_for(self, variant_id: int) -> dict[str, str]:
        rows = list(
            self.session.scalars(
                select(PromptVariantTemplate).where(
                    PromptVariantTemplate.prompt_variant_id == variant_id
                )
            )
        )
        prompts = {row.task_type: row.user_prompt_template for row in rows}
        for task in TASK_TYPES:
            prompts.setdefault(task, DEFAULT_PROMPTS[task])
        return prompts
