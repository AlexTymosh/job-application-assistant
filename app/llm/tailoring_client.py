from __future__ import annotations

import json
from typing import Any, Protocol

from app.core.errors import TailoringWorkflowError
from app.llm.schemas import expected_response_contract_for_task


class SectionTailoringClient(Protocol):
    def complete_json(
        self, task_name: str, payload: dict[str, Any], prompt: str, model: str
    ) -> dict[str, Any]: ...


class FakeSectionTailoringClient:
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
                "OpenAI mode requires an API key. Add it in Settings → Models first."
            )
        from openai import OpenAI

        self.client = OpenAI(api_key=api_key)

    def complete_json(
        self, task_name: str, payload: dict[str, Any], prompt: str, model: str
    ) -> dict[str, Any]:
        raw_text = self._complete(
            task_name=task_name, payload=payload, prompt=prompt, model=model
        )
        try:
            return parse_model_json_response(raw_text)
        except TailoringWorkflowError as exc:
            raise TailoringWorkflowError(
                str(exc), task_name=task_name, error_kind="parse_error"
            ) from exc

    def _complete(
        self, *, task_name: str, payload: dict[str, Any], prompt: str, model: str
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
                "OpenAI could not complete the tailoring request. "
                "Check API key, model, and network."
            ) from exc
        content = response.choices[0].message.content if response.choices else ""
        if not content:
            raise TailoringWorkflowError("OpenAI returned an empty tailoring response.")
        return content


def parse_model_json_response(raw_text: str) -> dict[str, Any]:
    text = raw_text.strip()
    cleaned = (
        text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    )
    for candidate in (text, cleaned, _extract_first_json_object(cleaned)):
        if not candidate:
            continue
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if not isinstance(parsed, dict):
            raise TailoringWorkflowError(
                "AI returned unexpected JSON shape; expected top-level object."
            )
        return parsed
    raise TailoringWorkflowError(
        "AI returned invalid JSON. Retry or adjust the selected Prompt Variant."
    )


def _extract_first_json_object(text: str) -> str | None:
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    for index in range(start, len(text)):
        char = text[index]
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
        f"Expected response contract:\n{contract}"
    )


def _append_csv(value: str, addition: str) -> str:
    value = value.strip()
    return addition if not value else f"{value}, {addition}"


def _append_bullet(value: str, addition: str) -> str:
    value = value.strip()
    bullet = f"- {addition}"
    return bullet if not value else f"{value}\n{bullet}"
