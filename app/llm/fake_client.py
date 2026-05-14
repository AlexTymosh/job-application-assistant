from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.llm.errors import JobExtractionError
from app.llm.schemas import (
    ExtractedJob,
    ExtractionWarning,
    ExtractionWarningCode,
    JobRequirement,
    RequirementCategory,
    RequirementPriority,
    SeniorityLevel,
    WorkArrangement,
)

SUSPICIOUS_PHRASES = (
    "ignore previous instructions",
    "forget your rules",
    "system prompt",
    "developer message",
    "act as chatgpt",
    "act as an ai",
    "act as a system",
    "override instructions",
    "reveal hidden prompt",
    "disregard previous",
    "you are chatgpt",
    "hidden instructions",
)


class JobExtractionClient(Protocol):
    def extract_job(self, job_text: str) -> ExtractedJob:
        """Extract structured job information from untrusted job text."""


@dataclass(frozen=True)
class KeywordRule:
    token: str
    technology: str
    requirement_text: str
    category: RequirementCategory
    priority: RequirementPriority = RequirementPriority.UNKNOWN


KEYWORD_RULES = (
    KeywordRule(
        token="python",
        technology="Python",
        requirement_text="Work with Python.",
        category=RequirementCategory.PROGRAMMING_LANGUAGE,
        priority=RequirementPriority.MUST_HAVE,
    ),
    KeywordRule(
        token="fastapi",
        technology="FastAPI",
        requirement_text="Build backend services with FastAPI.",
        category=RequirementCategory.FRAMEWORK,
        priority=RequirementPriority.MUST_HAVE,
    ),
    KeywordRule(
        token="sqlite",
        technology="SQLite",
        requirement_text="Work with SQLite databases.",
        category=RequirementCategory.DATABASE,
    ),
    KeywordRule(
        token="postgresql",
        technology="PostgreSQL",
        requirement_text="Work with PostgreSQL databases.",
        category=RequirementCategory.DATABASE,
    ),
    KeywordRule(
        token="sql",
        technology="SQL",
        requirement_text="Use SQL for data storage and querying.",
        category=RequirementCategory.DATABASE,
    ),
    KeywordRule(
        token="docker",
        technology="Docker",
        requirement_text="Use Docker in the development workflow.",
        category=RequirementCategory.DEVOPS,
    ),
    KeywordRule(
        token="testing",
        technology="Testing",
        requirement_text="Write and maintain automated tests.",
        category=RequirementCategory.TESTING,
    ),
    KeywordRule(
        token="api",
        technology="API",
        requirement_text="Design and maintain APIs.",
        category=RequirementCategory.ARCHITECTURE,
    ),
    KeywordRule(
        token="backend",
        technology="Backend",
        requirement_text="Develop backend application features.",
        category=RequirementCategory.RESPONSIBILITY,
    ),
)


class FakeJobExtractionClient:
    """Deterministic local extraction client for tests and pipeline contracts."""

    def extract_job(self, job_text: str) -> ExtractedJob:
        normalised_text = " ".join(job_text.strip().split())

        if not normalised_text:
            raise JobExtractionError("Job text must not be empty.")

        lowered_text = normalised_text.lower()
        requirements = self._build_requirements(lowered_text, normalised_text)
        technologies = self._build_technologies(lowered_text)
        warnings = self._build_warnings(lowered_text, normalised_text)

        return ExtractedJob(
            job_title=self._infer_job_title(lowered_text),
            seniority_level=self._infer_seniority_level(lowered_text),
            work_arrangement=self._infer_work_arrangement(lowered_text),
            requirements=requirements,
            responsibilities=self._build_responsibilities(lowered_text),
            technologies=technologies,
            warnings=warnings,
        )

    def _build_requirements(
        self,
        lowered_text: str,
        normalised_text: str,
    ) -> list[JobRequirement]:
        requirements: list[JobRequirement] = []
        seen_requirement_ids: set[str] = set()

        for rule in KEYWORD_RULES:
            if rule.token not in lowered_text:
                continue

            requirement_id = f"req_{rule.token.replace(' ', '_')}"

            if requirement_id in seen_requirement_ids:
                continue

            seen_requirement_ids.add(requirement_id)
            requirements.append(
                JobRequirement(
                    id=requirement_id,
                    text=rule.requirement_text,
                    priority=rule.priority,
                    category=rule.category,
                    keywords=[rule.technology],
                    source_excerpt=_source_excerpt(normalised_text, rule.token),
                )
            )

        if requirements:
            return requirements

        return [
            JobRequirement(
                id="req_general",
                text=(
                    "Review the job posting and identify relevant "
                    "delivery responsibilities."
                ),
                priority=RequirementPriority.UNKNOWN,
                category=RequirementCategory.OTHER,
                keywords=[normalised_text.split()[0]],
                source_excerpt=normalised_text[:160],
            )
        ]

    def _build_technologies(self, lowered_text: str) -> list[str]:
        technologies: list[str] = []

        for rule in KEYWORD_RULES:
            if rule.token in lowered_text and rule.technology not in technologies:
                technologies.append(rule.technology)

        return technologies

    def _build_warnings(
        self,
        lowered_text: str,
        normalised_text: str,
    ) -> list[ExtractionWarning]:
        warnings: list[ExtractionWarning] = []

        for phrase in SUSPICIOUS_PHRASES:
            if phrase not in lowered_text:
                continue

            warnings.append(
                ExtractionWarning(
                    code=ExtractionWarningCode.PROMPT_INJECTION_RISK,
                    message=f"Suspicious phrase detected in job text: {phrase}",
                    source_excerpt=_source_excerpt(normalised_text, phrase),
                )
            )

        return warnings

    def _build_responsibilities(self, lowered_text: str) -> list[str]:
        responsibilities: list[str] = []

        if "backend" in lowered_text or "api" in lowered_text:
            responsibilities.append("Develop and maintain backend services.")

        if "testing" in lowered_text:
            responsibilities.append("Maintain automated test coverage.")

        return responsibilities

    def _infer_job_title(self, lowered_text: str) -> str | None:
        if "backend" in lowered_text and "senior" in lowered_text:
            return "Senior Backend Developer"

        if "backend" in lowered_text:
            return "Backend Developer"

        if "developer" in lowered_text and "senior" in lowered_text:
            return "Senior Developer"

        if "developer" in lowered_text:
            return "Developer"

        return None

    def _infer_seniority_level(self, lowered_text: str) -> SeniorityLevel:
        if "principal" in lowered_text:
            return SeniorityLevel.PRINCIPAL

        if "lead" in lowered_text:
            return SeniorityLevel.LEAD

        if "senior" in lowered_text:
            return SeniorityLevel.SENIOR

        if "junior" in lowered_text:
            return SeniorityLevel.JUNIOR

        if "intern" in lowered_text:
            return SeniorityLevel.INTERNSHIP

        return SeniorityLevel.UNKNOWN

    def _infer_work_arrangement(self, lowered_text: str) -> WorkArrangement:
        if "remote" in lowered_text:
            return WorkArrangement.REMOTE

        if "hybrid" in lowered_text:
            return WorkArrangement.HYBRID

        if "onsite" in lowered_text or "on-site" in lowered_text:
            return WorkArrangement.ONSITE

        return WorkArrangement.UNKNOWN


def _source_excerpt(text: str, token: str) -> str:
    start_index = text.lower().find(token.lower())

    if start_index == -1:
        return text[:160]

    excerpt_start = max(0, start_index - 60)
    excerpt_end = min(len(text), start_index + len(token) + 60)

    return text[excerpt_start:excerpt_end]
