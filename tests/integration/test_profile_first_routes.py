from __future__ import annotations


def _create_profile(client, name="Alex") -> int:
    response = client.post(
        "/profiles/new",
        data={
            "display_name": name,
            "full_name": f"{name} Example",
            "location": "Remote",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    return int(response.headers["location"].rsplit("/", 1)[1])


def _create_resume(client, profile_id: int, name="Backend") -> int:
    response = client.post(
        f"/profiles/{profile_id}/resumes/new",
        data={
            "name": name,
            "target_role": "Backend Developer",
            "language": "en",
            "create_standard_sections": "on",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    return int(response.headers["location"].rsplit("/", 1)[1])


def test_navigation_header_active_profile_and_settings_hub(app_client):
    dashboard = app_client.get("/")
    assert dashboard.status_code == 200
    assert "AI JOB APPLICATION ASSISTANT" in dashboard.text
    assert "🏠 Dashboard" in dashboard.text
    assert "📄 Application" in dashboard.text
    assert "🧩 CV Builder" in dashboard.text
    assert "⚙ Settings" in dashboard.text
    assert (
        'href="https://github.com/AlexTymosh/job-application-assistant"'
        in dashboard.text
    )
    assert "No active profile" in dashboard.text

    profile_id = _create_profile(app_client)
    page = app_client.get("/")
    assert "Alex" in page.text

    settings = app_client.get("/settings")
    assert "Workspace hub" in settings.text
    assert "Prompt templates" in settings.text
    assert f"/profiles/{profile_id}/resumes" in settings.text
    assert "Safety and privacy" in settings.text


def test_prompt_template_route_can_edit_user_instruction(app_client):
    page = app_client.get("/settings/prompts")
    assert page.status_code == 200
    assert "AI prompt instructions" in page.text
    assert "Protected AI instructions" not in page.text
    marker = 'action="/settings/prompts/'
    template_id = int(page.text.split(marker, 1)[1].split('"', 1)[0])
    response = app_client.post(
        f"/settings/prompts/{template_id}",
        data={"user_prompt_template": "Prefer concise bullets."},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "Prefer concise bullets." in app_client.get("/settings/prompts").text
    assert (
        "Internal privacy and anti-fabrication guardrails"
        in app_client.get("/settings/prompts").text
    )


def test_application_workspace_active_profile_scope_and_events(app_client):
    profile_id = _create_profile(app_client)
    resume_id = _create_resume(app_client, profile_id)
    workspace = app_client.get("/applications")
    assert workspace.status_code == 200
    assert "Adapt a resume for a job" in workspace.text
    assert "Backend" in workspace.text

    response = app_client.post(
        "/applications/adapt",
        data={
            "resume_id": resume_id,
            "job_title": "Backend Engineer",
            "company_name": "Acme",
            "source_url": "https://example.invalid/job",
            "raw_job_text": "Python FastAPI SQL testing",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    application_url = response.headers["location"]
    detail = app_client.get(application_url)
    assert "Job fit summary" in detail.text
    assert "Cover letter" in detail.text
    assert "Mark as applied" in detail.text

    application_id = int(application_url.rsplit("/", 1)[1])
    copy_response = app_client.post(
        f"/applications/{application_id}/events/copy",
        data={"target_type": "cover_letter", "target_id": "1", "label": "cover letter"},
        follow_redirects=False,
    )
    assert copy_response.status_code == 303
    dashboard = app_client.get("/")
    assert "Likely applied" in dashboard.text
    assert "1" in dashboard.text

    mark_response = app_client.post(
        f"/applications/{application_id}/mark-applied",
        follow_redirects=False,
    )
    assert mark_response.status_code == 303
    assert "manually_marked_applied" in app_client.get(application_url).text
