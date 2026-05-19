from __future__ import annotations

import json
from typing import Any, Protocol

from app.core.errors import TailoringWorkflowError


class SectionTailoringClient(Protocol):
    """Boundary for variant-only tailoring clients."""

    def complete_json(
        self, task_name: str, payload: dict[str, Any], prompt: str, model: str
    ) -> dict[str, Any]: ...


class FakeSectionTailoringClient:
    """Deterministic client for local mode and tests."""

    def __init__(self) -> None:
        self.captured_json_calls: list[dict[str, Any]] = []

    def complete_json(
        self, task_name: str, payload: dict[str, Any], prompt: str, model: str
    ) -> dict[str, Any]:
        self.captured_json_calls.append(
            {
                "task_name": task_name,
                "payload": payload,
                "prompt": prompt,
                "model": model,
            }
        )
        if task_name == "resume_tailoring":
            sections = payload.get("safe_resume", {}).get("sections", {})
            return {
                "summary": (
                    f"{sections.get('summary', {}).get('text', '').strip()} "
                    "Variant-only tailored summary."
                ).strip(),
                "skills": {
                    "hard_skills": _append_csv(
                        sections.get("skills", {}).get("hard", ""),
                        "Variant-only tailored skill",
                    ),
                    "soft_skills": sections.get("skills", {}).get("soft", ""),
                },
                "work_experience": [
                    {
                        "block_id": int(item.get("id")),
                        "key_bullets": _append_bullet(
                            str(item.get("content", "")),
                            "Variant-only tailored bullet.",
                        ),
                    }
                    for item in sections.get("work_experience", [])
                    if item.get("id") is not None
                ],
                "education": [
                    {
                        "block_id": int(item.get("id")),
                        "key_bullets": _append_bullet(
                            str(item.get("content", "")),
                            "Variant-only tailored bullet.",
                        ),
                    }
                    for item in sections.get("education", [])
                    if item.get("id") is not None
                ],
            }
        if task_name == "cover_letter":
            return {
                "cover_letter": (
                    "Thank you for considering my application. The attached tailored "
                    "resume highlights relevant experience for this role."
                )
            }
        if task_name == "fit_analysis":
            return {
                "fit_summary": "The resume appears relevant for the position.",
                "strong_matches": ["Relevant Python and FastAPI experience"],
                "weak_or_missing_points": ["Domain-specific tooling is not explicit"],
                "positioning_advice": ["Emphasise delivery outcomes and ownership"],
                "warnings": ["Review and refine before final submission"],
            }
        return {}


class OpenAISectionTailoringClient:
    """Synchronous OpenAI client for variant-only tailoring."""

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise TailoringWorkflowError(
                "OpenAI mode requires an API key. Add it in Settings → Models first."
            )
        from openai import OpenAI

        self.client = OpenAI(api_key=api_key)

    def complete_json(
        self, task_name: str, payload: dict[str, Any], prompt: str, model: str
    ) -> dict[str, Any]:
        raw_text = self._complete(
            task_name=task_name,
            payload=payload,
            prompt=prompt,
            model=model,
        )
        try:
            parsed = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise TailoringWorkflowError(
                "OpenAI returned invalid JSON for a tailoring task. Try again or "
                "switch to deterministic local mode."
            ) from exc
        if not isinstance(parsed, dict):
            raise TailoringWorkflowError(
                "OpenAI returned an unexpected JSON shape for a tailoring task."
            )
        return parsed

    def _complete(
        self,
        *,
        task_name: str,
        payload: dict[str, Any],
        prompt: str,
        model: str,
    ) -> str:
        messages = [
            {
                "role": "system",
                "content": _system_instruction(task_name),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "task_name": task_name,
                        "user_prompt_instruction": prompt,
                        "payload": payload,
                    },
                    ensure_ascii=False,
                ),
            },
        ]
        if not model.strip():
            raise TailoringWorkflowError(
                "OpenAI model is empty. Configure OpenAI model settings first."
            )
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                response_format={"type": "json_object"},
            )
        except Exception as exc:  # pragma: no cover
            raise TailoringWorkflowError(
                "OpenAI could not complete the tailoring request. Check the API key, "
                "model identifier, and network connection."
            ) from exc
        content = response.choices[0].message.content if response.choices else ""
        if not content:
            raise TailoringWorkflowError("OpenAI returned an empty tailoring response.")
        return content


def _system_instruction(task_name: str) -> str:
    base = (
        "You tailor only the provided variant resume content for the pasted job "
        "description. Header and References are intentionally absent. Follow the "
        "user prompt instruction for style and emphasis."
    )
    schemas = {
        "resume_tailoring": (
            '{"summary":"text","skills":{"hard_skills":"text","soft_skills":"text"},'
            '"work_experience":[{"block_id":1,"key_bullets":"text"}],'
            '"education":[{"block_id":2,"key_bullets":"text"}]}'
        ),
        "cover_letter": '{"cover_letter":"text"}',
        "fit_analysis": (
            '{"fit_summary":"text","strong_matches":["text"],'
            '"weak_or_missing_points":["text"],"positioning_advice":["text"],'
            '"warnings":["text"]}'
        ),
    }
    return (
        f"{base} Return valid JSON only with this shape: {schemas.get(task_name, '{}')}"
    )


def _append_csv(value: str, addition: str) -> str:
    value = value.strip()
    return addition if not value else f"{value}, {addition}"


def _append_bullet(value: str, addition: str) -> str:
    value = value.strip()
    bullet = f"- {addition}"
    return bullet if not value else f"{value}\n{bullet}"
