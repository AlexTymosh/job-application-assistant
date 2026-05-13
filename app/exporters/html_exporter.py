from __future__ import annotations

from html import escape


class HtmlExporter:
    """Render a conservative Markdown subset as a standalone HTML document."""

    def export(self, markdown: str, title: str = "Tailored CV") -> str:
        if not markdown.strip():
            raise ValueError("HTML export content must not be empty.")

        body = _render_body(markdown)
        escaped_title = escape(title, quote=True)

        return "\n".join(
            [
                "<!doctype html>",
                '<html lang="en">',
                "<head>",
                '<meta charset="utf-8">',
                '<meta name="viewport" content="width=device-width, initial-scale=1">',
                f"<title>{escaped_title}</title>",
                "</head>",
                "<body>",
                "<main>",
                body,
                "</main>",
                "</body>",
                "</html>",
                "",
            ]
        )


def _render_body(markdown: str) -> str:
    blocks: list[str] = []
    paragraph_lines: list[str] = []
    list_items: list[str] = []

    def flush_paragraph() -> None:
        if paragraph_lines:
            text = " ".join(line.strip() for line in paragraph_lines)
            blocks.append(f"<p>{escape(text)}</p>")
            paragraph_lines.clear()

    def flush_list() -> None:
        if list_items:
            rendered_items = "".join(f"<li>{escape(item)}</li>" for item in list_items)
            blocks.append(f"<ul>{rendered_items}</ul>")
            list_items.clear()

    for raw_line in markdown.splitlines():
        line = raw_line.strip()

        if not line:
            flush_paragraph()
            flush_list()
            continue

        if line.startswith("## "):
            flush_paragraph()
            flush_list()
            blocks.append(f"<h2>{escape(line[3:].strip())}</h2>")
            continue

        if line.startswith("# "):
            flush_paragraph()
            flush_list()
            blocks.append(f"<h1>{escape(line[2:].strip())}</h1>")
            continue

        if line.startswith("- "):
            flush_paragraph()
            list_items.append(line[2:].strip())
            continue

        flush_list()
        paragraph_lines.append(line)

    flush_paragraph()
    flush_list()

    return "\n".join(blocks)
