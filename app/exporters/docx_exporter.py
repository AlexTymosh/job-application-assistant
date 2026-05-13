from __future__ import annotations

from io import BytesIO

from docx import Document


class DocxExporter:
    """Render a conservative Markdown subset as DOCX bytes."""

    def export(self, markdown: str, title: str = "Tailored CV") -> bytes:
        if not markdown.strip():
            raise ValueError("DOCX export content must not be empty.")

        document = Document()
        document.core_properties.title = title
        _render_markdown(document, markdown)

        buffer = BytesIO()
        document.save(buffer)
        return buffer.getvalue()


def _render_markdown(document: Document, markdown: str) -> None:
    paragraph_lines: list[str] = []

    def flush_paragraph() -> None:
        if paragraph_lines:
            text = " ".join(line.strip() for line in paragraph_lines)
            document.add_paragraph(text)
            paragraph_lines.clear()

    for raw_line in markdown.splitlines():
        line = raw_line.strip()

        if not line:
            flush_paragraph()
            continue

        if line.startswith("## "):
            flush_paragraph()
            document.add_heading(line[3:].strip(), level=2)
            continue

        if line.startswith("# "):
            flush_paragraph()
            document.add_heading(line[2:].strip(), level=1)
            continue

        if line.startswith("- "):
            flush_paragraph()
            document.add_paragraph(line[2:].strip(), style="List Bullet")
            continue

        paragraph_lines.append(line)

    flush_paragraph()
