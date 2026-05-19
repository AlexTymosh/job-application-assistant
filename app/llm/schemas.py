from __future__ import annotations

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
