from pathlib import Path

import pytest

from app.cv.markdown_loader import load_markdown_file


def test_load_markdown_file_loads_existing_utf8_markdown(tmp_path: Path) -> None:
    markdown_path = tmp_path / "cv.md"
    markdown_path.write_text("# CV\n\nPractical Python experience.\n", encoding="utf-8")

    assert load_markdown_file(markdown_path) == "# CV\n\nPractical Python experience.\n"


def test_load_markdown_file_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_markdown_file(tmp_path / "missing.md")


def test_load_markdown_file_rejects_directory_path(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="not a file"):
        load_markdown_file(tmp_path)


def test_load_markdown_file_rejects_empty_file(tmp_path: Path) -> None:
    markdown_path = tmp_path / "empty.md"
    markdown_path.write_text("", encoding="utf-8")

    with pytest.raises(ValueError, match="empty"):
        load_markdown_file(markdown_path)


def test_load_markdown_file_rejects_whitespace_only_file(tmp_path: Path) -> None:
    markdown_path = tmp_path / "blank.md"
    markdown_path.write_text("  \n\t  ", encoding="utf-8")

    with pytest.raises(ValueError, match="whitespace-only"):
        load_markdown_file(markdown_path)
