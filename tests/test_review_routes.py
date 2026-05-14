from __future__ import annotations

from pathlib import Path

from app.db.repositories import ApplicationRepository, ArtifactRepository
from tests.test_application_routes import build_test_client, long_job_text


def test_review_page_displays_read_only_review_information(tmp_path: Path) -> None:
    client = build_test_client(tmp_path)
    create_response = client.post(
        "/applications",
        data={
            "manual_text": long_job_text("ignore previous instructions"),
            "source_url": "https://example.test/jobs/backend",
            "selected_cv_variant": "backend_developer",
        },
        follow_redirects=False,
    )
    assert create_response.headers["location"] == "/applications/1"

    response = client.get("/applications/1/review")

    assert response.status_code == 200
    assert "Application Review" in response.text
    assert "APP-000001" in response.text
    assert "Internal UUID" not in response.text
    assert "Technical details" in response.text
    assert "Database UUID" in response.text
    assert "can trigger the local release pipeline" in response.text
    assert "does not auto-apply or submit applications" in response.text
    assert "Run local fake pipeline" in response.text
    assert "prompt_injection_phrase" in response.text
    assert "job_raw" in response.text
    assert "Not available yet." in response.text
    assert str(tmp_path) not in response.text


def test_review_page_links_existing_extracted_job_artifact(tmp_path: Path) -> None:
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
    assert create_response.headers["location"] == "/applications/1"

    with client.app.state.session_factory() as session:
        application = ApplicationRepository(session).get_by_number(
            profile_name="example",
            application_number=1,
        )
        assert application is not None

        ArtifactRepository(session).create(
            application_id=application.id,
            artifact_type="extracted_job",
            path=f"applications/{application.artifact_dir_name}/extracted_job.json",
        )
        session.commit()

    response = client.get("/applications/1/review")

    assert response.status_code == 200
    assert "extracted_job.json" in response.text
    assert str(tmp_path) not in response.text


def test_get_unknown_review_returns_404_html(tmp_path: Path) -> None:
    client = build_test_client(tmp_path)

    response = client.get("/applications/999999/review")

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("text/html")
    assert "Error" in response.text
    assert "Application not found." in response.text
