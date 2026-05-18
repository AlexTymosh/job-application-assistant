from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from sqlalchemy import select

from app.applications.service import ApplicationService
from app.db.models import AppSetting
from app.llm.tailoring_client import FakeSectionTailoringClient
from app.people.service import PeopleService
from app.settings.service import DEFAULT_USER_PROMPTS, SettingsService
from app.tailoring.service import DeterministicTailoringClient, TailoringService
from tests.test_master_cv_workflow import create_profile_resume

MASTER_ONLY_TEXT = "MASTER_CV_SHOULD_NOT_APPEAR"
PRIVATE_EMAIL = "abc@gmail.com"
PRIVATE_PHONE = "+44"
PRIVATE_REFERENCE_EMAIL = "john@example.com"


def _set_variant_only(session) -> None:
    SettingsService(session).set(
        "ai_policy_defaults",
        {
            "use_master_cv": False,
            "allow_new_bullets": True,
            "allow_hide_bullets": False,
            "allow_title_edits": False,
        },
    )


def _payload_text(client: FakeSectionTailoringClient) -> str:
    return str(client.captured_json_calls + client.captured_text_calls)


def _adapt_variant_only(session):
    profile, resume = create_profile_resume(session)
    _set_variant_only(session)
    PeopleService(session).create_master_entry(
        profile.id,
        category="skills",
        title="Secret Master CV",
        content=MASTER_ONLY_TEXT,
        allowed_wording=MASTER_ONLY_TEXT,
    )
    application = ApplicationService(session).create_application(
        profile_id=profile.id,
        resume_id=resume.id,
        raw_job_text="Python FastAPI job description",
    )
    client = FakeSectionTailoringClient()
    tailored = ApplicationService(session).adapt_application(
        application.id, section_client=client
    )
    return profile, resume, application, tailored, client


def test_variant_only_mode_does_not_use_master_cv(session):
    _profile, _resume, _application, tailored, client = _adapt_variant_only(session)

    assert tailored.content_json["tailoring_sources"] == []
    assert MASTER_ONLY_TEXT not in _payload_text(client)
    assert all(
        call["payload"].get("master_cv_items") in (None, [])
        for call in client.captured_json_calls + client.captured_text_calls
    )


def test_master_cv_enhanced_mode_still_uses_current_master_cv_behaviour(session):
    profile, resume = create_profile_resume(session)
    PeopleService(session).create_master_entry(
        profile.id,
        category="skills",
        title="Poetry",
        content="Used Poetry.",
        allowed_wording="Poetry dependency management",
    )
    application = ApplicationService(session).create_application(
        profile_id=profile.id,
        resume_id=resume.id,
        raw_job_text="Dependency management role",
    )
    client = DeterministicTailoringClient()

    tailored = ApplicationService(session).adapt_application(
        application.id, client=client
    )

    assert client.last_payload is not None
    assert client.last_payload.master_cv_items[0]["title"] == "Poetry"
    assert "Poetry dependency management" in tailored.rendered_markdown


def test_variant_only_section_calls_are_separate(session):
    _profile, _resume, _application, _tailored, client = _adapt_variant_only(session)

    task_names = [call["task_name"] for call in client.captured_json_calls]
    task_names += [call["task_name"] for call in client.captured_text_calls]

    assert task_names == [
        "summary",
        "skills",
        "work_experience_bullets",
        "education_achievements",
        "cover_letter",
        "fit_analysis",
    ]


def test_variant_only_excludes_private_sections_from_all_ai_payloads(session):
    _profile, _resume, _application, _tailored, client = _adapt_variant_only(session)
    payload_text = _payload_text(client)

    assert "header" not in payload_text
    assert "references" not in payload_text
    assert PRIVATE_EMAIL not in payload_text
    assert PRIVATE_PHONE not in payload_text
    assert PRIVATE_REFERENCE_EMAIL not in payload_text


def test_master_cv_enhanced_excludes_private_sections_from_tailoring_payload(session):
    profile, resume = create_profile_resume(session)
    application = ApplicationService(session).create_application(
        profile_id=profile.id, resume_id=resume.id, raw_job_text="FastAPI role"
    )
    client = DeterministicTailoringClient()

    ApplicationService(session).adapt_application(application.id, client=client)

    assert client.last_payload is not None
    assert "header" not in str(client.last_payload.base_resume)
    assert "references" not in str(client.last_payload.base_resume)
    assert PRIVATE_EMAIL not in str(client.last_payload.base_resume)
    assert PRIVATE_REFERENCE_EMAIL not in str(client.last_payload.base_resume)


def test_variant_only_preserves_base_resume_variant(session):
    profile, resume = create_profile_resume(session)
    _set_variant_only(session)
    original_content = deepcopy(
        TailoringService(session).build_variant_only_payloads(resume, "job")
    )
    application = ApplicationService(session).create_application(
        profile_id=profile.id, resume_id=resume.id, raw_job_text="FastAPI role"
    )

    tailored = ApplicationService(session).adapt_application(
        application.id, section_client=FakeSectionTailoringClient()
    )
    refreshed_content = TailoringService(session).build_variant_only_payloads(
        resume, "job"
    )

    assert refreshed_content == original_content
    assert "Variant-only tailored summary" in tailored.rendered_markdown
    assert "Variant-only tailored skill" in tailored.rendered_markdown


def test_fit_analysis_default_prompt_exists_and_resolves(session):
    SettingsService(session).ensure_defaults()

    assert "fit_analysis" in DEFAULT_USER_PROMPTS
    assert (
        SettingsService(session).get_prompt_instruction("fit_analysis")
        == DEFAULT_USER_PROMPTS["fit_analysis"]
    )


def test_fit_analysis_prompt_page_can_show_and_edit(app_client, session):
    profile, resume = create_profile_resume(session)
    SettingsService(session).set_active_profile(profile.id)

    page = app_client.get("/settings/prompts?block_type=fit_analysis")
    assert page.status_code == 200
    assert "Fit Analysis" in page.text
    assert "Section scope is not available" in page.text

    response = app_client.post(
        "/settings/prompts-scoped",
        data={
            "scope": "resume",
            "block_type": "fit_analysis",
            "resume_id": str(resume.id),
            "user_prompt_template": "Custom fit analysis prompt",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert (
        SettingsService(session).get_prompt_instruction(
            "fit_analysis", profile_id=profile.id, resume_id=resume.id
        )
        == "Custom fit analysis prompt"
    )


def test_fit_analysis_displayed_above_comparison(app_client, session):
    profile, resume = create_profile_resume(session)
    SettingsService(session).set_active_profile(profile.id)
    _set_variant_only(session)

    response = app_client.post(
        "/applications/adapt",
        data={"resume_id": str(resume.id), "raw_job_text": "FastAPI role"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    fit_index = response.text.index("Fit Analysis")
    base_index = response.text.index("Base Resume Variant")
    tailored_index = response.text.index("Tailored Resume Preview")
    assert fit_index < base_index < tailored_index
    assert "strong matches" in response.text
    assert "Cover Letter" in response.text


def test_variant_only_cover_letter_payload_excludes_private_and_master_cv(session):
    _profile, _resume, _application, _tailored, client = _adapt_variant_only(session)
    cover_call = next(
        call
        for call in client.captured_text_calls
        if call["task_name"] == "cover_letter"
    )

    assert MASTER_ONLY_TEXT not in str(cover_call["payload"])
    assert PRIVATE_EMAIL not in str(cover_call["payload"])
    assert PRIVATE_REFERENCE_EMAIL not in str(cover_call["payload"])
    assert (
        "Thank you for considering my application"
        in ApplicationService(session).latest_cover_letter(_application.id).content
    )


def test_openai_mode_requires_key(app_client, session):
    profile, resume = create_profile_resume(session)
    SettingsService(session).set_active_profile(profile.id)
    _set_variant_only(session)
    SettingsService(session).set_llm_mode("openai")

    response = app_client.post(
        "/applications/adapt",
        data={"resume_id": str(resume.id), "raw_job_text": "FastAPI role"},
    )

    assert response.status_code == 400
    assert "OpenAI mode requires an API key" in response.text


def test_settings_saves_llm_mode_and_openai_key_without_rendering_secret(
    app_client, session
):
    raw_key = "sk-test-secret-value"

    response = app_client.post(
        "/settings?section=models",
        data={
            "settings_section": "models",
            "llm_mode": "openai",
            "openai_model_default": "model-default",
            "openai_model_qa": "model-qa",
            "openai_model_extract": "model-extract",
            "openai_model_tailor": "model-tailor",
            "openai_api_key": raw_key,
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert app_client.app.state.openai_secret_service.get_api_key() == raw_key
    assert SettingsService(session).effective().llm_mode == "openai"
    stored_settings = session.scalars(select(AppSetting)).all()
    assert raw_key not in str([setting.value_json for setting in stored_settings])

    page = app_client.get("/settings?section=models")
    assert page.status_code == 200
    assert "Key available: yes" in page.text
    assert raw_key not in page.text


def test_openai_key_not_persisted_or_leaked_to_fake_payloads(app_client, session):
    raw_key = "sk-test-secret-value"
    app_client.post(
        "/settings?section=models",
        data={
            "settings_section": "models",
            "llm_mode": "fake",
            "openai_api_key": raw_key,
        },
    )
    _profile, _resume, _application, _tailored, client = _adapt_variant_only(session)

    assert raw_key not in _payload_text(client)
    stored_settings = session.scalars(select(AppSetting)).all()
    assert raw_key not in str([setting.value_json for setting in stored_settings])


def test_gitignore_keeps_env_and_local_private_data_ignored():
    gitignore = Path(".gitignore").read_text(encoding="utf-8")

    assert ".env" in gitignore
    assert "_local/" in gitignore
    assert "profiles/*/applications/" in gitignore
    assert "profiles/*/*.sqlite3" in gitignore
