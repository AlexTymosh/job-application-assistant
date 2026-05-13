from __future__ import annotations

from pathlib import Path
from uuid import UUID

from app.db.repositories import ApplicationWarningRepository, ArtifactRepository
from tests.test_application_routes import build_test_client, long_job_text


def test_dashboard_empty_state_renders(tmp_path: Path) -> None:
    client = build_test_client(tmp_path)

    response = client.get("/dashboard")

    assert response.status_code == 200
    assert "Dashboard" in response.text
    assert "No applications have been created yet." in response.text


def test_dashboard_lists_applications_counts_and_links(tmp_path: Path) -> None:
    client = build_test_client(tmp_path)
    create_response = client.post(
        "/applications",
        data={
            "manual_text": long_job_text(),
            "source_url": "https://example.test/jobs/backend",
            "selected_cv_variant": "backend_developer",
        },
        follow_redirects=False,
    )
    application_id = create_response.headers["location"].rsplit("/", maxsplit=1)[-1]

    with client.app.state.session_factory() as session:
        ApplicationWarningRepository(session).create(
            application_id=UUID(application_id),
            code="manual_review",
            message="Manual review requested.",
        )
        ArtifactRepository(session).create(
            application_id=UUID(application_id),
            artifact_type="extracted_job",
            path=f"applications/{application_id}/extracted_job.json",
        )
        session.commit()

    response = client.get("/dashboard")

    assert response.status_code == 200
    assert "backend_developer" in response.text
    assert "draft" in response.text
    assert f'href="/applications/{application_id}"' in response.text
    assert f'href="/applications/{application_id}/review"' in response.text
    assert ">1</td>" in response.text
    assert ">2</td>" in response.text
    assert str(tmp_path) not in response.text
