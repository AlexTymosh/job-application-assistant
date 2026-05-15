import pytest

from app.exporters.html_exporter import HtmlExporter


def test_html_exporter_creates_complete_html_document() -> None:
    html = HtmlExporter().export("# Jane Example", title="Jane CV")

    assert html.startswith("<!doctype html>\n")
    assert '<html lang="en">' in html
    assert '<meta charset="utf-8">' in html
    assert (
        '<meta name="viewport" content="width=device-width, initial-scale=1">' in html
    )
    assert "<title>Jane CV</title>" in html
    assert "<main>" in html
    assert html.endswith("</html>\n")


def test_html_exporter_renders_headings_lists_and_paragraphs() -> None:
    markdown = (
        "# Jane Example\n\n## Skills\n\n- Python\n- FastAPI\n\nBuilds local tools."
    )

    html = HtmlExporter().export(markdown)

    assert "<h1>Jane Example</h1>" in html
    assert "<h2>Skills</h2>" in html
    assert "<ul><li>Python</li><li>FastAPI</li></ul>" in html
    assert "<p>Builds local tools.</p>" in html


def test_html_exporter_escapes_raw_html_and_script_input() -> None:
    markdown = "# <script>alert('x')</script>\n\n<script src=\"https://example.invalid/x.js\"></script>"

    html = HtmlExporter().export(markdown, title="<Tailored>")

    assert "<title>&lt;Tailored&gt;</title>" in html
    assert "&lt;script&gt;alert(&#x27;x&#x27;)&lt;/script&gt;" in html
    assert (
        "&lt;script src=&quot;https://example.invalid/x.js&quot;&gt;&lt;/script&gt;"
        in html
    )
    assert "<script" not in html
    assert "</script>" not in html


def test_html_exporter_rejects_whitespace_only_markdown() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        HtmlExporter().export(" \n\t ")


def test_html_exporter_does_not_include_external_scripts_or_css() -> None:
    html = HtmlExporter().export("# Tailored CV\n\nPlain content.")

    assert "<script" not in html
    assert "stylesheet" not in html
    assert "http://" not in html
    assert "https://" not in html
