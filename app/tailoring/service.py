from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import MasterCVEntry, Resume, TailoredResume
from app.resumes.renderer import render_resume_markdown_from_content, resume_to_content
from app.settings.service import SettingsService

AI_EDITABLE_SECTIONS = {"summary", "skills", "work_experience", "education"}
PRIVATE_SECTIONS = {"header", "references"}
PRIVATE_MASTER_CV_CATEGORIES = {
    "header",
    "reference",
    "references",
}


@dataclass
class TailoringPayload:
    base_resume: dict[str, Any]
    master_cv_items: list[dict[str, Any]]
    job_description: str
    prompt_instructions: dict[str, str]


class DeterministicTailoringClient:
    """Deterministic fake AI used for local development and tests."""

    def __init__(self) -> None:
        self.last_payload: TailoringPayload | None = None

    def adapt(self, payload: TailoringPayload) -> dict[str, Any]:
        self.last_payload = payload
        content = _deepcopy_content(payload.base_resume)
        allowed_terms = _allowed_terms(payload.master_cv_items)
        forbidden_terms = _forbidden_terms(payload.master_cv_items)
        sections = content.setdefault("sections", {})
        if sections.get("summary", {}).get("text"):
            instruction = payload.prompt_instructions.get("summary", "")
            summary_suffix = (
                " Tailored for this role using the selected resume variant "
                "and Master CV source material."
            )
            if instruction:
                summary_suffix += f" Prompt focus: {instruction}"
            sections["summary"]["text"] = _append_once(
                sections["summary"]["text"], summary_suffix
            )
        if sections.get("skills") and allowed_terms:
            relevant = allowed_terms
            if relevant:
                additions = ", ".join(
                    term
                    for term in relevant
                    if term not in sections["skills"].get("hard", "")
                )
                if additions:
                    sections["skills"]["hard"] = _join_text(
                        sections["skills"].get("hard", ""), additions
                    )
        for item in sections.get("work_experience", []):
            if item.get("content"):
                item["content"] = _remove_forbidden(
                    _append_once(
                        item["content"],
                        (
                            "\n- Emphasised relevant experience for the pasted "
                            "job description."
                        ),
                    ),
                    forbidden_terms,
                )
        for item in sections.get("education", []):
            if item.get("content"):
                item["content"] = _remove_forbidden(item["content"], forbidden_terms)
        content["tailoring_sources"] = [item["id"] for item in payload.master_cv_items]
        return content


class TailoringService:
    def __init__(
        self, session: Session, client: DeterministicTailoringClient | None = None
    ) -> None:
        self.session = session
        self.client = client or DeterministicTailoringClient()

    def build_payload(
        self, resume: Resume, master_items: list[MasterCVEntry], job_description: str
    ) -> TailoringPayload:
        base_content = resume_to_content(resume)
        safe_sections = {
            key: value
            for key, value in base_content.get("sections", {}).items()
            if key not in PRIVATE_SECTIONS
        }
        base_content["sections"] = safe_sections
        prompt_instructions = self._prompt_instructions(resume)
        return TailoringPayload(
            base_resume=base_content,
            master_cv_items=[
                _master_item_payload(item)
                for item in master_items
                if _is_ai_safe_master_item(item)
            ],
            job_description=job_description,
            prompt_instructions=prompt_instructions,
        )

    def _prompt_instructions(self, resume: Resume) -> dict[str, str]:
        settings = SettingsService(self.session)
        section_ids = {section.section_type: section.id for section in resume.sections}
        return {
            "summary": settings.get_prompt_instruction(
                "summary",
                profile_id=resume.profile_id,
                resume_id=resume.id,
                section_id=section_ids.get("summary"),
            ),
            "skills": settings.get_prompt_instruction(
                "skills",
                profile_id=resume.profile_id,
                resume_id=resume.id,
                section_id=section_ids.get("skills"),
            ),
            "work_experience_bullets": settings.get_prompt_instruction(
                "work_experience_bullets",
                profile_id=resume.profile_id,
                resume_id=resume.id,
                section_id=section_ids.get("work_experience"),
            ),
            "education_achievements": settings.get_prompt_instruction(
                "education_achievements",
                profile_id=resume.profile_id,
                resume_id=resume.id,
                section_id=section_ids.get("education"),
            ),
            "cover_letter": settings.get_prompt_instruction(
                "cover_letter",
                profile_id=resume.profile_id,
                resume_id=resume.id,
            ),
        }

    def tailor(
        self,
        *,
        application_id: int,
        profile_id: int,
        resume: Resume,
        master_items: list[MasterCVEntry],
        job_description: str,
    ) -> TailoredResume:
        payload = self.build_payload(resume, master_items, job_description)
        tailored_content = self.client.adapt(payload)
        # Render/export needs private header/reference sections.
        # Those sections are never sent to the AI payload.
        full_base = resume_to_content(resume)
        for private_key in PRIVATE_SECTIONS:
            if private_key in full_base.get("sections", {}):
                tailored_content.setdefault("sections", {})[private_key] = full_base[
                    "sections"
                ][private_key]
        rendered = render_resume_markdown_from_content(tailored_content)
        tailored = TailoredResume(
            application_id=application_id,
            profile_id=profile_id,
            base_resume_id=resume.id,
            content_json=tailored_content,
            rendered_markdown=rendered,
        )
        self.session.add(tailored)
        self.session.flush()
        return tailored


def _master_item_payload(item: MasterCVEntry) -> dict[str, Any]:
    return {
        "id": item.id,
        "category": item.category,
        "title": item.title,
        "content": item.content,
        "keywords": item.keywords_json or [],
        "allowed_wording": item.allowed_wording,
        "forbidden_wording": item.forbidden_wording,
        "inference_notes": item.inference_notes,
        "claim_strength": item.claim_strength,
    }


def _is_ai_safe_master_item(item: MasterCVEntry) -> bool:
    return item.is_active and item.category not in PRIVATE_MASTER_CV_CATEGORIES


def _deepcopy_content(content: dict[str, Any]) -> dict[str, Any]:
    import copy

    return copy.deepcopy(content)


def _allowed_terms(items: list[dict[str, Any]]) -> list[str]:
    terms: list[str] = []
    for item in items:
        for source in [
            item.get("allowed_wording", ""),
            " ".join(item.get("keywords", [])),
        ]:
            for raw in source.replace("\n", ",").split(","):
                term = raw.strip()
                if term and term not in terms:
                    terms.append(term)
    return terms


def _forbidden_terms(items: list[dict[str, Any]]) -> list[str]:
    terms: list[str] = []
    for item in items:
        for raw in item.get("forbidden_wording", "").replace("\n", ",").split(","):
            term = raw.strip()
            if term:
                terms.append(term)
    return terms


def _append_once(text: str, suffix: str) -> str:
    return text if suffix.strip() in text else text.rstrip() + suffix


def _join_text(text: str, additions: str) -> str:
    return additions if not text.strip() else f"{text.rstrip()}, {additions}"


def _remove_forbidden(text: str, forbidden_terms: list[str]) -> str:
    result = text
    for term in forbidden_terms:
        result = result.replace(term, "").replace("  ", " ")
    return result.strip()
