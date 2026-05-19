from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel


class ResumeTailoringSkills(BaseModel):
    hard_skills: str
    soft_skills: str


class ResumeTailoringWorkItem(BaseModel):
    block_id: int
    key_bullets: str


class ResumeTailoringEducationItem(BaseModel):
    block_id: int
    key_bullets: str


class ResumeTailoringResponse(BaseModel):
    summary: str
    skills: ResumeTailoringSkills
    work_experience: list[ResumeTailoringWorkItem]
    education: list[ResumeTailoringEducationItem]


class CoverLetterResponse(BaseModel):
    cover_letter: str


class FitAnalysisResponse(BaseModel):
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
        "summary": {"type": "string"},
        "skills": {
            "type": "object",
            "additionalProperties": False,
            "required": ["hard_skills", "soft_skills"],
            "properties": {
                "hard_skills": {"type": "string"},
                "soft_skills": {"type": "string"},
            },
        },
        "work_experience": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["block_id", "key_bullets"],
                "properties": {
                    "block_id": {"type": "integer"},
                    "key_bullets": {"type": "string"},
                },
            },
        },
        "education": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["block_id", "key_bullets"],
                "properties": {
                    "block_id": {"type": "integer"},
                    "key_bullets": {"type": "string"},
                },
            },
        },
    },
}

COVER_LETTER_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["cover_letter"],
    "properties": {"cover_letter": {"type": "string"}},
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
        "fit_summary": {"type": "string"},
        "strong_matches": {"type": "array", "items": {"type": "string"}},
        "weak_or_missing_points": {
            "type": "array",
            "items": {"type": "string"},
        },
        "positioning_advice": {"type": "array", "items": {"type": "string"}},
        "warnings": {"type": "array", "items": {"type": "string"}},
    },
}


TASK_SCHEMAS = {
    "resume_tailoring": RESUME_TAILORING_RESPONSE_SCHEMA,
    "cover_letter": COVER_LETTER_RESPONSE_SCHEMA,
    "fit_analysis": FIT_ANALYSIS_RESPONSE_SCHEMA,
}


def schema_for_task(task_name: str) -> dict[str, Any]:
    return TASK_SCHEMAS.get(task_name, {"type": "object", "properties": {}})


def expected_response_contract_for_task(task_name: str) -> str:
    return json.dumps(
        schema_for_task(task_name), ensure_ascii=False, indent=2, sort_keys=True
    )
