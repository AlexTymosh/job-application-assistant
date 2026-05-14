from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import ProjectConfig, load_profile_config
from app.db.session import create_all_tables
from app.main import create_app


def build_test_client(tmp_path: Path) -> TestClient:
    base_config = load_profile_config()
    profile_dir = tmp_path / "example"
    profile_dir.mkdir(parents=True)
    (profile_dir / "blacklist.example.txt").write_text(
        "BlockedCorp\n", encoding="utf-8"
    )

    config = ProjectConfig.model_validate(
        base_config.model_dump()
        | {"app": {"profile_name": "example", "data_dir": profile_dir}}
    )
    app = create_app(config)
    create_all_tables(app.state.engine)
    return TestClient(app)


def long_job_text(extra: str = "") -> str:
    return (
        "We need a backend developer to build reliable API services, write tests, "
        "work with databases, review code, document decisions, and collaborate with "
        "product stakeholders. The role values clear communication, maintainable "
        "Python services, and careful delivery. "
        f"{extra}"
    )


def test_get_new_application_returns_form(tmp_path: Path) -> None:
    client = build_test_client(tmp_path)

    response = client.get("/applications/new")

    assert response.status_code == 200
    assert "New Application" in response.text
    assert "Manual job text" in response.text
    assert "Create application" in response.text


def test_post_valid_manual_text_creates_application_and_redirects(
    tmp_path: Path,
) -> None:
    client = build_test_client(tmp_path)

    response = client.post(
        "/applications",
        data={
            "manual_text": long_job_text(),
            "source_url": "https://Example.test/jobs/backend?utm_source=newsletter",
            "selected_cv_variant": "backend_developer",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/applications/1"

    detail_response = client.get(response.headers["location"])

    assert detail_response.status_code == 200
    assert "Application Detail" in detail_response.text
    assert "APP-000001" in detail_response.text
    assert "Internal UUID" not in detail_response.text
    assert "Technical details" in detail_response.text
    assert "Database UUID" in detail_response.text
    assert "backend_developer" in detail_response.text
    assert "https://example.test/jobs/backend" in detail_response.text
    assert "Present" in detail_response.text
    assert "applications/" in detail_response.text
    assert str(tmp_path) not in detail_response.text


def test_post_too_short_manual_text_returns_validation_response(
    tmp_path: Path,
) -> None:
    client = build_test_client(tmp_path)

    response = client.post(
        "/applications",
        data={
            "manual_text": "Too short.",
            "source_url": "",
            "selected_cv_variant": "backend_developer",
        },
    )

    assert response.status_code == 400
    assert "Validation errors" in response.text
    assert "Manual job text must contain at least" in response.text

    dashboard_response = client.get("/dashboard")

    assert "No applications have been created yet." in dashboard_response.text


def test_get_application_detail_displays_warnings_events_and_artifacts(
    tmp_path: Path,
) -> None:
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

    response = client.get(create_response.headers["location"])

    assert response.status_code == 200
    assert "prompt_injection_phrase" in response.text
    assert "job_input_created" in response.text
    assert "job_raw" in response.text
    assert "applications/" in response.text
    assert str(tmp_path) not in response.text


def test_get_unknown_application_returns_404_html(tmp_path: Path) -> None:
    client = build_test_client(tmp_path)

    response = client.get("/applications/999999")

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("text/html")
    assert "Error" in response.text
    assert "Application not found." in response.text
