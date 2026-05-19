from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ApplicationWorkflowError, NotFoundError
from app.db.models import PromptVariant, PromptVariantTemplate

TASK_TYPES = ("resume_tailoring", "cover_letter", "fit_analysis")
DEFAULT_VARIANT_NAME = "Default Prompt Variant"
PROMPT_TEMPLATE_DIR = Path(__file__).parent / "templates"
DEFAULT_PROMPT_FILES = {
    "resume_tailoring": PROMPT_TEMPLATE_DIR / "resume_tailoring.md",
    "cover_letter": PROMPT_TEMPLATE_DIR / "cover_letter.md",
    "fit_analysis": PROMPT_TEMPLATE_DIR / "fit_analysis.md",
}


def _load_default_prompt(task_type: str) -> str:
    try:
        path = DEFAULT_PROMPT_FILES[task_type]
    except KeyError as exc:
        raise ValueError(f"Unknown default prompt task type: {task_type}") from exc

    try:
        content = path.read_text(encoding="utf-8").strip()
    except FileNotFoundError as exc:
        raise RuntimeError(f"Default prompt template file is missing: {path}") from exc

    if not content:
        raise RuntimeError(f"Default prompt template file is empty: {path}")

    return content


DEFAULT_PROMPTS = {task_type: _load_default_prompt(task_type) for task_type in TASK_TYPES}


class PromptVariantService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def ensure_default_variant(self) -> PromptVariant:
        existing = self.session.scalar(
            select(PromptVariant).where(PromptVariant.is_builtin.is_(True))
        )
        if existing is not None:
            self._sync_builtin_templates(existing.id)
            return existing
        variant = PromptVariant(
            name=DEFAULT_VARIANT_NAME,
            description="Built-in default prompts for Variant 1 tailoring tasks.",
            is_builtin=True,
            is_active=True,
        )
        self.session.add(variant)
        self.session.flush()
        self._upsert_templates(variant.id, DEFAULT_PROMPTS)
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

    def get_variant(self, variant_id: int) -> PromptVariant:
        variant = self.session.get(PromptVariant, variant_id)
        if variant is None:
            raise NotFoundError("Prompt Variant not found.")
        return variant

    def create_variant(
        self, *, name: str, description: str, prompts: dict[str, str]
    ) -> PromptVariant:
        variant = PromptVariant(
            name=name.strip() or "Custom Prompt Variant",
            description=description.strip(),
            is_builtin=False,
            is_active=True,
            profile_id=None,
        )
        self.session.add(variant)
        self.session.flush()
        self._upsert_templates(variant.id, prompts)
        self.session.commit()
        return variant

    def update_variant(
        self, variant_id: int, *, name: str, description: str, prompts: dict[str, str]
    ) -> PromptVariant:
        variant = self.get_variant(variant_id)
        if variant.is_builtin:
            raise ApplicationWorkflowError(
                "Built-in Prompt Variant is read-only. "
                "Copy it to a custom variant first."
            )
        variant.name = name.strip() or variant.name
        variant.description = description.strip()
        self._upsert_templates(variant.id, prompts)
        self.session.commit()
        return variant

    def deactivate_variant(self, variant_id: int) -> None:
        variant = self.get_variant(variant_id)
        if variant.is_builtin:
            raise ApplicationWorkflowError(
                "Built-in Prompt Variant cannot be deactivated."
            )
        variant.is_active = False
        self.session.commit()

    def copy_variant(self, variant_id: int) -> PromptVariant:
        source = self.get_variant(variant_id)
        prompts = self.prompts_for(source.id)
        return self.create_variant(
            name=f"{source.name} (Copy)",
            description=source.description,
            prompts=prompts,
        )

    def resolve_or_default(self, prompt_variant_id: int | None) -> PromptVariant:
        default = self.ensure_default_variant()
        if prompt_variant_id is None:
            return default
        variant = self.session.get(PromptVariant, prompt_variant_id)
        if variant is None or not variant.is_active:
            raise ApplicationWorkflowError(
                "The selected Prompt Variant is not available. "
                "Choose an active variant and try again."
            )
        return variant

    def templates_for(self, variant_id: int) -> list[PromptVariantTemplate]:
        self._ensure_templates_exist(variant_id)
        return list(
            self.session.scalars(
                select(PromptVariantTemplate).where(
                    PromptVariantTemplate.prompt_variant_id == variant_id
                )
            )
        )

    def prompts_for(self, variant_id: int) -> dict[str, str]:
        rows = self.templates_for(variant_id)
        prompts = {row.task_type: row.user_prompt_template for row in rows}
        for task in TASK_TYPES:
            prompts.setdefault(task, DEFAULT_PROMPTS[task])
        return prompts

    def _ensure_templates_exist(self, variant_id: int) -> None:
        existing = {
            row.task_type
            for row in self.session.scalars(
                select(PromptVariantTemplate).where(
                    PromptVariantTemplate.prompt_variant_id == variant_id
                )
            )
        }
        for task in TASK_TYPES:
            if task not in existing:
                self.session.add(
                    PromptVariantTemplate(
                        prompt_variant_id=variant_id,
                        task_type=task,
                        user_prompt_template=DEFAULT_PROMPTS[task],
                    )
                )
        self.session.flush()

    def _sync_builtin_templates(self, variant_id: int) -> None:
        self._upsert_templates(variant_id, DEFAULT_PROMPTS)

    def _upsert_templates(self, variant_id: int, prompts: dict[str, str]) -> None:
        for task in TASK_TYPES:
            row = self.session.scalar(
                select(PromptVariantTemplate).where(
                    PromptVariantTemplate.prompt_variant_id == variant_id,
                    PromptVariantTemplate.task_type == task,
                )
            )
            text = (prompts.get(task, "") or DEFAULT_PROMPTS[task]).strip()
            if row is None:
                self.session.add(
                    PromptVariantTemplate(
                        prompt_variant_id=variant_id,
                        task_type=task,
                        user_prompt_template=text,
                    )
                )
            else:
                row.user_prompt_template = text
        self.session.flush()
