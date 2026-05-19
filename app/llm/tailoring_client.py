from __future__ import annotations

import json
from typing import Any, Protocol

from app.core.errors import TailoringWorkflowError
from app.llm.schemas import expected_response_contract_for_task


class SectionTailoringClient(Protocol):
    def complete_text(
        self, task_name: str, payload: dict[str, Any], prompt: str, model: str
    ) -> str: ...

    def complete_json(
        self, task_name: str, payload: dict[str, Any], prompt: str, model: str
    ) -> dict[str, Any]: ...


class FakeSectionTailoringClient:
    def __init__(self) -> None:
        self.captured_json_calls: list[dict[str, Any]] = []
        self.override_text_by_task: dict[str, str] = {}
        self.override_json_by_task: dict[str, dict[str, Any]] = {}

    def complete_text(
        self, task_name: str, payload: dict[str, Any], prompt: str, model: str
    ) -> str:
        self.captured_json_calls.append(
            {
                "task_name": task_name,
                "payload": payload,
                "prompt": prompt,
                "model": model,
            }
        )
        if task_name in self.override_text_by_task:
            return self.override_text_by_task[task_name]
        if task_name in self.override_json_by_task:
            return json.dumps(self.override_json_by_task[task_name], ensure_ascii=False)
        return json.dumps(
            self._default_response(task_name, payload), ensure_ascii=False
        )

    def complete_json(
        self, task_name: str, payload: dict[str, Any], prompt: str, model: str
    ) -> dict[str, Any]:
        return parse_model_json_response(
            self.complete_text(task_name, payload, prompt, model)
        )

    def _default_response(
        self, task_name: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
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
            return {"cover_letter": "Thank you for considering my application."}
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
    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise TailoringWorkflowError(
                "OpenAI mode requires an API key. Add it in Settings → Models first.",
                error_kind="provider_error",
            )
        from openai import OpenAI

        self.client = OpenAI(api_key=api_key)

    def complete_text(
        self, task_name: str, payload: dict[str, Any], prompt: str, model: str
    ) -> str:
        contract = expected_response_contract_for_task(task_name)
        messages = [
            {"role": "system", "content": _system_instruction(task_name)},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "task_name": task_name,
                        "expected_response_contract": contract,
                        "user_prompt_instruction": prompt,
                        "payload": payload,
                    },
                    ensure_ascii=False,
                ),
            },
        ]
        if not model.strip():
            raise TailoringWorkflowError(
                "OpenAI model is empty. Configure OpenAI model settings first.",
                task_name=task_name,
                error_kind="provider_error",
            )
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                response_format={"type": "json_object"},
            )
        except Exception as exc:  # pragma: no cover
            raise TailoringWorkflowError(
                "OpenAI could not complete the tailoring request. "
                "Check API key, model, and network.",
                task_name=task_name,
                error_kind="provider_error",
            ) from exc
        content = response.choices[0].message.content if response.choices else ""
        if not content:
            raise TailoringWorkflowError(
                "OpenAI returned an empty tailoring response.",
                task_name=task_name,
                error_kind="provider_error",
            )
        return content

    def complete_json(
        self, task_name: str, payload: dict[str, Any], prompt: str, model: str
    ) -> dict[str, Any]:
        return parse_model_json_response(
            self.complete_text(task_name, payload, prompt, model)
        )


def parse_model_json_response(raw_text: str) -> dict[str, Any]:
    text = raw_text.strip()
    cleaned = _strip_json_fence(text)
    for candidate in (text, cleaned, _extract_first_json_object(cleaned)):
        if not candidate:
            continue
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if not isinstance(parsed, dict):
            raise TailoringWorkflowError(
                "AI returned unexpected JSON shape; expected top-level object.",
                error_kind="parse_error",
            )
        return parsed
    raise TailoringWorkflowError(
        "AI returned invalid JSON. Retry or adjust the selected Prompt Variant.",
        error_kind="parse_error",
    )


def _strip_json_fence(text: str) -> str:
    if text.startswith("```json") and text.endswith("```"):
        return text.removeprefix("```json").removesuffix("```").strip()
    if text.startswith("```") and text.endswith("```"):
        return text.removeprefix("```").removesuffix("```").strip()
    return text


def _extract_first_json_object(text: str) -> str | None:
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if escaped:
            escaped = False
            continue
        if char == "\\" and in_string:
            escaped = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    return None


def _system_instruction(task_name: str) -> str:
    contract = expected_response_contract_for_task(task_name)
    return (
        "You tailor only provided safe resume content for the pasted job description. "
        "Return JSON only. Do not wrap the response in ```json. "
        "Do not include any text before or after the JSON. "
        "Do not include Markdown, XML, comments, or explanations. "
        f"Expected response contract:\n{contract}"
    )


def _append_csv(value: str, addition: str) -> str:
    value = value.strip()
    return addition if not value else f"{value}, {addition}"


def _append_bullet(value: str, addition: str) -> str:
    value = value.strip()
    bullet = f"- {addition}"
    return bullet if not value else f"{value}\n{bullet}"
