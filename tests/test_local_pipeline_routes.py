from __future__ import annotations

from pathlib import Path

from app.db.models import ApplicationStatus
from app.db.repositories import ApplicationRepository
from tests.test_application_routes import build_test_client, long_job_text


def create_application(client) -> None:  # type: ignore[no-untyped-def]
    response = client.post(
        "/applications",
        data={
            "manual_text": long_job_text(" FastAPI Python SQLite API testing."),
            "source_url": "https://example.test/jobs/backend",
            "selected_cv_variant": "backend_developer",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_local_pipeline_action_generates_review_artifacts(tmp_path: Path) -> None:
    client = build_test_client(tmp_path)
    create_application(client)

    response = client.post("/applications/1/run-local-pipeline", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/applications/1/review"

    review_response = client.get("/applications/1/review")

    assert review_response.status_code == 200
    assert "extracted_job.json" in review_response.text
    assert "evidence_matrix.json" in review_response.text
    assert "match_report.json" in review_response.text
    assert "tailored_cv.md" in review_response.text
    assert "tailored_cv.html" in review_response.text
    assert "tailored_cv.pdf" in review_response.text
    assert "tailored_cv.docx" in review_response.text
    assert str(tmp_path) not in review_response.text


def test_local_pipeline_updates_status_to_exported(tmp_path: Path) -> None:
    client = build_test_client(tmp_path)
    create_application(client)

    client.post("/applications/1/run-local-pipeline", follow_redirects=False)

    with client.app.state.session_factory() as session:
        application = ApplicationRepository(session).get_by_number_with_related(
            profile_name="example",
            application_number=1,
        )
        assert application is not None
        assert application.status == ApplicationStatus.EXPORTED.value
        event_types = {event.event_type for event in application.events}
        assert "pipeline_job_extracted" in event_types
        assert "pipeline_cv_tailored" in event_types
        assert "pipeline_reports_generated" in event_types
        assert "pipeline_exports_generated" in event_types


def test_local_pipeline_unknown_application_returns_400(tmp_path: Path) -> None:
    client = build_test_client(tmp_path)

    response = client.post("/applications/999/run-local-pipeline")

    assert response.status_code == 400
    assert "Application not found." in response.text
