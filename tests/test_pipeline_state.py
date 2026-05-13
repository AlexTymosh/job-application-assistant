from app.llm.schemas import (
    ExtractedJob,
    JobRequirement,
    RequirementCategory,
    RequirementPriority,
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
