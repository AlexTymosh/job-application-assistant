from __future__ import annotations


def test_setup_settings_profiles_pages_render(app_client):
    assert app_client.get("/setup").status_code == 200
    assert app_client.get("/settings").status_code == 200
    assert app_client.get("/profiles").status_code == 200


def test_profile_resume_application_route_flow(app_client):
    response = app_client.post(
        "/profiles/new",
        data={
            "display_name": "Alex",
            "full_name": "Alex Example",
            "location": "Remote",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    profile_url = response.headers["location"]
    profile_id = int(profile_url.rsplit("/", 1)[1])

    response = app_client.post(
        f"/profiles/{profile_id}/resumes/new",
        data={"name": "Backend", "target_role": "Backend Developer", "language": "en"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    resume_id = int(response.headers["location"].rsplit("/", 1)[1])

    app_client.post(
        f"/resumes/{resume_id}/sections/new",
        data={
            "section_type": "work_experience",
            "title": "Work Experience",
            "ai_edit_enabled": "true",
        },
    )
    page = app_client.get(f"/resumes/{resume_id}")
    assert "Work Experience" in page.text

    response = app_client.post(
        "/applications/new",
        data={
            "profile_id": profile_id,
            "resume_id": resume_id,
            "job_title": "Engineer",
            "company_name": "Acme",
            "raw_job_text": "Python SQL",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
