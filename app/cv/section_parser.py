from __future__ import annotations

from app.cv.models import CvSection, CvSectionName

REQUIRED_SECTION_MARKERS: dict[CvSectionName, tuple[str, str]] = {
    CvSectionName.SUMMARY: (
        "<!-- SECTION: SUMMARY_START -->",
        "<!-- SECTION: SUMMARY_END -->",
    ),
    CvSectionName.SKILLS: (
        "<!-- SECTION: SKILLS_START -->",
        "<!-- SECTION: SKILLS_END -->",
    ),
    CvSectionName.EXPERIENCE: (
        "<!-- SECTION: EXPERIENCE_START -->",
        "<!-- SECTION: EXPERIENCE_END -->",
    ),
    CvSectionName.PROJECTS: (
        "<!-- SECTION: PROJECTS_START -->",
        "<!-- SECTION: PROJECTS_END -->",
    ),
}


def parse_cv_sections(markdown: str) -> dict[CvSectionName, CvSection]:
    """Parse and validate all required Markdown CV section markers."""
    if not markdown.strip():
        raise ValueError("Markdown CV content is empty or whitespace-only.")

    sections: dict[CvSectionName, CvSection] = {}

    for section_name, (start_marker, end_marker) in REQUIRED_SECTION_MARKERS.items():
        _validate_marker_count(markdown, start_marker, section_name, "start")
        _validate_marker_count(markdown, end_marker, section_name, "end")

        start_index = markdown.index(start_marker)
        end_index = markdown.index(end_marker)

        if start_index > end_index:
            raise ValueError(
                f"Invalid marker order for {section_name.value}: "
                "start marker must appear before end marker."
            )

        content_start = start_index + len(start_marker)
        content = markdown[content_start:end_index].strip()
        sections[section_name] = CvSection(
            name=section_name,
            start_marker=start_marker,
            end_marker=end_marker,
            content=content,
        )

    return sections


def _validate_marker_count(
    markdown: str,
    marker: str,
    section_name: CvSectionName,
    marker_role: str,
) -> None:
    count = markdown.count(marker)

    if count == 0:
        raise ValueError(
            f"Missing {marker_role} marker for {section_name.value}: {marker}"
        )

    if count > 1:
        raise ValueError(
            f"Duplicate {marker_role} marker for {section_name.value}: {marker}"
        )
