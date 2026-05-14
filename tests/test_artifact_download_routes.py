from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from app.db.repositories import ApplicationRepository, ArtifactRepository
from tests.test_application_routes import build_test_client, long_job_text


def create_application(client) -> str:  # type: ignore[no-untyped-def]
    response = client.post(
        "/applications",
        data={
            "manual_text": long_job_text(),
            "source_url": "https://example.test/jobs/backend",
            "selected_cv_variant": "backend_developer",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    return response.headers["location"]


def test_download_existing_artifact_for_application(tmp_path: Path) -> None:
    client = build_test_client(tmp_path)
    create_application(client)

    with client.app.state.session_factory() as session:
        application = ApplicationRepository(session).get_by_number(
            profile_name="example",
            application_number=1,
        )
        assert application is not None
        artifact = application.artifacts[0]

    response = client.get(f"/applications/1/artifacts/{artifact.id}/download")

    assert response.status_code == 200
    assert b"backend developer" in response.content.lower()
    assert str(tmp_path).encode() not in response.content


def test_download_missing_artifact_returns_404(tmp_path: Path) -> None:
    client = build_test_client(tmp_path)
    create_application(client)

    response = client.get(f"/applications/1/artifacts/{uuid4()}/download")

    assert response.status_code == 404
    assert "Artifact not found." in response.text


def test_download_artifact_from_wrong_application_returns_404(tmp_path: Path) -> None:
    client = build_test_client(tmp_path)
    create_application(client)
    create_application(client)

    with client.app.state.session_factory() as session:
        first_application = ApplicationRepository(session).get_by_number(
            profile_name="example",
            application_number=1,
        )
        assert first_application is not None
        artifact = first_application.artifacts[0]

    response = client.get(f"/applications/2/artifacts/{artifact.id}/download")

    assert response.status_code == 404
    assert "Artifact not found." in response.text


def test_download_rejects_path_traversal(tmp_path: Path) -> None:
    client = build_test_client(tmp_path)
    create_application(client)

    with client.app.state.session_factory() as session:
        application = ApplicationRepository(session).get_by_number(
            profile_name="example",
            application_number=1,
        )
        assert application is not None
        artifact = ArtifactRepository(session).create(
            application_id=application.id,
            artifact_type="unsafe",
            path="applications/../secrets.txt",
        )
        session.commit()
        artifact_id = artifact.id

    response = client.get(f"/applications/1/artifacts/{artifact_id}/download")

    assert response.status_code == 400
    assert "Unsafe artifact path." in response.text
