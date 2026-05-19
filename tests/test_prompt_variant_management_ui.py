from __future__ import annotations

from app.settings.service import SettingsService
from tests.test_master_cv_workflow import create_profile_resume


def test_prompt_variant_create_edit_deactivate_routes(app_client, session):
    profile, _resume = create_profile_resume(session)
    SettingsService(session).set_active_profile(profile.id)

    create_response = app_client.post(
        "/settings/prompt-variants/new",
        data={
            "name": "My Variant",
            "description": "Desc",
            "resume_tailoring": "R",
            "cover_letter": "C",
            "fit_analysis": "F",
        },
        follow_redirects=True,
    )
    assert create_response.status_code == 200
    assert "My Variant" in create_response.text

    list_response = app_client.get("/settings/prompt-variants")
    assert "Default Prompt Variant" in list_response.text

    edit_page = app_client.get("/settings/prompt-variants")
    assert edit_page.status_code == 200

    # Find created variant id from listing links
    marker = "/settings/prompt-variants/"
    matches = [
        part for part in edit_page.text.split(marker) if part and part[0].isdigit()
    ]
    variant_id = max(int(part.split("/")[0]) for part in matches)

    edit_response = app_client.post(
        f"/settings/prompt-variants/{variant_id}/edit",
        data={
            "name": "My Variant Updated",
            "description": "Updated",
            "resume_tailoring": "R2",
            "cover_letter": "C2",
            "fit_analysis": "F2",
        },
        follow_redirects=True,
    )
    assert "My Variant Updated" in edit_response.text

    deactivate = app_client.post(
        f"/settings/prompt-variants/{variant_id}/deactivate", follow_redirects=True
    )
    assert deactivate.status_code == 200

    new_app_page = app_client.get("/applications/new")
    assert "My Variant Updated" not in new_app_page.text


def test_builtin_variant_cannot_be_deactivated(app_client):
    response = app_client.post("/settings/prompt-variants/1/deactivate")
    assert response.status_code in {400, 404}
