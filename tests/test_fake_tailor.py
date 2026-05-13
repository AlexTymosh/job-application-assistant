from pathlib import Path

from app.cv.fact_bank import load_fact_bank
from app.cv.markdown_loader import load_markdown_file
from app.cv.models import (
    AllowedClaimLevel,
    CvSectionName,
    Fact,
    FactBank,
    FactCategory,
    LoadedCv,
)
from app.cv.section_parser import parse_cv_sections
from app.llm.fake_tailor import FakeCvTailoringClient
from app.llm.schemas import (
    ExtractedJob,
    JobRequirement,
    RequirementCategory,
    RequirementPriority,
)

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_MASTER_CV = ROOT / "profiles" / "example" / "cv" / "master.example.md"
EXAMPLE_FACT_BANK = ROOT / "profiles" / "example" / "cv" / "fact_bank.example.yaml"


def build_requirement(
    requirement_id: str,
    text: str,
    keywords: list[str],
) -> JobRequirement:
    return JobRequirement(
        id=requirement_id,
        text=text,
        priority=RequirementPriority.MUST_HAVE,
        category=RequirementCategory.FRAMEWORK,
        keywords=keywords,
    )


def build_loaded_cv() -> LoadedCv:
    markdown = load_markdown_file(EXAMPLE_MASTER_CV)
    return LoadedCv(
        path=EXAMPLE_MASTER_CV,
        markdown=markdown,
        sections=parse_cv_sections(markdown),
    )


def tailor(extracted_job: ExtractedJob, fact_bank: FactBank | None = None):
    loaded_cv = build_loaded_cv()
    return FakeCvTailoringClient().tailor_cv(
        original_markdown=loaded_cv.markdown,
        extracted_job=extracted_job,
        fact_bank=fact_bank or load_fact_bank(EXAMPLE_FACT_BANK),
        allowed_sections=loaded_cv.sections,
    )


def test_fake_tailor_creates_safe_summary_change_for_verified_fact_match() -> None:
    result = tailor(
        ExtractedJob(
            requirements=[
                build_requirement(
                    "req_fastapi",
                    "Build backend services with FastAPI.",
                    ["FastAPI"],
                )
            ]
        )
    )

    assert len(result.changes) == 1
    change = result.changes[0]
    assert change.section is CvSectionName.SUMMARY
    assert change.cv_fact_ids == ["fact_fastapi_001"]
    assert "FastAPI" in change.after_text
    assert result.tailored_markdown != build_loaded_cv().markdown


def test_fake_tailor_does_not_mention_unmatched_technologies() -> None:
    result = tailor(
        ExtractedJob(
            requirements=[
                build_requirement("req_fastapi", "Use FastAPI.", ["FastAPI"]),
                build_requirement("req_kubernetes", "Use Kubernetes.", ["Kubernetes"]),
            ]
        )
    )

    assert "FastAPI" in result.changes[0].after_text
    assert "Kubernetes" not in result.changes[0].after_text


def test_fake_tailor_creates_warnings_for_unmatched_requirements() -> None:
    result = tailor(
        ExtractedJob(
            requirements=[
                build_requirement("req_fastapi", "Use FastAPI.", ["FastAPI"]),
                build_requirement("req_rust", "Use Rust.", ["Rust"]),
            ]
        )
    )

    assert [warning.code.value for warning in result.warnings] == [
        "no_relevant_requirement"
    ]
    assert "req_rust" in result.warnings[0].message


def test_fake_tailor_returns_unchanged_markdown_when_no_safe_fact_match_exists() -> (
    None
):
    loaded_cv = build_loaded_cv()
    result = tailor(
        ExtractedJob(
            requirements=[build_requirement("req_rust", "Use Rust.", ["Rust"])]
        )
    )

    assert result.tailored_markdown == loaded_cv.markdown
    assert result.changes == []
    assert result.warnings


def test_fake_tailor_ignores_do_not_claim_facts() -> None:
    fact_bank = FactBank(
        facts=[
            Fact(
                id="fact_rust_001",
                category=FactCategory.SKILL,
                name="Rust",
                allowed_claim_level=AllowedClaimLevel.DO_NOT_CLAIM,
                evidence="Read introductory material only.",
            )
        ]
    )

    result = tailor(
        ExtractedJob(
            requirements=[build_requirement("req_rust", "Use Rust.", ["Rust"])]
        ),
        fact_bank=fact_bank,
    )

    assert result.changes == []
    assert result.warnings
    assert result.tailored_markdown == build_loaded_cv().markdown


def test_fake_tailor_does_not_modify_master_file_and_uses_in_memory_strings() -> None:
    before_file_content = EXAMPLE_MASTER_CV.read_text(encoding="utf-8")

    result = tailor(
        ExtractedJob(
            requirements=[build_requirement("req_python", "Use Python.", ["Python"])]
        )
    )

    after_file_content = EXAMPLE_MASTER_CV.read_text(encoding="utf-8")
    assert before_file_content == after_file_content
    assert result.tailored_markdown != after_file_content
