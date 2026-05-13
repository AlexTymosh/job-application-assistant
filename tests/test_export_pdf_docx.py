from pathlib import Path

import pytest
from sqlalchemy import select

from app.artifacts.writer import ArtifactWriter
from app.db.models import Artifact
from app.db.repositories import ApplicationRepository
from app.db.session import (
    create_all_tables,
    create_session_factory,
    create_sqlite_engine,
)
from app.pipeline.export_pdf_docx import export_pdf_docx_artifacts


def test_export_pdf_docx_writes_files_and_database_rows(tmp_path: Path) -> None:
    database_file = tmp_path / "applications.sqlite3"
    applications_dir = tmp_path / "private-profile" / "applications"
    engine = create_sqlite_engine(database_file)
    create_all_tables(engine)
    session_factory = create_session_factory(engine)
    markdown = "# Jane Example\n\n## Skills\n\n- Python\n\nBuilds local tools."

    with session_factory() as session, session.begin():
        application = ApplicationRepository(session).create(profile_name="example")
        application_id = application.id

        result = export_pdf_docx_artifacts(
            session=session,
            applications_dir=applications_dir,
            application_id=application_id,
            tailored_cv_markdown=markdown,
            title="Jane Example CV",
        )

        assert (
            result.pdf.relative_path == f"applications/{application_id}/tailored_cv.pdf"
        )
        assert result.docx.relative_path == (
            f"applications/{application_id}/tailored_cv.docx"
        )
        assert result.pdf_artifact.path == result.pdf.relative_path
        assert result.docx_artifact.path == result.docx.relative_path

    pdf_path = applications_dir / str(application_id) / "tailored_cv.pdf"
    docx_path = applications_dir / str(application_id) / "tailored_cv.docx"

    assert pdf_path.is_file()
    assert docx_path.is_file()
    assert pdf_path.read_bytes().startswith(b"%PDF")
    assert docx_path.read_bytes().startswith(b"PK")
    assert pdf_path.stat().st_size > 0
    assert docx_path.stat().st_size > 0

    with session_factory() as session:
        artifacts = list(
            session.scalars(select(Artifact).order_by(Artifact.artifact_type)).all()
        )

    assert [artifact.artifact_type for artifact in artifacts] == [
        "tailored_cv_docx",
        "tailored_cv_pdf",
    ]
    assert {artifact.path for artifact in artifacts} == {
        f"applications/{application_id}/tailored_cv.pdf",
        f"applications/{application_id}/tailored_cv.docx",
    }
    for artifact in artifacts:
        assert str(tmp_path) not in artifact.path
        assert not Path(artifact.path).is_absolute()


def test_export_pdf_docx_works_with_explicit_artifact_writer(tmp_path: Path) -> None:
    database_file = tmp_path / "applications.sqlite3"
    applications_dir = tmp_path / "private-profile" / "applications"
    engine = create_sqlite_engine(database_file)
    create_all_tables(engine)
    session_factory = create_session_factory(engine)
    writer = ArtifactWriter(applications_dir=applications_dir)

    with session_factory() as session, session.begin():
        application = ApplicationRepository(session).create(profile_name="example")
        application_id = application.id

        result = export_pdf_docx_artifacts(
            session=session,
            artifact_writer=writer,
            application_id=application_id,
            tailored_cv_markdown="# Jane Example\n\n- Python",
        )

    assert (
        result.pdf.absolute_path
        == applications_dir / str(application_id) / "tailored_cv.pdf"
    )
    assert result.docx.absolute_path == (
        applications_dir / str(application_id) / "tailored_cv.docx"
    )
    assert result.pdf.absolute_path.read_bytes().startswith(b"%PDF")
    assert result.docx.absolute_path.read_bytes().startswith(b"PK")


def test_export_pdf_docx_requires_writer_or_applications_dir(tmp_path: Path) -> None:
    database_file = tmp_path / "applications.sqlite3"
    engine = create_sqlite_engine(database_file)
    create_all_tables(engine)
    session_factory = create_session_factory(engine)

    with session_factory() as session, session.begin():
        application = ApplicationRepository(session).create(profile_name="example")

        with pytest.raises(
            ValueError, match="Either artifact_writer or applications_dir"
        ):
            export_pdf_docx_artifacts(
                session=session,
                application_id=application.id,
                tailored_cv_markdown="# Jane Example",
            )
