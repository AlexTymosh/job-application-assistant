from __future__ import annotations

from pathlib import Path

from app.core.config import ProjectConfig
from app.cv.markdown_loader import load_markdown_file
from app.cv.models import CvSectionName
from app.cv.section_parser import parse_cv_sections
from app.import_tools.models import PlannedCvBlock, PlannedCvSection, PlannedCvVariant

_IMPORTED_BLOCK_KEY = "imported_content"
_REQUIRED_SECTION_KEYS = {section.value for section in CvSectionName}


class LoadedMarkdownVariant:
    def __init__(
        self,
        *,
        name: str,
        display_name: str,
        source_path: Path,
        sections: list[PlannedCvSection],
    ) -> None:
        self.name = name
        self.display_name = display_name
        self.source_path = source_path
        self.sections = sections


def load_markdown_variants(
    profile_dir: Path, config: ProjectConfig
) -> list[LoadedMarkdownVariant]:
    variants_dir = profile_dir / "cv" / "variants"
    discovered_paths = _discover_variant_paths(variants_dir, config.cv.variants)
    loaded_variants: list[LoadedMarkdownVariant] = []
    for source_path in discovered_paths:
        variant_name = _variant_name_from_path(source_path)
        markdown = load_markdown_file(source_path)
        parsed_sections = parse_cv_sections(markdown)
        planned_sections = [
            PlannedCvSection(
                section_key=section_name.value,
                title=_section_title(section_name),
                display_order=display_order,
                is_required=section_name.value in _REQUIRED_SECTION_KEYS,
                action="create",
                blocks=[
                    PlannedCvBlock(
                        block_key=_IMPORTED_BLOCK_KEY,
                        content_markdown=section.content,
                        display_order=0,
                        is_enabled=True,
                        action="create",
                    )
                ],
            )
            for display_order, (section_name, section) in enumerate(
                parsed_sections.items()
            )
        ]
        loaded_variants.append(
            LoadedMarkdownVariant(
                name=variant_name,
                display_name=_display_name_from_variant_name(variant_name),
                source_path=source_path,
                sections=planned_sections,
            )
        )
    return loaded_variants


def planned_variant_from_loaded(loaded: LoadedMarkdownVariant) -> PlannedCvVariant:
    return PlannedCvVariant(
        name=loaded.name,
        display_name=loaded.display_name,
        source_filename=loaded.source_path.name,
        action="create",
        sections=loaded.sections,
    )


def _discover_variant_paths(
    variants_dir: Path, configured_variants: list[str]
) -> list[Path]:
    if not variants_dir.is_dir():
        raise FileNotFoundError(f"CV variants folder not found: {variants_dir}")

    paths_by_name = {
        _variant_name_from_path(path): path for path in variants_dir.glob("*.md")
    }
    ordered_names: list[str] = []
    for configured_name in configured_variants:
        cleaned_name = configured_name.strip()
        if cleaned_name and cleaned_name not in ordered_names:
            ordered_names.append(cleaned_name)
    for name in sorted(paths_by_name):
        if name not in ordered_names:
            ordered_names.append(name)

    if not ordered_names:
        raise ValueError(f"No Markdown CV variant files found in {variants_dir}")

    missing = [name for name in ordered_names if name not in paths_by_name]
    if missing:
        raise FileNotFoundError(
            "Configured Markdown CV variant files were not found: " + ", ".join(missing)
        )

    return [paths_by_name[name] for name in ordered_names]


def _variant_name_from_path(path: Path) -> str:
    filename = path.name
    if filename.endswith(".example.md"):
        return filename.removesuffix(".example.md")
    if filename.endswith(".md"):
        return filename.removesuffix(".md")
    raise ValueError(f"Unsupported CV variant file extension: {filename}")


def _display_name_from_variant_name(variant_name: str) -> str:
    return variant_name.replace("_", " ").replace("-", " ").title()


def _section_title(section_name: CvSectionName) -> str:
    return section_name.value.replace("_", " ").title()
