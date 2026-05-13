from app.cv.models import CvSectionName
from app.llm.schemas import (
    ExtractedJob,
    JobRequirement,
    RequirementCategory,
    RequirementPriority,
)
from app.llm.tailoring_schemas import (
    CvChange,
    TailoringAction,
    TailoringRiskLevel,
)
from app.pipeline.state import ApplicationRunState


def build_extracted_job() -> ExtractedJob:
    return ExtractedJob(
        requirements=[
            JobRequirement(
                id="req_python",
                text="Work with Python.",
                priority=RequirementPriority.MUST_HAVE,
                category=RequirementCategory.PROGRAMMING_LANGUAGE,
                keywords=["Python"],
            )
        ],
        technologies=["Python"],
    )


def test_application_run_state_can_be_created() -> None:
    state = ApplicationRunState(
        application_id="app-1",
        profile_name="example",
        manual_job_text="Backend role with Python.",
    )

    assert state.application_id == "app-1"
    assert state.profile_name == "example"


def test_default_status_is_draft() -> None:
    state = ApplicationRunState(application_id="app-1", profile_name="example")

    assert state.status == "draft"


def test_state_is_json_serialisable_without_sqlalchemy_objects() -> None:
    state = ApplicationRunState(
        application_id="app-1",
        profile_name="example",
        warning_codes=["prompt_injection_risk"],
        artifact_paths=["applications/app-1/job_raw.txt"],
    )

    dumped = state.model_dump(mode="json")

    assert dumped["application_id"] == "app-1"
    assert dumped["warning_codes"] == ["prompt_injection_risk"]
    assert dumped["artifact_paths"] == ["applications/app-1/job_raw.txt"]


def test_extracted_job_can_be_embedded_and_serialised() -> None:
    state = ApplicationRunState(
        application_id="app-1",
        profile_name="example",
        extracted_job=build_extracted_job(),
    )

    dumped = state.model_dump(mode="json")

    assert dumped["extracted_job"]["requirements"][0]["id"] == "req_python"
    assert dumped["extracted_job"]["technologies"] == ["Python"]


def test_tailoring_fields_are_serialisable_and_deserialisable() -> None:
    change = CvChange(
        section=CvSectionName.SUMMARY,
        action=TailoringAction.REPLACE_SECTION,
        before_text="Original summary.",
        after_text="Tailored summary.",
        reason="Matched verified facts.",
        job_requirement_ids=["req_python"],
        cv_fact_ids=["fact_python_001"],
        risk_level=TailoringRiskLevel.LOW,
    )
    state = ApplicationRunState(
        application_id="app-1",
        profile_name="example",
        original_cv_markdown="Original Markdown",
        tailored_cv_markdown="Tailored Markdown",
        cv_changes=[change],
        tailoring_warning_codes=["no_relevant_requirement"],
    )

    dumped = state.model_dump(mode="json")
    restored = ApplicationRunState.model_validate(dumped)

    assert dumped["cv_changes"][0]["section"] == "summary"
    assert dumped["cv_changes"][0]["risk_level"] == "low"
    assert restored.cv_changes[0].cv_fact_ids == ["fact_python_001"]
    assert restored.tailoring_warning_codes == ["no_relevant_requirement"]


def test_report_fields_are_serialisable_and_deserialisable() -> None:
    from app.reports.models import (
        CoverageLevel,
        CvMatchReport,
        EvidenceMatrixItem,
        ReportRiskLevel,
    )

    evidence_item = EvidenceMatrixItem(
        requirement_id="req_python",
        requirement_text="Work with Python.",
        requirement_priority=RequirementPriority.MUST_HAVE,
        coverage=CoverageLevel.FULL,
        fact_ids=["fact_python_001"],
        matched_fact_names=["Python"],
        risk_level=ReportRiskLevel.LOW,
        comment="Covered by verified fact bank facts.",
    )
    report = CvMatchReport(
        application_id="app-1",
        overall_summary="Requirements are covered by verified evidence.",
        must_have_total=1,
        must_have_covered=1,
        nice_to_have_total=0,
        nice_to_have_covered=0,
        evidence_matrix=[evidence_item],
        risk_level=ReportRiskLevel.LOW,
        warnings=["No ATS score is provided."],
    )
    state = ApplicationRunState(
        application_id="app-1",
        profile_name="example",
        evidence_matrix=[evidence_item],
        match_report=report,
    )

    dumped = state.model_dump(mode="json")
    restored = ApplicationRunState.model_validate(dumped)

    assert dumped["evidence_matrix"][0]["coverage"] == "full"
    assert dumped["match_report"]["risk_level"] == "low"
    assert restored.match_report is not None
    assert restored.match_report.evidence_matrix[0].fact_ids == ["fact_python_001"]
