from __future__ import annotations

from app.people.service import PeopleService
from app.resumes.service import ResumeService
from app.settings.service import SettingsService


def _profile_with_resume(session, name: str):
    profile = PeopleService(session).create_profile(name, name)
    resume = ResumeService(session).create_resume(
        profile.id,
        f"{name} Resume",
        "Software Engineer",
        create_standard_sections=True,
    )
    ResumeService(session).save_section(
        resume.id,
        "header",
        {
            "first_name": name,
            "surname": "Private",
            "email": f"{name.lower()}@example.com",
            "phone": "+44 000",
            "location": "Basingstoke",
            "linkedin_url": "https://linkedin.example",
            "github_url": "https://github.example",
            "extra_text": "Private header text",
        },
    )
    return profile, resume


def test_resume_builder_blocks_cross_profile_direct_access(app_client, session):
    profile_a, _resume_a = _profile_with_resume(session, "Alice")
    _profile_b, resume_b = _profile_with_resume(session, "Bob")
    SettingsService(session).set_active_profile(profile_a.id)

    response = app_client.get(f"/resumes/{resume_b.id}/builder/header")

    assert response.status_code in {403, 404}
    assert "bob@example.com" not in response.text.lower()


def test_resume_export_blocks_cross_profile_direct_access(app_client, session):
    profile_a, _resume_a = _profile_with_resume(session, "Alice")
    _profile_b, resume_b = _profile_with_resume(session, "Bob")
    SettingsService(session).set_active_profile(profile_a.id)

    response = app_client.post(
        f"/resumes/{resume_b.id}/export/docx", follow_redirects=False
    )

    assert response.status_code in {303, 400, 403, 404}
    if response.status_code == 303:
        follow = app_client.get(response.headers["location"])
        assert follow.status_code in {403, 404}


def test_master_cv_blocks_cross_profile_access(app_client, session):
    profile_a, _resume_a = _profile_with_resume(session, "Alice")
    profile_b, _resume_b = _profile_with_resume(session, "Bob")
    SettingsService(session).set_active_profile(profile_a.id)

    get_response = app_client.get(f"/profiles/{profile_b.id}/master-cv/work_experience")
    post_response = app_client.post(
        f"/profiles/{profile_b.id}/master-cv",
        data={
            "category": "summary",
            "summary": "This must not be created for the inactive profile.",
        },
        follow_redirects=False,
    )

    assert get_response.status_code in {403, 404}
    assert post_response.status_code in {403, 404}
    assert PeopleService(session).list_master_entries(profile_b.id) == []


def test_prompt_settings_uses_builder_layout(app_client, session):
    profile, resume = _profile_with_resume(session, "Alice")
    SettingsService(session).set_active_profile(profile.id)

    response = app_client.get("/settings/prompts?block_type=summary")

    assert response.status_code == 200
    assert "builder-shell" in response.text
    assert "builder-nav" in response.text
    assert "builder-preview" in response.text
    assert "Prompt impact preview" in response.text


def test_master_cv_uses_cv_builder_fields_without_abstract_fact_fields(
    app_client, session
):
    profile, _resume = _profile_with_resume(session, "Alice")
    SettingsService(session).set_active_profile(profile.id)

    response = app_client.get(f"/profiles/{profile.id}/master-cv/work_experience")

    assert response.status_code == 200
    assert "Key bullets / source bullets" in response.text
    assert "Job title" not in response.text
    assert "Employer" not in response.text
    assert "Start Date" not in response.text
    assert "End Date" not in response.text
    assert "Keywords (comma-separated)" not in response.text
    assert "Allowed wording" not in response.text
    assert "Forbidden wording" not in response.text
    assert "Inference notes" not in response.text
    assert "Claim strength" not in response.text


def test_settings_profiles_exposes_profile_management(app_client, session):
    profile, _resume = _profile_with_resume(session, "Alice")
    SettingsService(session).set_active_profile(profile.id)

    response = app_client.get("/settings?section=profiles")

    assert response.status_code == 200
    assert "Add profile" in response.text
    assert "/profiles/new" in response.text
    assert f"/profiles/{profile.id}/edit" in response.text
    assert f"/profiles/{profile.id}/delete" in response.text


def test_dashboard_explanatory_sentence_removed(app_client, session):
    profile, _resume = _profile_with_resume(session, "Alice")
    SettingsService(session).set_active_profile(profile.id)

    response = app_client.get("/?days=30")

    assert response.status_code == 200
    assert "X axis shows dates. Y axis shows application count" not in response.text
    assert "data-chart-bar" in response.text


def test_prompt_sections_are_filtered_by_prompt_type(app_client, session):
    profile, resume = _profile_with_resume(session, "Alice")
    SettingsService(session).set_active_profile(profile.id)

    sections = {section.section_type: section.id for section in resume.sections}

    summary_response = app_client.get("/settings/prompts?block_type=summary")

    assert summary_response.status_code == 200
    assert f'value="{sections["summary"]}"' in summary_response.text
    assert f'value="{sections["work_experience"]}"' not in summary_response.text
    assert f'value="{sections["education"]}"' not in summary_response.text

    work_response = app_client.get(
        "/settings/prompts?block_type=work_experience_bullets"
    )

    assert work_response.status_code == 200
    assert f'value="{sections["work_experience"]}"' in work_response.text
    assert f'value="{sections["summary"]}"' not in work_response.text
    assert f'value="{sections["education"]}"' not in work_response.text


def test_resume_builder_header_form_contains_optional_website(app_client, session):
    profile, resume = _profile_with_resume(session, "Alice")
    SettingsService(session).set_active_profile(profile.id)

    response = app_client.get(f"/resumes/{resume.id}/builder/header")

    assert response.status_code == 200
    assert "Website URL optional" in response.text
    assert 'name="website_url"' in response.text


def test_settings_profile_delete_requires_typed_confirmation(app_client, session):
    profile, _resume = _profile_with_resume(session, "Alice")
    SettingsService(session).set_active_profile(profile.id)

    page = app_client.get("/settings?section=profiles")
    assert page.status_code == 200
    assert "Add profile" in page.text
    assert "Edit" in page.text
    assert "Delete" in page.text
    assert "Set active" in page.text
    assert "profile-delete-form" in page.text

    missing = app_client.post(
        f"/profiles/{profile.id}/delete", data={"confirm_profile_name": ""}
    )
    assert missing.status_code == 400
    assert PeopleService(session).get_profile(profile.id).id == profile.id

    deleted = app_client.post(
        f"/profiles/{profile.id}/delete",
        data={"confirm_profile_name": profile.display_name},
        follow_redirects=False,
    )
    assert deleted.status_code == 303
    assert PeopleService(session).list_profiles() == []


def test_dashboard_chart_uses_flat_bars_without_gradient(app_client, session):
    profile, _resume = _profile_with_resume(session, "Alice")
    SettingsService(session).set_active_profile(profile.id)

    response = app_client.get("/?days=10")

    assert response.status_code == 200
    assert "data-chart-bar" in response.text
    assert (
        "background:linear-gradient(180deg,#b9dcec,var(--brand))" not in response.text
    )
    assert "background:linear-gradient(180deg,#f8fafc,#eef6ff)" not in response.text
    assert "background:#f8fafc" in response.text
    assert "background:#9fc7dd" in response.text
