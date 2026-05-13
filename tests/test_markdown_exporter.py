import pytest

from app.exporters.markdown_exporter import MarkdownExporter


def test_valid_markdown_is_returned_with_exactly_one_final_newline() -> None:
    exporter = MarkdownExporter()

    exported = exporter.export("# Tailored CV\n\nExperienced with FastAPI.\n\n")

    assert exported == "# Tailored CV\n\nExperienced with FastAPI.\n"
    assert exported.endswith("\n")
    assert not exported.endswith("\n\n")


def test_whitespace_only_markdown_is_rejected() -> None:
    exporter = MarkdownExporter()

    with pytest.raises(ValueError, match="must not be empty"):
        exporter.export(" \n\t ")


def test_markdown_content_is_not_rewritten() -> None:
    exporter = MarkdownExporter()
    markdown = "# Tailored CV\n\n- Python\n- FastAPI\n\nExisting claim text."

    exported = exporter.export(markdown)

    assert exported == f"{markdown}\n"
