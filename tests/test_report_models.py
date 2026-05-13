import pytest
from pydantic import ValidationError

from app.llm.schemas import RequirementPriority
from app.reports.models import (
    CoverageLevel,
    CvMatchReport,
    EvidenceMatrixItem,
    KeywordCoverageItem,
    MissingSkill,
    ReportRiskLevel,
)


def build_evidence_item() -> EvidenceMatrixItem:
    return EvidenceMatrixItem(
        requirement_id="req_python",
        requirement_text="Use Python.",
        requirement_priority=RequirementPriority.MUST_HAVE,
        coverage=CoverageLevel.FULL,
        fact_ids=["fact_python_001"],
        matched_fact_names=["Python"],
        risk_level=ReportRiskLevel.LOW,
        comment="Covered by verified fact bank facts.",
    )


def build_report() -> CvMatchReport:
    return CvMatchReport(
        application_id="app-1",
        overall_summary="Requirements are covered by verified evidence.",
        must_have_total=1,
        must_have_covered=1,
        nice_to_have_total=0,
        nice_to_have_covered=0,
        keyword_coverage=[
            KeywordCoverageItem(
                keyword="Python",
                is_covered=True,
                source="Python",
            )
        ],
        missing_skills=[],
        evidence_matrix=[build_evidence_item()],
        risk_level=ReportRiskLevel.LOW,
        warnings=["  No ATS score is provided.  ", ""],
    )


def test_unknown_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        EvidenceMatrixItem.model_validate(
            {
                **build_evidence_item().model_dump(mode="json"),
                "ats_score": 99,
            }
        )


def test_blank_required_text_is_rejected() -> None:
    with pytest.raises(ValidationError):
        MissingSkill(
            requirement_id="req_python",
            requirement_text="   ",
            priority=RequirementPriority.MUST_HAVE,
            reason="No verified fact exists.",
        )


def test_blank_id_list_values_are_rejected() -> None:
    with pytest.raises(ValidationError):
        EvidenceMatrixItem(
            requirement_id="req_python",
            requirement_text="Use Python.",
            requirement_priority=RequirementPriority.MUST_HAVE,
            coverage=CoverageLevel.FULL,
            fact_ids=["fact_python_001", "  "],
            matched_fact_names=["Python"],
            risk_level=ReportRiskLevel.LOW,
            comment="Covered by verified fact bank facts.",
        )


def test_negative_counts_are_rejected() -> None:
    with pytest.raises(ValidationError):
        CvMatchReport(
            application_id="app-1",
            overall_summary="Summary.",
            must_have_total=-1,
            must_have_covered=0,
            nice_to_have_total=0,
            nice_to_have_covered=0,
            evidence_matrix=[build_evidence_item()],
            risk_level=ReportRiskLevel.LOW,
        )


def test_covered_counts_cannot_exceed_total_counts() -> None:
    with pytest.raises(ValidationError):
        CvMatchReport(
            application_id="app-1",
            overall_summary="Summary.",
            must_have_total=1,
            must_have_covered=2,
            nice_to_have_total=0,
            nice_to_have_covered=0,
            evidence_matrix=[build_evidence_item()],
            risk_level=ReportRiskLevel.LOW,
        )


def test_report_requires_evidence_matrix_item() -> None:
    with pytest.raises(ValidationError):
        CvMatchReport(
            application_id="app-1",
            overall_summary="Summary.",
            must_have_total=0,
            must_have_covered=0,
            nice_to_have_total=0,
            nice_to_have_covered=0,
            evidence_matrix=[],
            risk_level=ReportRiskLevel.LOW,
        )


def test_warnings_are_normalised() -> None:
    report = build_report()

    assert report.warnings == ["No ATS score is provided."]


def test_reports_do_not_accept_fake_ats_score_fields() -> None:
    with pytest.raises(ValidationError):
        CvMatchReport.model_validate(
            {
                **build_report().model_dump(mode="json"),
                "ats_score": 97,
            }
        )
