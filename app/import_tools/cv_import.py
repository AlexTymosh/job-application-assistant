from __future__ import annotations

from collections import defaultdict
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
    is_example_profile = config.app.profile_name == "example"
    discovered_paths = _discover_variant_paths(
        variants_dir,
        config.cv.variants,
        is_example_profile=is_example_profile,
    )
    loaded_variants: list[LoadedMarkdownVariant] = []
    for source_path in discovered_paths:
        variant_name = _variant_name_from_path(source_path)
        markdown = load_markdown_file(source_path)
        parsed_sections = parse_cv_sections(markdown)
        planned_sections = [
            _planned_section_from_parsed(
                variant_name=variant_name,
                section_name=section_name,
                content=section.content,
                display_order=display_order,
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


def _planned_section_from_parsed(
    *,
    variant_name: str,
    section_name: CvSectionName,
    content: str,
    display_order: int,
) -> PlannedCvSection:
    if not content.strip():
        raise ValueError(
            f"CV variant {variant_name!r} has empty required section "
            f"{section_name.value!r}. Add content between the section markers "
            "before importing."
        )
    return PlannedCvSection(
        section_key=section_name.value,
        title=_section_title(section_name),
        display_order=display_order,
        is_required=section_name.value in _REQUIRED_SECTION_KEYS,
        action="create",
        blocks=[
            PlannedCvBlock(
                block_key=_IMPORTED_BLOCK_KEY,
                content_markdown=content,
                display_order=0,
                is_enabled=True,
                action="create",
            )
        ],
    )


def _discover_variant_paths(
    variants_dir: Path,
    configured_variants: list[str],
    *,
    is_example_profile: bool,
) -> list[Path]:
    if not variants_dir.is_dir():
        raise FileNotFoundError(
            "CV variants folder was not found in the connected profile folder."
        )

    all_paths = sorted(variants_dir.glob("*.md"), key=lambda path: path.name)
    configured_names = _ordered_configured_variant_names(configured_variants)
    if is_example_profile:
        source_paths = [path for path in all_paths if _is_example_variant_file(path)]
    else:
        _reject_unsafe_non_example_sources(all_paths, configured_names)
        source_paths = [
            path for path in all_paths if not _is_example_variant_file(path)
        ]

    paths_by_name = _unique_paths_by_variant_name(source_paths)
    ordered_names = [name for name in configured_names if name in paths_by_name]
    for name in sorted(paths_by_name):
        if name not in ordered_names:
            ordered_names.append(name)

    if not ordered_names:
        profile_label = "example" if is_example_profile else "non-example"
        raise ValueError(
            f"No Markdown CV variant files found for {profile_label} profile import."
        )

    missing = [name for name in configured_names if name not in paths_by_name]
    if missing:
        raise FileNotFoundError(
            "Configured Markdown CV variant files were not found: " + ", ".join(missing)
        )

    return [paths_by_name[name] for name in ordered_names]


def _ordered_configured_variant_names(configured_variants: list[str]) -> list[str]:
    ordered_names: list[str] = []
    for configured_name in configured_variants:
        cleaned_name = configured_name.strip()
        if cleaned_name and cleaned_name not in ordered_names:
            ordered_names.append(cleaned_name)
    return ordered_names


def _reject_unsafe_non_example_sources(
    all_paths: list[Path], configured_names: list[str]
) -> None:
    real_names = {
        _variant_name_from_path(path)
        for path in all_paths
        if not _is_example_variant_file(path)
    }
    example_names = {
        _variant_name_from_path(path)
        for path in all_paths
        if _is_example_variant_file(path)
    }
    collisions = sorted(real_names & example_names)
    if collisions:
        raise ValueError(
            "Ambiguous CV variant source files for non-example profile import: "
            + ", ".join(f"{name}.md and {name}.example.md" for name in collisions)
            + ". Remove or rename the example file before importing."
        )

    configured_example_only = sorted(
        (set(configured_names) & example_names) - real_names
    )
    if configured_example_only:
        raise ValueError(
            "Configured CV variants point to example-only source files for a "
            "non-example profile: "
            + ", ".join(
                f"{name}.example.md; expected {name}.md"
                for name in configured_example_only
            )
            + "."
        )


def _unique_paths_by_variant_name(paths: list[Path]) -> dict[str, Path]:
    grouped_paths: dict[str, list[Path]] = defaultdict(list)
    for path in paths:
        grouped_paths[_variant_name_from_path(path)].append(path)

    duplicates = {
        name: duplicate_paths
        for name, duplicate_paths in grouped_paths.items()
        if len(duplicate_paths) > 1
    }
    if duplicates:
        details = ", ".join(
            f"{name}: " + ", ".join(path.name for path in duplicate_paths)
            for name, duplicate_paths in sorted(duplicates.items())
        )
        raise ValueError(
            "Duplicate CV variant source files resolve to the same variant name: "
            f"{details}."
        )

    return {name: duplicate_paths[0] for name, duplicate_paths in grouped_paths.items()}


def _variant_name_from_path(path: Path) -> str:
    filename = path.name
    if filename.endswith(".example.md"):
        return filename.removesuffix(".example.md")
    if filename.endswith(".md"):
        return filename.removesuffix(".md")
    raise ValueError(f"Unsupported CV variant file extension: {filename}")


def _is_example_variant_file(path: Path) -> bool:
    return path.name.endswith(".example.md")


def _display_name_from_variant_name(variant_name: str) -> str:
    return variant_name.replace("_", " ").replace("-", " ").title()


def _section_title(section_name: CvSectionName) -> str:
    return section_name.value.replace("_", " ").title()
