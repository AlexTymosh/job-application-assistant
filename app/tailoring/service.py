from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import MasterCVEntry, Resume, TailoredResume
from app.llm.tailoring_client import SectionTailoringClient
from app.resumes.renderer import render_resume_markdown_from_content, resume_to_content
from app.settings.service import SettingsService

AI_EDITABLE_SECTIONS = {"summary", "skills", "work_experience", "education"}
PRIVATE_SECTIONS = {"header", "references"}
AI_SAFE_MASTER_CV_CATEGORIES = {"summary", "skills", "work_experience", "education"}
PRIVATE_MASTER_CV_CATEGORIES = {
    "header",
    "reference",
    "references",
    "languages",
    "certificates",
}
VARIANT_ONLY_TASKS = (
    "summary",
    "skills",
    "work_experience_bullets",
    "education_achievements",
)


class TailoringMode(StrEnum):
    VARIANT_ONLY = "variant_only"
    MASTER_CV_ENHANCED = "master_cv_enhanced"


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
        self,
        session: Session,
        client: DeterministicTailoringClient | None = None,
        section_client: SectionTailoringClient | None = None,
        model: str = "",
    ) -> None:
        self.session = session
        self.client = client or DeterministicTailoringClient()
        self.section_client = section_client
        self.model = model

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
            "fit_analysis": settings.get_prompt_instruction(
                "fit_analysis",
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
        mode: TailoringMode = TailoringMode.MASTER_CV_ENHANCED,
        variant_prompts: dict[str, str] | None = None,
    ) -> TailoredResume:
        if mode == TailoringMode.VARIANT_ONLY:
            tailored_content = self._tailor_variant_only(
                resume, job_description, variant_prompts=variant_prompts
            )
        else:
            payload = self.build_payload(resume, master_items, job_description)
            tailored_content = self.client.adapt(payload)
        tailored_content = self._reattach_private_sections(resume, tailored_content)
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

    def build_variant_only_payloads(
        self, resume: Resume, job_description: str
    ) -> dict[str, dict[str, Any]]:
        safe_content = self._safe_resume_content(resume)
        sections = safe_content.get("sections", {})
        base = {
            "resume_id": safe_content.get("resume_id"),
            "resume_name": safe_content.get("name", ""),
            "target_role": safe_content.get("target_role", ""),
            "job_description": job_description,
        }
        return {
            "summary": {**base, "summary": sections.get("summary", {}).get("text", "")},
            "skills": {**base, "skills": sections.get("skills", {})},
            "work_experience_bullets": {
                **base,
                "work_experience": sections.get("work_experience", []),
            },
            "education_achievements": {
                **base,
                "education": sections.get("education", []),
            },
        }

    def _tailor_variant_only(
        self,
        resume: Resume,
        job_description: str,
        *,
        variant_prompts: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        if self.section_client is None:
            raise RuntimeError("Variant-only tailoring requires a section client.")
        content = _deepcopy_content(self._safe_resume_content(resume))
        # Variant-only mode uses Prompt Variant prompt pack instructions.
        # Legacy scoped section prompts remain in SettingsService for existing
        # Master CV-enhanced flow and future compatibility.
        resume_tailoring_prompt = (variant_prompts or {}).get("resume_tailoring", "")
        prompts = {
            task_name: resume_tailoring_prompt for task_name in VARIANT_ONLY_TASKS
        }
        payloads = self.build_variant_only_payloads(resume, job_description)
        sections = content.setdefault("sections", {})
        for task_name in VARIANT_ONLY_TASKS:
            result = self.section_client.complete_json(
                task_name,
                payloads[task_name],
                prompts.get(task_name, ""),
                self.model,
            )
            if task_name == "summary" and "text" in result:
                sections.setdefault("summary", {})["text"] = str(result["text"])
            elif task_name == "skills":
                sections["skills"] = {
                    "hard": str(result.get("hard", "")),
                    "soft": str(result.get("soft", "")),
                }
            elif task_name == "work_experience_bullets":
                sections["work_experience"] = _merge_item_content(
                    sections.get("work_experience", []),
                    result.get("work_experience", []),
                )
            elif task_name == "education_achievements":
                sections["education"] = _merge_item_content(
                    sections.get("education", []), result.get("education", [])
                )
        content["tailoring_sources"] = []
        content["tailoring_mode"] = TailoringMode.VARIANT_ONLY.value
        return content

    def _safe_resume_content(self, resume: Resume) -> dict[str, Any]:
        base_content = resume_to_content(resume)
        base_content["sections"] = {
            key: value
            for key, value in base_content.get("sections", {}).items()
            if key not in PRIVATE_SECTIONS
        }
        return base_content

    def _reattach_private_sections(
        self, resume: Resume, tailored_content: dict[str, Any]
    ) -> dict[str, Any]:
        # Render/export needs private header/reference sections. Those sections are
        # never sent to AI payloads.
        full_base = resume_to_content(resume)
        for private_key in PRIVATE_SECTIONS:
            if private_key in full_base.get("sections", {}):
                tailored_content.setdefault("sections", {})[private_key] = full_base[
                    "sections"
                ][private_key]
        return tailored_content


def _merge_item_content(
    original_items: list[dict[str, Any]], tailored_items: Any
) -> list[dict[str, Any]]:
    if not isinstance(tailored_items, list):
        return original_items
    content_by_id = {
        item.get("id"): item.get("content")
        for item in tailored_items
        if isinstance(item, dict) and item.get("id") is not None
    }
    merged: list[dict[str, Any]] = []
    for index, original in enumerate(original_items):
        item = dict(original)
        replacement = content_by_id.get(item.get("id"))
        if replacement is None and index < len(tailored_items):
            candidate = tailored_items[index]
            if isinstance(candidate, dict):
                replacement = candidate.get("content")
        if replacement is not None:
            item["content"] = str(replacement)
        merged.append(item)
    return merged


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
    return item.is_active and item.category in AI_SAFE_MASTER_CV_CATEGORIES


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
