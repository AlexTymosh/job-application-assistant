from pathlib import Path

from app.artifacts.writer import ArtifactWriter

ARTIFACT_DIR_NAME = "2026-05-14_09-26-01__unknown-company__unknown-role__33333333"


def test_artifact_writer_creates_raw_job_text_file_and_safe_relative_path(
    tmp_path: Path,
) -> None:
    applications_dir = tmp_path / "private-profile" / "applications"
    raw_text = "Senior Python developer role with FastAPI and SQL."

    writer = ArtifactWriter(applications_dir=applications_dir)

    written_artifact = writer.write_raw_job_text(
        artifact_dir_name=ARTIFACT_DIR_NAME,
        raw_text=raw_text,
    )

    assert written_artifact.absolute_path == (
        applications_dir / ARTIFACT_DIR_NAME / "job_raw.txt"
    )
    assert written_artifact.absolute_path.is_file()
    assert written_artifact.absolute_path.read_text(encoding="utf-8") == raw_text
    assert (
        written_artifact.relative_path
        == f"applications/{ARTIFACT_DIR_NAME}/job_raw.txt"
    )
    assert str(tmp_path) not in written_artifact.relative_path


def test_artifact_writer_creates_tailored_cv_markdown_with_final_newline(
    tmp_path: Path,
) -> None:
    applications_dir = tmp_path / "private-profile" / "applications"

    writer = ArtifactWriter(applications_dir=applications_dir)

    written_artifact = writer.write_tailored_cv_markdown(
        artifact_dir_name=ARTIFACT_DIR_NAME,
        markdown="# Tailored CV",
    )

    assert written_artifact.absolute_path == (
        applications_dir / ARTIFACT_DIR_NAME / "tailored_cv.md"
    )
    assert (
        written_artifact.absolute_path.read_text(encoding="utf-8") == "# Tailored CV\n"
    )
    assert (
        written_artifact.relative_path
        == f"applications/{ARTIFACT_DIR_NAME}/tailored_cv.md"
    )
    assert str(tmp_path) not in written_artifact.relative_path


def test_artifact_writer_creates_tailored_cv_html_with_final_newline(
    tmp_path: Path,
) -> None:
    applications_dir = tmp_path / "private-profile" / "applications"

    writer = ArtifactWriter(applications_dir=applications_dir)

    written_artifact = writer.write_tailored_cv_html(
        artifact_dir_name=ARTIFACT_DIR_NAME,
        html="<!doctype html>",
    )

    assert written_artifact.absolute_path == (
        applications_dir / ARTIFACT_DIR_NAME / "tailored_cv.html"
    )
    assert (
        written_artifact.absolute_path.read_text(encoding="utf-8")
        == "<!doctype html>\n"
    )
    assert (
        written_artifact.relative_path
        == f"applications/{ARTIFACT_DIR_NAME}/tailored_cv.html"
    )
    assert str(tmp_path) not in written_artifact.relative_path


def test_artifact_writer_creates_tailored_cv_pdf_and_preserves_bytes(
    tmp_path: Path,
) -> None:
    applications_dir = tmp_path / "private-profile" / "applications"
    pdf_bytes = b"%PDF-1.4 fake test bytes"

    writer = ArtifactWriter(applications_dir=applications_dir)

    written_artifact = writer.write_tailored_cv_pdf(
        artifact_dir_name=ARTIFACT_DIR_NAME,
        pdf_bytes=pdf_bytes,
    )

    assert written_artifact.absolute_path == (
        applications_dir / ARTIFACT_DIR_NAME / "tailored_cv.pdf"
    )
    assert written_artifact.absolute_path.read_bytes() == pdf_bytes
    assert (
        written_artifact.relative_path
        == f"applications/{ARTIFACT_DIR_NAME}/tailored_cv.pdf"
    )
    assert str(tmp_path) not in written_artifact.relative_path


def test_artifact_writer_creates_tailored_cv_docx_and_preserves_bytes(
    tmp_path: Path,
) -> None:
    applications_dir = tmp_path / "private-profile" / "applications"
    docx_bytes = b"PK fake test bytes"

    writer = ArtifactWriter(applications_dir=applications_dir)

    written_artifact = writer.write_tailored_cv_docx(
        artifact_dir_name=ARTIFACT_DIR_NAME,
        docx_bytes=docx_bytes,
    )

    assert written_artifact.absolute_path == (
        applications_dir / ARTIFACT_DIR_NAME / "tailored_cv.docx"
    )
    assert written_artifact.absolute_path.read_bytes() == docx_bytes
    assert (
        written_artifact.relative_path
        == f"applications/{ARTIFACT_DIR_NAME}/tailored_cv.docx"
    )
    assert str(tmp_path) not in written_artifact.relative_path
