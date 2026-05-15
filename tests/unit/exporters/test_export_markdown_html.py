from pathlib import Path

from sqlalchemy import select

from app.db.models import Artifact
from app.db.repositories import ApplicationRepository
from app.db.session import (
    create_all_tables,
    create_session_factory,
    create_sqlite_engine,
)
from app.pipeline.export_markdown_html import export_markdown_html_artifacts


def test_export_markdown_html_writes_files_and_database_rows(tmp_path: Path) -> None:
    database_file = tmp_path / "applications.sqlite3"
    applications_dir = tmp_path / "private-profile" / "applications"
    engine = create_sqlite_engine(database_file)
    create_all_tables(engine)
    session_factory = create_session_factory(engine)
    markdown = "# Jane Example\n\n## Skills\n\n- Python\n\n<script>alert('x')</script>"

    with session_factory() as session, session.begin():
        application = ApplicationRepository(session).create(profile_name="example")
        application_id = application.id
        artifact_dir_name = application.artifact_dir_name
        assert artifact_dir_name is not None

        result = export_markdown_html_artifacts(
            session=session,
            applications_dir=applications_dir,
            application_id=application_id,
            artifact_dir_name=artifact_dir_name,
            tailored_cv_markdown=markdown,
            title="Jane Example CV",
        )

        assert result.markdown.relative_path == (
            f"applications/{artifact_dir_name}/tailored_cv.md"
        )
        assert (
            result.html.relative_path
            == f"applications/{artifact_dir_name}/tailored_cv.html"
        )
        assert result.markdown_artifact.path == result.markdown.relative_path
        assert result.html_artifact.path == result.html.relative_path

    markdown_path = applications_dir / artifact_dir_name / "tailored_cv.md"
    html_path = applications_dir / artifact_dir_name / "tailored_cv.html"

    assert markdown_path.is_file()
    assert html_path.is_file()
    assert markdown_path.read_text(encoding="utf-8") == f"{markdown}\n"

    html = html_path.read_text(encoding="utf-8")
    assert "<title>Jane Example CV</title>" in html
    assert "&lt;script&gt;alert(&#x27;x&#x27;)&lt;/script&gt;" in html
    assert "<script" not in html

    with session_factory() as session:
        artifacts = list(
            session.scalars(select(Artifact).order_by(Artifact.artifact_type)).all()
        )

    assert [artifact.artifact_type for artifact in artifacts] == [
        "tailored_cv_html",
        "tailored_cv_markdown",
    ]
    assert {artifact.path for artifact in artifacts} == {
        f"applications/{artifact_dir_name}/tailored_cv.md",
        f"applications/{artifact_dir_name}/tailored_cv.html",
    }
    for artifact in artifacts:
        assert str(tmp_path) not in artifact.path
        assert not Path(artifact.path).is_absolute()
