from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Protocol

from app.core.errors import TailoringWorkflowError


class SectionTailoringClient(Protocol):
    """Boundary for section-by-section tailoring clients."""

    def complete_json(
        self, task_name: str, payload: dict[str, Any], prompt: str, model: str
    ) -> dict[str, Any]: ...

    def complete_text(
        self, task_name: str, payload: dict[str, Any], prompt: str, model: str
    ) -> str: ...


@dataclass
class FakeSectionTailoringClient:
    """Deterministic section-by-section client for local mode and tests."""

    captured_json_calls: list[dict[str, Any]] = field(default_factory=list)
    captured_text_calls: list[dict[str, Any]] = field(default_factory=list)

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
        if task_name == "summary":
            summary = payload.get("summary", "").strip()
            return {"text": f"{summary} Variant-only tailored summary.".strip()}
        if task_name == "skills":
            skills = dict(payload.get("skills") or {})
            skills["hard"] = _append_csv(
                skills.get("hard", ""), "Variant-only tailored skill"
            )
            return skills
        if task_name in {"work_experience_bullets", "education_achievements"}:
            key = (
                "work_experience"
                if task_name == "work_experience_bullets"
                else "education"
            )
            items = []
            for item in payload.get(key, []):
                tailored = dict(item)
                tailored["content"] = _append_bullet(
                    str(tailored.get("content", "")),
                    "Variant-only tailored bullet.",
                )
                items.append(tailored)
            return {key: items}
        return {}

    def complete_text(
        self, task_name: str, payload: dict[str, Any], prompt: str, model: str
    ) -> str:
        self.captured_text_calls.append(
            {
                "task_name": task_name,
                "payload": payload,
                "prompt": prompt,
                "model": model,
            }
        )
        if task_name == "fit_analysis":
            return (
                "Fit analysis: strong matches are visible in the selected resume; "
                "review weak or missing areas before applying."
            )
        return (
            "Thank you for considering my application. The attached tailored resume "
            "highlights relevant experience for this role."
        )


class OpenAISectionTailoringClient:
    """Synchronous OpenAI client for variant-only section tailoring."""

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
            json_response=True,
        )
        try:
            parsed = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise TailoringWorkflowError(
                "OpenAI returned invalid JSON for a tailoring section. Try again or "
                "switch to deterministic local mode."
            ) from exc
        if not isinstance(parsed, dict):
            raise TailoringWorkflowError(
                "OpenAI returned an unexpected JSON shape for a tailoring section."
            )
        return parsed

    def complete_text(
        self, task_name: str, payload: dict[str, Any], prompt: str, model: str
    ) -> str:
        return self._complete(
            task_name=task_name,
            payload=payload,
            prompt=prompt,
            model=model,
            json_response=False,
        ).strip()

    def _complete(
        self,
        *,
        task_name: str,
        payload: dict[str, Any],
        prompt: str,
        model: str,
        json_response: bool,
    ) -> str:
        messages = [
            {
                "role": "system",
                "content": _system_instruction(task_name, json_response=json_response),
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
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
        }
        if json_response:
            kwargs["response_format"] = {"type": "json_object"}
        try:
            response = self.client.chat.completions.create(**kwargs)
        except Exception as exc:  # pragma: no cover - provider/runtime boundary
            raise TailoringWorkflowError(
                "OpenAI could not complete the tailoring request. Check the API key, "
                "model identifier, and network connection."
            ) from exc
        content = response.choices[0].message.content if response.choices else ""
        if not content:
            raise TailoringWorkflowError("OpenAI returned an empty tailoring response.")
        return content


def _system_instruction(task_name: str, *, json_response: bool) -> str:
    base = (
        "You tailor only the provided variant resume content for the pasted job "
        "description. Header and References are intentionally absent. Follow the "
        "user prompt instruction for style and emphasis."
    )
    if not json_response:
        return base
    schemas = {
        "summary": '{"text": "tailored summary text"}',
        "skills": (
            '{"hard": "comma separated hard skills", '
            '"soft": "comma separated soft skills"}'
        ),
        "work_experience_bullets": (
            '{"work_experience": [{"id": 1, "content": "bullet lines"}]}'
        ),
        "education_achievements": (
            '{"education": [{"id": 1, "content": "bullet lines"}]}'
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
