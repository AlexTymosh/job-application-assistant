from pathlib import Path
from uuid import UUID

from app.artifacts.writer import ArtifactWriter


def test_artifact_writer_creates_raw_job_text_file_and_safe_relative_path(
    tmp_path: Path,
) -> None:
    application_id = UUID("33333333-3333-3333-3333-333333333333")
    applications_dir = tmp_path / "private-profile" / "applications"
    raw_text = "Senior Python developer role with FastAPI and SQL."

    writer = ArtifactWriter(applications_dir=applications_dir)

    written_artifact = writer.write_raw_job_text(
        application_id=application_id,
        raw_text=raw_text,
    )

    assert written_artifact.absolute_path == (
        applications_dir / str(application_id) / "job_raw.txt"
    )
    assert written_artifact.absolute_path.is_file()
    assert written_artifact.absolute_path.read_text(encoding="utf-8") == raw_text
    assert (
        written_artifact.relative_path
        == "applications/33333333-3333-3333-3333-333333333333/job_raw.txt"
    )
    assert str(tmp_path) not in written_artifact.relative_path


def test_artifact_writer_creates_tailored_cv_markdown_with_final_newline(
    tmp_path: Path,
) -> None:
    application_id = UUID("66666666-6666-6666-6666-666666666666")
    applications_dir = tmp_path / "private-profile" / "applications"

    writer = ArtifactWriter(applications_dir=applications_dir)

    written_artifact = writer.write_tailored_cv_markdown(
        application_id=application_id,
        markdown="# Tailored CV",
    )

    assert written_artifact.absolute_path == (
        applications_dir / str(application_id) / "tailored_cv.md"
    )
    assert (
        written_artifact.absolute_path.read_text(encoding="utf-8") == "# Tailored CV\n"
    )
    assert (
        written_artifact.relative_path
        == "applications/66666666-6666-6666-6666-666666666666/tailored_cv.md"
    )
    assert str(tmp_path) not in written_artifact.relative_path


def test_artifact_writer_creates_tailored_cv_html_with_final_newline(
    tmp_path: Path,
) -> None:
    application_id = UUID("77777777-7777-7777-7777-777777777777")
    applications_dir = tmp_path / "private-profile" / "applications"

    writer = ArtifactWriter(applications_dir=applications_dir)

    written_artifact = writer.write_tailored_cv_html(
        application_id=application_id,
        html="<!doctype html>",
    )

    assert written_artifact.absolute_path == (
        applications_dir / str(application_id) / "tailored_cv.html"
    )
    assert (
        written_artifact.absolute_path.read_text(encoding="utf-8")
        == "<!doctype html>\n"
    )
    assert (
        written_artifact.relative_path
        == "applications/77777777-7777-7777-7777-777777777777/tailored_cv.html"
    )
    assert str(tmp_path) not in written_artifact.relative_path
