from __future__ import annotations

from app.cv.models import AllowedClaimLevel, Fact, FactBank
from app.llm.schemas import ExtractedJob, JobRequirement, RequirementPriority
from app.reports.models import CoverageLevel, EvidenceMatrixItem, ReportRiskLevel


def build_evidence_matrix(
    extracted_job: ExtractedJob,
    fact_bank: FactBank,
) -> list[EvidenceMatrixItem]:
    """Build a deterministic evidence matrix without LLM or filesystem access."""
    return [
        _build_item(requirement=requirement, facts=fact_bank.facts)
        for requirement in extracted_job.requirements
    ]


def _build_item(requirement: JobRequirement, facts: list[Fact]) -> EvidenceMatrixItem:
    matching_facts = [
        fact for fact in facts if _requirement_matches_fact(requirement, fact)
    ]
    claimable_facts = [
        fact
        for fact in matching_facts
        if fact.allowed_claim_level is not AllowedClaimLevel.DO_NOT_CLAIM
    ]

    if claimable_facts:
        return EvidenceMatrixItem(
            requirement_id=requirement.id,
            requirement_text=requirement.text,
            requirement_priority=requirement.priority,
            coverage=CoverageLevel.FULL,
            fact_ids=[fact.id for fact in claimable_facts],
            matched_fact_names=[fact.name for fact in claimable_facts],
            risk_level=_risk_for_claimable_match(requirement, claimable_facts),
            comment=("Requirement is covered by verified claimable fact bank facts."),
        )

    if matching_facts:
        return EvidenceMatrixItem(
            requirement_id=requirement.id,
            requirement_text=requirement.text,
            requirement_priority=requirement.priority,
            coverage=CoverageLevel.MISSING,
            fact_ids=[],
            matched_fact_names=[fact.name for fact in matching_facts],
            risk_level=ReportRiskLevel.HIGH,
            comment=(
                "Matching fact bank facts exist, but they are marked as do not "
                "claim and cannot be used as evidence."
            ),
        )

    return EvidenceMatrixItem(
        requirement_id=requirement.id,
        requirement_text=requirement.text,
        requirement_priority=requirement.priority,
        coverage=CoverageLevel.MISSING,
        fact_ids=[],
        matched_fact_names=[],
        risk_level=_risk_for_missing_requirement(requirement),
        comment="No verified claimable fact was found for this requirement.",
    )


def _risk_for_claimable_match(
    requirement: JobRequirement,
    facts: list[Fact],
) -> ReportRiskLevel:
    if any(
        fact.allowed_claim_level is AllowedClaimLevel.MENTION_ONLY for fact in facts
    ):
        return ReportRiskLevel.MEDIUM

    if requirement.priority is RequirementPriority.UNKNOWN and not any(
        fact.allowed_claim_level is AllowedClaimLevel.STRONG for fact in facts
    ):
        return ReportRiskLevel.MEDIUM

    return ReportRiskLevel.LOW


def _risk_for_missing_requirement(requirement: JobRequirement) -> ReportRiskLevel:
    if requirement.priority is RequirementPriority.MUST_HAVE:
        return ReportRiskLevel.HIGH

    return ReportRiskLevel.MEDIUM


def _requirement_matches_fact(requirement: JobRequirement, fact: Fact) -> bool:
    fact_name = fact.name.strip().casefold()
    requirement_text = requirement.text.casefold()
    requirement_keywords = [keyword.casefold() for keyword in requirement.keywords]

    return fact_name in requirement_text or fact_name in requirement_keywords
