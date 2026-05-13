from __future__ import annotations

from typing import Protocol

from app.cv.models import AllowedClaimLevel, CvSection, CvSectionName, Fact, FactBank
from app.llm.schemas import ExtractedJob, JobRequirement
from app.llm.tailoring_schemas import (
    CvChange,
    TailoringAction,
    TailoringResult,
    TailoringRiskLevel,
    TailoringWarning,
    TailoringWarningCode,
)


class JobTailoringClient(Protocol):
    def tailor_cv(
        self,
        original_markdown: str,
        extracted_job: ExtractedJob,
        fact_bank: FactBank,
        allowed_sections: dict[CvSectionName, CvSection],
    ) -> TailoringResult:
        """Tailor a CV in memory using only verified facts and allowed sections."""


class FakeCvTailoringClient:
    """Deterministic in-memory CV tailor for safe pipeline contract tests."""

    def tailor_cv(
        self,
        original_markdown: str,
        extracted_job: ExtractedJob,
        fact_bank: FactBank,
        allowed_sections: dict[CvSectionName, CvSection],
    ) -> TailoringResult:
        summary_section = allowed_sections.get(CvSectionName.SUMMARY)
        if summary_section is None:
            return TailoringResult(
                tailored_markdown=original_markdown,
                changes=[],
                warnings=[
                    TailoringWarning(
                        code=TailoringWarningCode.UNSUPPORTED_SECTION,
                        message=(
                            "The summary section is not available for safe tailoring."
                        ),
                        section=CvSectionName.SUMMARY,
                    )
                ],
            )

        safe_matches = self._match_requirements_to_facts(
            extracted_job.requirements,
            fact_bank.facts,
        )
        warnings = self._build_unmatched_requirement_warnings(
            extracted_job.requirements,
            safe_matches,
        )

        if not safe_matches:
            warnings.append(
                TailoringWarning(
                    code=TailoringWarningCode.NO_RELEVANT_REQUIREMENT,
                    message=(
                        "No safe CV tailoring was possible because no "
                        "requirement matched a claimable verified fact."
                    ),
                    section=CvSectionName.SUMMARY,
                )
            )
            return TailoringResult(
                tailored_markdown=original_markdown,
                changes=[],
                warnings=warnings,
            )

        matched_facts = self._ordered_unique_facts(safe_matches)
        matched_requirement_ids = self._ordered_unique_requirement_ids(safe_matches)
        tailored_summary = self._build_summary(matched_facts)
        tailored_markdown = _replace_section_content(
            original_markdown,
            summary_section,
            tailored_summary,
        )

        change = CvChange(
            section=CvSectionName.SUMMARY,
            action=TailoringAction.REPLACE_SECTION,
            before_text=summary_section.content,
            after_text=tailored_summary,
            reason="Conservatively aligned the summary with matched verified facts.",
            job_requirement_ids=matched_requirement_ids,
            cv_fact_ids=[fact.id for fact in matched_facts],
            risk_level=self._risk_level(matched_facts),
        )

        return TailoringResult(
            tailored_markdown=tailored_markdown,
            changes=[change],
            warnings=warnings,
        )

    def _match_requirements_to_facts(
        self,
        requirements: list[JobRequirement],
        facts: list[Fact],
    ) -> dict[str, list[Fact]]:
        claimable_facts = [
            fact
            for fact in facts
            if fact.allowed_claim_level is not AllowedClaimLevel.DO_NOT_CLAIM
        ]
        matches: dict[str, list[Fact]] = {}

        for requirement in requirements:
            requirement_matches: list[Fact] = []
            for fact in claimable_facts:
                if _requirement_matches_fact(requirement, fact):
                    requirement_matches.append(fact)

            if requirement_matches:
                matches[requirement.id] = requirement_matches

        return matches

    def _build_unmatched_requirement_warnings(
        self,
        requirements: list[JobRequirement],
        matches: dict[str, list[Fact]],
    ) -> list[TailoringWarning]:
        warnings: list[TailoringWarning] = []

        for requirement in requirements:
            if requirement.id in matches:
                continue

            warnings.append(
                TailoringWarning(
                    code=TailoringWarningCode.NO_RELEVANT_REQUIREMENT,
                    message=(
                        "No verified claimable fact matched job requirement "
                        f"'{requirement.id}'."
                    ),
                )
            )

        return warnings

    def _ordered_unique_facts(self, matches: dict[str, list[Fact]]) -> list[Fact]:
        facts: list[Fact] = []
        seen_fact_ids: set[str] = set()

        for requirement_facts in matches.values():
            for fact in requirement_facts:
                if fact.id in seen_fact_ids:
                    continue

                seen_fact_ids.add(fact.id)
                facts.append(fact)

        return facts

    def _ordered_unique_requirement_ids(
        self, matches: dict[str, list[Fact]]
    ) -> list[str]:
        return list(matches.keys())

    def _build_summary(self, facts: list[Fact]) -> str:
        fact_names = _human_join([fact.name for fact in facts])
        return (
            "Backend-focused software developer with verified exposure to "
            f"{fact_names}, described only where supported by the fact bank."
        )

    def _risk_level(self, facts: list[Fact]) -> TailoringRiskLevel:
        if any(
            fact.allowed_claim_level is AllowedClaimLevel.MENTION_ONLY for fact in facts
        ):
            return TailoringRiskLevel.MEDIUM

        return TailoringRiskLevel.LOW


def _requirement_matches_fact(requirement: JobRequirement, fact: Fact) -> bool:
    fact_name = fact.name.casefold()
    requirement_text = requirement.text.casefold()
    requirement_keywords = [keyword.casefold() for keyword in requirement.keywords]

    return fact_name in requirement_text or fact_name in requirement_keywords


def _replace_section_content(
    markdown: str,
    section: CvSection,
    new_content: str,
) -> str:
    start_index = markdown.index(section.start_marker) + len(section.start_marker)
    end_index = markdown.index(section.end_marker)
    replacement = f"\n{new_content.strip()}\n"

    return f"{markdown[:start_index]}{replacement}{markdown[end_index:]}"


def _human_join(values: list[str]) -> str:
    if len(values) == 1:
        return values[0]

    if len(values) == 2:
        return f"{values[0]} and {values[1]}"

    return f"{', '.join(values[:-1])}, and {values[-1]}"
