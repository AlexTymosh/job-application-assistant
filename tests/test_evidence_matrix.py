from app.cv.models import AllowedClaimLevel, Fact, FactBank, FactCategory
from app.llm.schemas import (
    ExtractedJob,
    JobRequirement,
    RequirementCategory,
    RequirementPriority,
)
from app.reports.evidence_matrix import build_evidence_matrix
from app.reports.models import CoverageLevel, ReportRiskLevel


def build_requirement(
    requirement_id: str,
    text: str,
    keywords: list[str],
    priority: RequirementPriority = RequirementPriority.MUST_HAVE,
) -> JobRequirement:
    return JobRequirement(
        id=requirement_id,
        text=text,
        priority=priority,
        category=RequirementCategory.FRAMEWORK,
        keywords=keywords,
    )


def build_fact(
    fact_id: str,
    name: str,
    claim_level: AllowedClaimLevel,
) -> Fact:
    return Fact(
        id=fact_id,
        category=FactCategory.SKILL,
        name=name,
        allowed_claim_level=claim_level,
        evidence=f"Verified evidence for {name}.",
    )


def test_claimable_fact_gives_full_coverage() -> None:
    matrix = build_evidence_matrix(
        ExtractedJob(
            requirements=[build_requirement("req_fastapi", "Use FastAPI.", [])]
        ),
        FactBank(
            facts=[
                build_fact("fact_fastapi_001", "FastAPI", AllowedClaimLevel.PRACTICAL)
            ]
        ),
    )

    assert matrix[0].coverage is CoverageLevel.FULL
    assert matrix[0].fact_ids == ["fact_fastapi_001"]
    assert matrix[0].matched_fact_names == ["FastAPI"]
    assert matrix[0].risk_level is ReportRiskLevel.LOW


def test_mention_only_fact_gives_medium_risk() -> None:
    matrix = build_evidence_matrix(
        ExtractedJob(requirements=[build_requirement("req_rag", "Use RAG.", ["RAG"])]),
        FactBank(
            facts=[build_fact("fact_rag_001", "RAG", AllowedClaimLevel.MENTION_ONLY)]
        ),
    )

    assert matrix[0].coverage is CoverageLevel.FULL
    assert matrix[0].risk_level is ReportRiskLevel.MEDIUM


def test_do_not_claim_fact_does_not_create_evidence_claim() -> None:
    matrix = build_evidence_matrix(
        ExtractedJob(
            requirements=[build_requirement("req_rust", "Use Rust.", ["Rust"])]
        ),
        FactBank(
            facts=[build_fact("fact_rust_001", "Rust", AllowedClaimLevel.DO_NOT_CLAIM)]
        ),
    )

    assert matrix[0].coverage is CoverageLevel.MISSING
    assert matrix[0].fact_ids == []
    assert matrix[0].matched_fact_names == ["Rust"]
    assert matrix[0].risk_level is ReportRiskLevel.HIGH


def test_missing_must_have_requirement_gives_high_risk() -> None:
    matrix = build_evidence_matrix(
        ExtractedJob(
            requirements=[build_requirement("req_kubernetes", "Use Kubernetes.", [])]
        ),
        FactBank(
            facts=[build_fact("fact_python_001", "Python", AllowedClaimLevel.STRONG)]
        ),
    )

    assert matrix[0].coverage is CoverageLevel.MISSING
    assert matrix[0].risk_level is ReportRiskLevel.HIGH


def test_missing_nice_to_have_requirement_gives_medium_risk() -> None:
    matrix = build_evidence_matrix(
        ExtractedJob(
            requirements=[
                build_requirement(
                    "req_kubernetes",
                    "Use Kubernetes.",
                    [],
                    RequirementPriority.NICE_TO_HAVE,
                )
            ]
        ),
        FactBank(
            facts=[build_fact("fact_python_001", "Python", AllowedClaimLevel.STRONG)]
        ),
    )

    assert matrix[0].coverage is CoverageLevel.MISSING
    assert matrix[0].risk_level is ReportRiskLevel.MEDIUM


def test_each_requirement_produces_one_evidence_item() -> None:
    matrix = build_evidence_matrix(
        ExtractedJob(
            requirements=[
                build_requirement("req_python", "Use Python.", ["Python"]),
                build_requirement("req_fastapi", "Use FastAPI.", ["FastAPI"]),
            ]
        ),
        FactBank(
            facts=[
                build_fact("fact_python_001", "Python", AllowedClaimLevel.STRONG),
                build_fact("fact_fastapi_001", "FastAPI", AllowedClaimLevel.PRACTICAL),
            ]
        ),
    )

    assert [item.requirement_id for item in matrix] == ["req_python", "req_fastapi"]


def test_fact_ids_are_preserved_only_for_claimable_facts() -> None:
    matrix = build_evidence_matrix(
        ExtractedJob(
            requirements=[build_requirement("req_python", "Use Python.", ["Python"])]
        ),
        FactBank(
            facts=[
                build_fact("fact_python_001", "Python", AllowedClaimLevel.DO_NOT_CLAIM),
                build_fact("fact_python_002", "Python", AllowedClaimLevel.STRONG),
            ]
        ),
    )

    assert matrix[0].coverage is CoverageLevel.FULL
    assert matrix[0].fact_ids == ["fact_python_002"]
    assert matrix[0].matched_fact_names == ["Python"]


def test_unknown_priority_practical_match_is_medium_risk() -> None:
    matrix = build_evidence_matrix(
        ExtractedJob(
            requirements=[
                build_requirement(
                    "req_python",
                    "Use Python.",
                    ["Python"],
                    RequirementPriority.UNKNOWN,
                )
            ]
        ),
        FactBank(
            facts=[build_fact("fact_python_001", "Python", AllowedClaimLevel.PRACTICAL)]
        ),
    )

    assert matrix[0].coverage is CoverageLevel.FULL
    assert matrix[0].risk_level is ReportRiskLevel.MEDIUM
