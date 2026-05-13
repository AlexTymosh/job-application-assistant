from __future__ import annotations

from app.cv.models import FactBank
from app.llm.schemas import ExtractedJob, JobRequirement, RequirementPriority
from app.reports.evidence_matrix import build_evidence_matrix
from app.reports.models import (
    CoverageLevel,
    CvMatchReport,
    EvidenceMatrixItem,
    KeywordCoverageItem,
    MissingSkill,
    ReportRiskLevel,
)

NO_FAKE_ATS_SCORE_WARNING = (
    "No ATS score is provided because closed ATS algorithms "
    "cannot be reliably simulated."
)


def build_cv_match_report(
    application_id: str,
    extracted_job: ExtractedJob,
    fact_bank: FactBank,
    evidence_matrix: list[EvidenceMatrixItem] | None = None,
) -> CvMatchReport:
    """Build an in-memory CV match report from extracted requirements and facts."""
    matrix = evidence_matrix or build_evidence_matrix(extracted_job, fact_bank)
    matrix_by_requirement_id = {item.requirement_id: item for item in matrix}

    must_have_items = [
        item
        for item in matrix
        if item.requirement_priority is RequirementPriority.MUST_HAVE
    ]
    nice_to_have_items = [
        item
        for item in matrix
        if item.requirement_priority is RequirementPriority.NICE_TO_HAVE
    ]

    missing_skills = _build_missing_skills(
        extracted_job.requirements, matrix_by_requirement_id
    )
    risk_level = _overall_risk(matrix, missing_skills)
    warnings = _build_warnings(matrix, missing_skills)

    return CvMatchReport(
        application_id=application_id,
        overall_summary=_build_overall_summary(risk_level, missing_skills),
        must_have_total=len(must_have_items),
        must_have_covered=_count_covered(must_have_items),
        nice_to_have_total=len(nice_to_have_items),
        nice_to_have_covered=_count_covered(nice_to_have_items),
        keyword_coverage=_build_keyword_coverage(
            extracted_job.requirements,
            matrix_by_requirement_id,
        ),
        missing_skills=missing_skills,
        evidence_matrix=matrix,
        risk_level=risk_level,
        warnings=warnings,
    )


def _count_covered(items: list[EvidenceMatrixItem]) -> int:
    return sum(
        item.coverage in {CoverageLevel.FULL, CoverageLevel.PARTIAL} for item in items
    )


def _build_missing_skills(
    requirements: list[JobRequirement],
    matrix_by_requirement_id: dict[str, EvidenceMatrixItem],
) -> list[MissingSkill]:
    missing_skills: list[MissingSkill] = []

    for requirement in requirements:
        item = matrix_by_requirement_id[requirement.id]
        if requirement.priority is RequirementPriority.UNKNOWN:
            continue
        if item.coverage is not CoverageLevel.MISSING:
            continue

        missing_skills.append(
            MissingSkill(
                requirement_id=requirement.id,
                requirement_text=requirement.text,
                priority=requirement.priority,
                reason=item.comment,
            )
        )

    return missing_skills


def _build_keyword_coverage(
    requirements: list[JobRequirement],
    matrix_by_requirement_id: dict[str, EvidenceMatrixItem],
) -> list[KeywordCoverageItem]:
    keyword_items: list[KeywordCoverageItem] = []
    seen_keywords: set[str] = set()

    for requirement in requirements:
        item = matrix_by_requirement_id[requirement.id]

        for keyword in requirement.keywords:
            normalised_keyword = keyword.strip()
            keyword_key = normalised_keyword.casefold()
            if not normalised_keyword or keyword_key in seen_keywords:
                continue

            matched_names = _matched_fact_names_for_keyword(normalised_keyword, item)
            source = ", ".join(matched_names) if matched_names else None

            seen_keywords.add(keyword_key)
            keyword_items.append(
                KeywordCoverageItem(
                    keyword=normalised_keyword,
                    is_covered=source is not None,
                    source=source,
                )
            )

    return keyword_items


def _matched_fact_names_for_keyword(
    keyword: str,
    item: EvidenceMatrixItem,
) -> list[str]:
    keyword_key = keyword.casefold()

    if item.coverage not in {CoverageLevel.FULL, CoverageLevel.PARTIAL}:
        return []

    return [
        fact_name
        for fact_name in item.matched_fact_names
        if keyword_key == fact_name.casefold() or keyword_key in fact_name.casefold()
    ]


def _overall_risk(
    matrix: list[EvidenceMatrixItem],
    missing_skills: list[MissingSkill],
) -> ReportRiskLevel:
    missing_must_have_exists = any(
        skill.priority is RequirementPriority.MUST_HAVE for skill in missing_skills
    )
    high_risk_exists = any(item.risk_level is ReportRiskLevel.HIGH for item in matrix)
    if missing_must_have_exists or high_risk_exists:
        return ReportRiskLevel.HIGH

    missing_nice_to_have_exists = any(
        skill.priority is RequirementPriority.NICE_TO_HAVE for skill in missing_skills
    )
    medium_risk_exists = any(
        item.risk_level is ReportRiskLevel.MEDIUM for item in matrix
    )
    if missing_nice_to_have_exists or medium_risk_exists:
        return ReportRiskLevel.MEDIUM

    return ReportRiskLevel.LOW


def _build_warnings(
    matrix: list[EvidenceMatrixItem],
    missing_skills: list[MissingSkill],
) -> list[str]:
    warnings: list[str] = []

    if any(skill.priority is RequirementPriority.MUST_HAVE for skill in missing_skills):
        warnings.append("Missing must-have requirements exist.")

    if any(item.risk_level is ReportRiskLevel.HIGH for item in matrix):
        warnings.append("High overclaiming risk exists.")

    warnings.append(NO_FAKE_ATS_SCORE_WARNING)
    return warnings


def _build_overall_summary(
    risk_level: ReportRiskLevel,
    missing_skills: list[MissingSkill],
) -> str:
    if risk_level is ReportRiskLevel.HIGH:
        return (
            "The CV has significant gaps against the extracted job requirements and "
            "should be reviewed before tailoring or export."
        )

    if risk_level is ReportRiskLevel.MEDIUM:
        return (
            "The CV covers the main extracted requirements but has gaps or cautious "
            "evidence that should be reviewed."
        )

    if missing_skills:
        return "The CV is mostly aligned, with minor gaps to review."

    return "The CV requirements are covered by verified low-risk fact bank evidence."
