from pathlib import Path

import pytest

from app.cv.selector import select_cv_variant, select_default_cv_variant
from tests.support.paths import PROJECT_ROOT

ROOT = PROJECT_ROOT
EXAMPLE_CV_DIR = ROOT / "profiles" / "example" / "cv"

VALID_VARIANT = """
<!-- SECTION: SUMMARY_START -->
Summary.
<!-- SECTION: SUMMARY_END -->
<!-- SECTION: SKILLS_START -->
Skills.
<!-- SECTION: SKILLS_END -->
<!-- SECTION: EXPERIENCE_START -->
Experience.
<!-- SECTION: EXPERIENCE_END -->
<!-- SECTION: PROJECTS_START -->
Projects.
<!-- SECTION: PROJECTS_END -->
"""


def test_select_cv_variant_selects_backend_developer_example_variant() -> None:
    selected = select_cv_variant(
        cv_dir=EXAMPLE_CV_DIR,
        variant_name="backend_developer",
        is_example_profile=True,
    )

    assert selected.variant_name == "backend_developer"
    assert selected.path == EXAMPLE_CV_DIR / "variants" / "backend_developer.example.md"
    assert "Backend Developer CV Variant" in selected.markdown


def test_select_cv_variant_rejects_missing_variant(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        select_cv_variant(cv_dir=tmp_path, variant_name="missing")


def test_select_cv_variant_rejects_blank_variant_name() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        select_cv_variant(cv_dir=EXAMPLE_CV_DIR, variant_name="  ")


def test_select_default_cv_variant_accepts_configured_default_variant() -> None:
    selected = select_default_cv_variant(
        cv_dir=EXAMPLE_CV_DIR,
        default_variant="backend_developer",
        available_variants=["backend_developer", "software_engineer"],
        is_example_profile=True,
    )

    assert selected.variant_name == "backend_developer"


def test_select_default_cv_variant_rejects_default_variant_not_listed() -> None:
    with pytest.raises(ValueError, match="not listed"):
        select_default_cv_variant(
            cv_dir=EXAMPLE_CV_DIR,
            default_variant="backend_developer",
            available_variants=["software_engineer"],
            is_example_profile=True,
        )


def test_select_cv_variant_validates_selected_variant_through_section_parsing(
    tmp_path: Path,
) -> None:
    variants_dir = tmp_path / "variants"
    variants_dir.mkdir()
    (variants_dir / "broken.md").write_text(
        VALID_VARIANT.replace("<!-- SECTION: PROJECTS_END -->", ""),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Missing end marker for projects"):
        select_cv_variant(cv_dir=tmp_path, variant_name="broken")
