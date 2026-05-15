import pytest

from app.cv.models import CvSectionName
from app.cv.section_parser import parse_cv_sections
from tests.support.paths import PROJECT_ROOT

ROOT = PROJECT_ROOT
EXAMPLE_VARIANT_CV = (
    ROOT / "profiles" / "example" / "cv" / "variants" / "backend_developer.example.md"
)

VALID_MARKDOWN = """
Intro outside sections.

<!-- SECTION: SUMMARY_START -->
  Summary content.
<!-- SECTION: SUMMARY_END -->

<!-- SECTION: SKILLS_START -->
- Python
<!-- SECTION: SKILLS_END -->

<!-- SECTION: EXPERIENCE_START -->
Experience content.
<!-- SECTION: EXPERIENCE_END -->

<!-- SECTION: PROJECTS_START -->
Project content.
<!-- SECTION: PROJECTS_END -->

Footer outside sections.
"""


def test_parse_cv_sections_parses_example_variant_cv() -> None:
    sections = parse_cv_sections(EXAMPLE_VARIANT_CV.read_text(encoding="utf-8"))

    assert set(sections) == {
        CvSectionName.SUMMARY,
        CvSectionName.SKILLS,
        CvSectionName.EXPERIENCE,
        CvSectionName.PROJECTS,
    }
    assert sections[CvSectionName.SUMMARY].content
    assert sections[CvSectionName.SKILLS].content
    assert sections[CvSectionName.EXPERIENCE].content
    assert sections[CvSectionName.PROJECTS].content


def test_parse_cv_sections_rejects_missing_summary_marker() -> None:
    markdown = VALID_MARKDOWN.replace("<!-- SECTION: SUMMARY_START -->", "")

    with pytest.raises(ValueError, match="Missing start marker for summary"):
        parse_cv_sections(markdown)


def test_parse_cv_sections_rejects_duplicated_marker() -> None:
    markdown = VALID_MARKDOWN.replace(
        "<!-- SECTION: SKILLS_START -->",
        "<!-- SECTION: SKILLS_START -->\n<!-- SECTION: SKILLS_START -->",
    )

    with pytest.raises(ValueError, match="Duplicate start marker for skills"):
        parse_cv_sections(markdown)


def test_parse_cv_sections_rejects_marker_order_error() -> None:
    valid_experience_section = (
        "<!-- SECTION: EXPERIENCE_START -->\n"
        "Experience content.\n"
        "<!-- SECTION: EXPERIENCE_END -->"
    )
    invalid_experience_section = (
        "<!-- SECTION: EXPERIENCE_END -->\n"
        "Experience content.\n"
        "<!-- SECTION: EXPERIENCE_START -->"
    )
    markdown = VALID_MARKDOWN.replace(
        valid_experience_section,
        invalid_experience_section,
    )

    with pytest.raises(ValueError, match="Invalid marker order for experience"):
        parse_cv_sections(markdown)


def test_parse_cv_sections_rejects_empty_markdown() -> None:
    with pytest.raises(ValueError, match="empty"):
        parse_cv_sections("  \n\t  ")


def test_parse_cv_sections_strips_section_content_edges() -> None:
    sections = parse_cv_sections(VALID_MARKDOWN)

    assert sections[CvSectionName.SUMMARY].content == "Summary content."


def test_parse_cv_sections_does_not_require_content_outside_section_markers() -> None:
    markdown = """
<!-- SECTION: SUMMARY_START -->
Summary content.
<!-- SECTION: SUMMARY_END -->
<!-- SECTION: SKILLS_START -->
Skills content.
<!-- SECTION: SKILLS_END -->
<!-- SECTION: EXPERIENCE_START -->
Experience content.
<!-- SECTION: EXPERIENCE_END -->
<!-- SECTION: PROJECTS_START -->
Projects content.
<!-- SECTION: PROJECTS_END -->
"""

    sections = parse_cv_sections(markdown)

    assert sections[CvSectionName.PROJECTS].content == "Projects content."
