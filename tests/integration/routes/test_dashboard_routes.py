from __future__ import annotations

from pathlib import Path

from app.db.repositories import (
    ApplicationRepository,
    ApplicationWarningRepository,
    ArtifactRepository,
)
from tests.support.apps import build_example_client, long_job_text


def test_dashboard_empty_state_renders(tmp_path: Path) -> None:
    client = build_example_client(tmp_path)

    response = client.get("/dashboard")

    assert response.status_code == 200
    assert "Dashboard" in response.text
    assert "No applications have been created yet." in response.text


def test_dashboard_lists_applications_counts_and_links(tmp_path: Path) -> None:
    client = build_example_client(tmp_path)
    create_response = client.post(
        "/applications",
        data={
            "manual_text": long_job_text(),
            "source_url": "https://example.test/jobs/backend",
            "selected_cv_variant": "backend_developer",
        },
        follow_redirects=False,
    )
    assert create_response.headers["location"] == "/applications/1"

    with client.app.state.session_factory() as session:
        application = ApplicationRepository(session).get_by_number(
            profile_name="example",
            application_number=1,
        )
        assert application is not None

        ApplicationWarningRepository(session).create(
            application_id=application.id,
            code="manual_review",
            message="Manual review requested.",
        )
        ArtifactRepository(session).create(
            application_id=application.id,
            artifact_type="extracted_job",
            path=f"applications/{application.artifact_dir_name}/extracted_job.json",
        )
        session.commit()

    response = client.get("/dashboard")

    assert response.status_code == 200
    assert "backend_developer" in response.text
    assert "draft" in response.text
    assert "APP-000001" in response.text
    assert 'href="/applications/1"' in response.text
    assert 'href="/applications/1/review"' in response.text
    assert ">1</td>" in response.text
    assert ">2</td>" in response.text
    assert str(tmp_path) not in response.text
