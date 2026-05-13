from pathlib import Path

import pytest

from app.exporters.pdf_exporter import PdfExporter


def test_pdf_exporter_rejects_empty_content() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        PdfExporter().export(" \n\t ")


def test_pdf_exporter_returns_pdf_bytes() -> None:
    pdf = PdfExporter().export("# Jane Example\n\nBuilds local tools.")

    assert isinstance(pdf, bytes)
    assert pdf.startswith(b"%PDF")


def test_pdf_exporter_handles_headings_bullet_lists_and_paragraphs() -> None:
    markdown = (
        "# Jane Example\n\n## Skills\n\n- Python\n- FastAPI\n\nBuilds local tools."
    )

    pdf = PdfExporter().export(markdown, title="Jane Example CV")

    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 500


def test_pdf_exporter_treats_raw_html_and_script_like_input_as_text() -> None:
    markdown = "# <script>alert('x')</script>\n\n<script src=\"https://example.invalid/x.js\"></script>"

    pdf = PdfExporter().export(markdown, title="<Tailored>")

    assert pdf.startswith(b"%PDF")
    assert b"https://example.invalid/x.js" not in pdf


def test_pdf_exporter_does_not_write_files_directly(tmp_path: Path) -> None:
    before = set(tmp_path.iterdir())

    PdfExporter().export("# Tailored CV\n\n- Python")

    assert set(tmp_path.iterdir()) == before
