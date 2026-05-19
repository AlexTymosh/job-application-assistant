from __future__ import annotations

from app.applications.service import ApplicationService
from app.core.errors import ApplicationWorkflowError
from app.db.models import PromptVariant, PromptVariantTemplate
from app.llm.tailoring_client import FakeSectionTailoringClient
from app.prompt_variants.service import PromptVariantService
from app.settings.service import SettingsService
from tests.test_master_cv_workflow import create_profile_resume
from tests.test_variant_only_tailoring import _set_variant_only


def _create_custom_variant(session) -> PromptVariant:
    variant = PromptVariant(
        name="Custom Variant",
        description="Custom test prompts",
        is_builtin=False,
        is_active=True,
        profile_id=None,
    )
    session.add(variant)
    session.flush()
    session.add_all(
        [
            PromptVariantTemplate(
                prompt_variant_id=variant.id,
                task_type="resume_tailoring",
                user_prompt_template="CUSTOM RESUME TAILORING PROMPT",
            ),
            PromptVariantTemplate(
                prompt_variant_id=variant.id,
                task_type="cover_letter",
                user_prompt_template="CUSTOM COVER LETTER PROMPT",
            ),
            PromptVariantTemplate(
                prompt_variant_id=variant.id,
                task_type="fit_analysis",
                user_prompt_template="CUSTOM FIT ANALYSIS PROMPT",
            ),
        ]
    )
    session.commit()
    return variant


def test_prompt_variant_service_default_and_active_filtering(session):
    service = PromptVariantService(session)
    default_variant = service.ensure_default_variant()
    session.commit()

    inactive_variant = PromptVariant(
        name="Inactive",
        description="Inactive",
        is_builtin=False,
        is_active=False,
        profile_id=None,
    )
    session.add(inactive_variant)
    session.commit()

    active_ids = [variant.id for variant in service.list_active()]
    assert default_variant.id in active_ids
    assert inactive_variant.id not in active_ids


def test_prompt_variant_invalid_selection_is_controlled_error(session):
    with_exception = False
    try:
        PromptVariantService(session).resolve_or_default(999999)
    except ApplicationWorkflowError:
        with_exception = True
    assert with_exception


def test_selected_prompt_variant_is_stored_on_application(session):
    profile, resume = create_profile_resume(session)
    variant = _create_custom_variant(session)

    application = ApplicationService(session).create_application(
        profile_id=profile.id,
        resume_id=resume.id,
        raw_job_text="Python role",
        prompt_variant_id=variant.id,
    )

    assert application.prompt_variant_id == variant.id


def test_selected_prompt_variant_drives_all_variant_only_prompts(session):
    profile, resume = create_profile_resume(session)
    _set_variant_only(session)
    variant = _create_custom_variant(session)

    application = ApplicationService(session).create_application(
        profile_id=profile.id,
        resume_id=resume.id,
        raw_job_text="Python role",
        prompt_variant_id=variant.id,
    )
    client = FakeSectionTailoringClient()

    ApplicationService(session).adapt_application(application.id, section_client=client)

    assert client.captured_json_calls
    resume_calls = [
        c for c in client.captured_json_calls if c["task_name"] == "resume_tailoring"
    ]
    assert resume_calls
    assert all(
        call["prompt"] == "CUSTOM RESUME TAILORING PROMPT" for call in resume_calls
    )
    assert all(
        call["prompt"] != SettingsService(session).get_prompt_instruction("summary")
        for call in client.captured_json_calls
    )
    cover_prompt = [
        call["prompt"]
        for call in client.captured_json_calls
        if call["task_name"] == "cover_letter"
    ][0]
    fit_prompt = [
        call["prompt"]
        for call in client.captured_json_calls
        if call["task_name"] == "fit_analysis"
    ][0]
    assert cover_prompt == "CUSTOM COVER LETTER PROMPT"
    assert fit_prompt == "CUSTOM FIT ANALYSIS PROMPT"


def test_application_new_page_lists_only_active_prompt_variants(app_client, session):
    profile, _resume = create_profile_resume(session)
    SettingsService(session).set_active_profile(profile.id)
    active_variant = _create_custom_variant(session)
    inactive_variant = PromptVariant(
        name="Inactive UI Variant",
        description="",
        is_builtin=False,
        is_active=False,
        profile_id=None,
    )
    session.add(inactive_variant)
    session.commit()

    response = app_client.get("/applications/new")

    assert response.status_code == 200
    assert "Default Prompt Variant" in response.text
    assert active_variant.name in response.text
    assert inactive_variant.name not in response.text


def test_application_new_page_mode_label_follows_setting(app_client, session):
    profile, _resume = create_profile_resume(session)
    SettingsService(session).set_active_profile(profile.id)
    settings = SettingsService(session)

    settings.set(
        "ai_policy_defaults",
        {
            "use_master_cv": False,
            "allow_new_bullets": True,
            "allow_hide_bullets": False,
            "allow_title_edits": False,
        },
    )
    variant_only = app_client.get("/applications/new")
    assert "Variant-only mode" in variant_only.text

    settings.set(
        "ai_policy_defaults",
        {
            "use_master_cv": True,
            "allow_new_bullets": True,
            "allow_hide_bullets": False,
            "allow_title_edits": False,
        },
    )
    enhanced = app_client.get("/applications/new")
    assert "Master CV enhanced mode" in enhanced.text
