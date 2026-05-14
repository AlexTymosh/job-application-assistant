from pathlib import Path

from app.cv.fact_bank import load_fact_bank
from app.cv.markdown_loader import load_markdown_file
from app.cv.models import CvSectionName, FactBank, LoadedCv
from app.cv.section_parser import parse_cv_sections
from app.llm.fake_tailor import FakeCvTailoringClient
from app.llm.schemas import (
    ExtractedJob,
    JobRequirement,
    RequirementCategory,
    RequirementPriority,
)
from app.pipeline.cv_tailoring import CvTailoringStep
from app.pipeline.state import ApplicationRunState

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_VARIANT_CV = (
    ROOT / "profiles" / "example" / "cv" / "variants" / "backend_developer.example.md"
)
EXAMPLE_FACT_BANK = ROOT / "profiles" / "example" / "cv" / "fact_bank.example.yaml"


class RecordingTailoringClient(FakeCvTailoringClient):
    def __init__(self) -> None:
        self.was_called = False

    def tailor_cv(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        self.was_called = True
        return super().tailor_cv(*args, **kwargs)


def build_loaded_cv() -> LoadedCv:
    markdown = load_markdown_file(EXAMPLE_VARIANT_CV)
    return LoadedCv(
        path=EXAMPLE_VARIANT_CV,
        markdown=markdown,
        sections=parse_cv_sections(markdown),
    )


def build_fact_bank() -> FactBank:
    return load_fact_bank(EXAMPLE_FACT_BANK)


def build_extracted_job(keyword: str = "FastAPI") -> ExtractedJob:
    return ExtractedJob(
        requirements=[
            JobRequirement(
                id=f"req_{keyword.lower()}",
                text=f"Use {keyword}.",
                priority=RequirementPriority.MUST_HAVE,
                category=RequirementCategory.FRAMEWORK,
                keywords=[keyword],
            )
        ]
    )


def test_step_updates_state_with_original_and_tailored_markdown() -> None:
    loaded_cv = build_loaded_cv()
    state = ApplicationRunState(
        application_id="app-1",
        profile_name="example",
        extracted_job=build_extracted_job(),
    )

    updated = CvTailoringStep(FakeCvTailoringClient()).run(
        state,
        loaded_cv=loaded_cv,
        fact_bank=build_fact_bank(),
    )

    assert updated.original_cv_markdown == loaded_cv.markdown
    assert updated.tailored_cv_markdown is not None
    assert updated.tailored_cv_markdown != loaded_cv.markdown


def test_step_records_cv_changes() -> None:
    state = ApplicationRunState(
        application_id="app-1",
        profile_name="example",
        extracted_job=build_extracted_job(),
    )

    updated = CvTailoringStep(FakeCvTailoringClient()).run(
        state,
        loaded_cv=build_loaded_cv(),
        fact_bank=build_fact_bank(),
    )

    assert len(updated.cv_changes) == 1
    assert updated.cv_changes[0].section is CvSectionName.SUMMARY


def test_step_records_tailoring_warning_codes() -> None:
    state = ApplicationRunState(
        application_id="app-1",
        profile_name="example",
        extracted_job=build_extracted_job("Rust"),
    )

    updated = CvTailoringStep(FakeCvTailoringClient()).run(
        state,
        loaded_cv=build_loaded_cv(),
        fact_bank=build_fact_bank(),
    )

    assert updated.tailoring_warning_codes == [
        "no_relevant_requirement",
        "no_relevant_requirement",
    ]


def test_step_sets_status_to_tailored_when_safe_changes_exist() -> None:
    state = ApplicationRunState(
        application_id="app-1",
        profile_name="example",
        extracted_job=build_extracted_job(),
    )

    updated = CvTailoringStep(FakeCvTailoringClient()).run(
        state,
        loaded_cv=build_loaded_cv(),
        fact_bank=build_fact_bank(),
    )

    assert updated.status == "tailored"


def test_step_does_not_call_openai() -> None:
    client = RecordingTailoringClient()
    state = ApplicationRunState(
        application_id="app-1",
        profile_name="example",
        extracted_job=build_extracted_job(),
    )

    updated = CvTailoringStep(client).run(
        state,
        loaded_cv=build_loaded_cv(),
        fact_bank=build_fact_bank(),
    )

    assert client.was_called is True
    assert updated.status == "tailored"


def test_step_keeps_selected_variant_read_only() -> None:
    before_file_content = EXAMPLE_VARIANT_CV.read_text(encoding="utf-8")
    state = ApplicationRunState(
        application_id="app-1",
        profile_name="example",
        extracted_job=build_extracted_job(),
    )

    CvTailoringStep(FakeCvTailoringClient()).run(
        state,
        loaded_cv=build_loaded_cv(),
        fact_bank=build_fact_bank(),
    )

    after_file_content = EXAMPLE_VARIANT_CV.read_text(encoding="utf-8")
    assert before_file_content == after_file_content


def test_step_handles_no_safe_change_case_without_crashing() -> None:
    state = ApplicationRunState(
        application_id="app-1",
        profile_name="example",
        extracted_job=build_extracted_job("Rust"),
    )

    updated = CvTailoringStep(FakeCvTailoringClient()).run(
        state,
        loaded_cv=build_loaded_cv(),
        fact_bank=build_fact_bank(),
    )

    assert updated.cv_changes == []
    assert updated.status == "qa_warning"
    assert updated.tailored_cv_markdown == build_loaded_cv().markdown
