from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ConfigDict


class StrictResponseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ResumeTailoringSkills(StrictResponseModel):
    hard_skills: str
    soft_skills: str


class ResumeTailoringWorkItem(StrictResponseModel):
    block_id: int
    key_bullets: str


class ResumeTailoringEducationItem(StrictResponseModel):
    block_id: int
    key_bullets: str


class ResumeTailoringResponse(StrictResponseModel):
    summary: str
    skills: ResumeTailoringSkills
    work_experience: list[ResumeTailoringWorkItem]
    education: list[ResumeTailoringEducationItem]


class CoverLetterResponse(StrictResponseModel):
    cover_letter: str


class FitAnalysisResponse(StrictResponseModel):
    fit_summary: str
    strong_matches: list[str]
    weak_or_missing_points: list[str]
    positioning_advice: list[str]
    warnings: list[str]


RESUME_TAILORING_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["summary", "skills", "work_experience", "education"],
    "properties": {
        "summary": {
            "type": "string",
            "description": "The tailored professional summary as plain text.",
        },
        "skills": {
            "type": "object",
            "additionalProperties": False,
            "required": ["hard_skills", "soft_skills"],
            "properties": {
                "hard_skills": {
                    "type": "string",
                    "description": "Tailored hard skills as plain text.",
                },
                "soft_skills": {
                    "type": "string",
                    "description": "Tailored soft skills as plain text.",
                },
            },
        },
        "work_experience": {
            "type": "array",
            "description": "Tailored key bullets for existing work experience blocks.",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["block_id", "key_bullets"],
                "properties": {
                    "block_id": {
                        "type": "integer",
                        "description": (
                            "Existing work experience block id from the input."
                        ),
                    },
                    "key_bullets": {
                        "type": "string",
                        "description": (
                            "Tailored key bullets as plain text, one bullet per line "
                            "if bullets are used."
                        ),
                    },
                },
            },
        },
        "education": {
            "type": "array",
            "description": "Tailored key bullets for existing education blocks.",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["block_id", "key_bullets"],
                "properties": {
                    "block_id": {
                        "type": "integer",
                        "description": "Existing education block id from the input.",
                    },
                    "key_bullets": {
                        "type": "string",
                        "description": (
                            "Tailored education bullets or achievements as plain text."
                        ),
                    },
                },
            },
        },
    },
}

COVER_LETTER_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["cover_letter"],
    "properties": {
        "cover_letter": {
            "type": "string",
            "description": "The cover letter draft as plain text.",
        }
    },
}

FIT_ANALYSIS_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "fit_summary",
        "strong_matches",
        "weak_or_missing_points",
        "positioning_advice",
        "warnings",
    ],
    "properties": {
        "fit_summary": {
            "type": "string",
            "description": "Concise textual fit summary. No percentage score.",
        },
        "strong_matches": {"type": "array", "items": {"type": "string"}},
        "weak_or_missing_points": {
            "type": "array",
            "items": {"type": "string"},
        },
        "positioning_advice": {"type": "array", "items": {"type": "string"}},
        "warnings": {"type": "array", "items": {"type": "string"}},
    },
}

TASK_SCHEMAS: dict[str, dict[str, Any]] = {
    "resume_tailoring": RESUME_TAILORING_RESPONSE_SCHEMA,
    "cover_letter": COVER_LETTER_RESPONSE_SCHEMA,
    "fit_analysis": FIT_ANALYSIS_RESPONSE_SCHEMA,
}

RESPONSE_MODEL_BY_TASK: dict[str, type[StrictResponseModel]] = {
    "resume_tailoring": ResumeTailoringResponse,
    "cover_letter": CoverLetterResponse,
    "fit_analysis": FitAnalysisResponse,
}


def schema_for_task(task_name: str) -> dict[str, Any]:
    return TASK_SCHEMAS.get(task_name, {"type": "object", "properties": {}})


def expected_response_contract_for_task(task_name: str) -> str:
    return json.dumps(
        schema_for_task(task_name), ensure_ascii=False, indent=2, sort_keys=True
    )
