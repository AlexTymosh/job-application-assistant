from __future__ import annotations

from app.llm.prompts.tailoring import (
    NO_FABRICATION_RULES,
    UNTRUSTED_JOB_TEXT_WARNING,
    PromptPayload,
)


def build_cover_letter_prompt(
    *,
    profile_name: str,
    resume_markdown: str,
    job_requirements: list[dict[str, object]],
    user_instruction: str = "",
) -> PromptPayload:
    return PromptPayload(
        prompt_key="cover_letter",
        system_prompt=f"{UNTRUSTED_JOB_TEXT_WARNING}\n{NO_FABRICATION_RULES}",
        user_payload={
            "profile_name": profile_name,
            "resume_content_without_private_contact": resume_markdown,
            "job_requirements": job_requirements,
            "user_instruction": user_instruction,
            "instruction": "Draft a concise cover letter using only supplied evidence.",
        },
    )
