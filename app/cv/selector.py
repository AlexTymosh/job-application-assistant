from __future__ import annotations

from pathlib import Path

from app.cv.markdown_loader import load_markdown_file
from app.cv.models import SelectedCvVariant
from app.cv.section_parser import parse_cv_sections


def select_cv_variant(
    *,
    cv_dir: Path,
    variant_name: str,
    is_example_profile: bool = False,
) -> SelectedCvVariant:
    """Select and validate a CV variant without modifying the source file."""
    cleaned_variant_name = variant_name.strip()
    if not cleaned_variant_name:
        raise ValueError("CV variant name must not be empty or whitespace-only.")

    suffix = ".example.md" if is_example_profile else ".md"
    variant_path = cv_dir / "variants" / f"{cleaned_variant_name}{suffix}"

    markdown = load_markdown_file(variant_path)
    parse_cv_sections(markdown)

    return SelectedCvVariant(
        variant_name=cleaned_variant_name,
        path=variant_path,
        markdown=markdown,
    )


def select_default_cv_variant(
    *,
    cv_dir: Path,
    default_variant: str,
    available_variants: list[str],
    is_example_profile: bool = False,
) -> SelectedCvVariant:
    """Select the configured default CV variant after validating configuration."""
    if default_variant not in available_variants:
        raise ValueError(
            f"Default CV variant '{default_variant}' is not listed in "
            "available variants."
        )

    return select_cv_variant(
        cv_dir=cv_dir,
        variant_name=default_variant,
        is_example_profile=is_example_profile,
    )
