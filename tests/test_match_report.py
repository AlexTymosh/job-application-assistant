from app.cv.models import AllowedClaimLevel, Fact, FactBank, FactCategory
from app.llm.schemas import (
    ExtractedJob,
    JobRequirement,
    RequirementCategory,
    RequirementPriority,
)
from app.reports.match_report import NO_FAKE_ATS_SCORE_WARNING, build_cv_match_report
from app.reports.models import ReportRiskLevel


def build_requirement(
    requirement_id: str,
    text: str,
    keywords: list[str],
    priority: RequirementPriority,
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
    claim_level: AllowedClaimLevel = AllowedClaimLevel.STRONG,
) -> Fact:
    return Fact(
        id=fact_id,
        category=FactCategory.SKILL,
        name=name,
        allowed_claim_level=claim_level,
        evidence=f"Verified evidence for {name}.",
    )


def build_fact_bank(*facts: Fact) -> FactBank:
    return FactBank(facts=list(facts))


def test_coverage_counts_are_correct() -> None:
    report = build_cv_match_report(
        application_id="app-1",
        extracted_job=ExtractedJob(
            requirements=[
                build_requirement(
                    "req_python",
                    "Use Python.",
                    ["Python"],
                    RequirementPriority.MUST_HAVE,
                ),
                build_requirement(
                    "req_fastapi",
                    "Use FastAPI.",
                    ["FastAPI"],
                    RequirementPriority.NICE_TO_HAVE,
                ),
                build_requirement(
                    "req_kubernetes",
                    "Use Kubernetes.",
                    ["Kubernetes"],
                    RequirementPriority.NICE_TO_HAVE,
                ),
            ]
        ),
        fact_bank=build_fact_bank(
            build_fact("fact_python_001", "Python"),
            build_fact("fact_fastapi_001", "FastAPI"),
        ),
    )

    assert report.must_have_total == 1
    assert report.must_have_covered == 1
    assert report.nice_to_have_total == 2
    assert report.nice_to_have_covered == 1


def test_missing_skills_are_listed() -> None:
    report = build_cv_match_report(
        application_id="app-1",
        extracted_job=ExtractedJob(
            requirements=[
                build_requirement(
                    "req_kubernetes",
                    "Use Kubernetes.",
                    ["Kubernetes"],
                    RequirementPriority.MUST_HAVE,
                )
            ]
        ),
        fact_bank=build_fact_bank(build_fact("fact_python_001", "Python")),
    )

    assert [skill.requirement_id for skill in report.missing_skills] == [
        "req_kubernetes"
    ]


def test_overall_risk_is_high_when_must_have_requirement_is_missing() -> None:
    report = build_cv_match_report(
        application_id="app-1",
        extracted_job=ExtractedJob(
            requirements=[
                build_requirement(
                    "req_kubernetes",
                    "Use Kubernetes.",
                    ["Kubernetes"],
                    RequirementPriority.MUST_HAVE,
                )
            ]
        ),
        fact_bank=build_fact_bank(build_fact("fact_python_001", "Python")),
    )

    assert report.risk_level is ReportRiskLevel.HIGH
    assert "Missing must-have requirements exist." in report.warnings
    assert "High overclaiming risk exists." in report.warnings


def test_overall_risk_is_medium_when_only_nice_to_have_items_are_missing() -> None:
    report = build_cv_match_report(
        application_id="app-1",
        extracted_job=ExtractedJob(
            requirements=[
                build_requirement(
                    "req_python",
                    "Use Python.",
                    ["Python"],
                    RequirementPriority.MUST_HAVE,
                ),
                build_requirement(
                    "req_kubernetes",
                    "Use Kubernetes.",
                    ["Kubernetes"],
                    RequirementPriority.NICE_TO_HAVE,
                ),
            ]
        ),
        fact_bank=build_fact_bank(build_fact("fact_python_001", "Python")),
    )

    assert report.risk_level is ReportRiskLevel.MEDIUM


def test_overall_risk_is_low_when_all_requirements_have_low_risk_facts() -> None:
    report = build_cv_match_report(
        application_id="app-1",
        extracted_job=ExtractedJob(
            requirements=[
                build_requirement(
                    "req_python",
                    "Use Python.",
                    ["Python"],
                    RequirementPriority.MUST_HAVE,
                ),
                build_requirement(
                    "req_fastapi",
                    "Use FastAPI.",
                    ["FastAPI"],
                    RequirementPriority.NICE_TO_HAVE,
                ),
            ]
        ),
        fact_bank=build_fact_bank(
            build_fact("fact_python_001", "Python"),
            build_fact("fact_fastapi_001", "FastAPI"),
        ),
    )

    assert report.risk_level is ReportRiskLevel.LOW


def test_keyword_coverage_is_deterministic() -> None:
    report = build_cv_match_report(
        application_id="app-1",
        extracted_job=ExtractedJob(
            requirements=[
                build_requirement(
                    "req_python",
                    "Use Python.",
                    [" Python ", "python", "FastAPI"],
                    RequirementPriority.MUST_HAVE,
                ),
                build_requirement(
                    "req_kubernetes",
                    "Use Kubernetes.",
                    ["Kubernetes"],
                    RequirementPriority.NICE_TO_HAVE,
                ),
            ]
        ),
        fact_bank=build_fact_bank(build_fact("fact_python_001", "Python")),
    )

    assert [item.keyword for item in report.keyword_coverage] == [
        "Python",
        "FastAPI",
        "Kubernetes",
    ]
    assert [item.is_covered for item in report.keyword_coverage] == [
        True,
        False,
        False,
    ]


def test_warnings_include_no_fake_ats_score_message() -> None:
    report = build_cv_match_report(
        application_id="app-1",
        extracted_job=ExtractedJob(
            requirements=[
                build_requirement(
                    "req_python",
                    "Use Python.",
                    ["Python"],
                    RequirementPriority.MUST_HAVE,
                )
            ]
        ),
        fact_bank=build_fact_bank(build_fact("fact_python_001", "Python")),
    )

    assert NO_FAKE_ATS_SCORE_WARNING in report.warnings
    assert "ats_score" not in report.model_dump(mode="json")


def test_report_builder_does_not_require_openai_or_network_calls() -> None:
    report = build_cv_match_report(
        application_id="app-1",
        extracted_job=ExtractedJob(
            requirements=[
                build_requirement(
                    "req_python",
                    "Use Python.",
                    ["Python"],
                    RequirementPriority.MUST_HAVE,
                )
            ]
        ),
        fact_bank=build_fact_bank(build_fact("fact_python_001", "Python")),
    )

    assert report.evidence_matrix[0].fact_ids == ["fact_python_001"]
