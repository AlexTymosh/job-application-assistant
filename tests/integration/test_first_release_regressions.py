from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.errors import ValidationAppError
from app.db.models import (
    AiChangeProposal,
    Application,
    ApplicationEvent,
    ProposalStatus,
    Resume,
    ResumeUpload,
    TailoredResumeSnapshot,
)
from app.main import create_app
from app.resumes.renderer import render_resume_markdown
from app.resumes.service import ResumeService
from app.settings.service import SettingsService


class MemorySecretService:
    def __init__(self) -> None:
        self.value: str | None = None

    def get_api_key(self) -> str | None:
        return self.value

    def set_api_key(self, value: str) -> None:
        self.value = value

    def delete_api_key(self) -> None:
        self.value = None


def _create_profile(client: TestClient, name: str = "Alex") -> int:
    response = client.post(
        "/profiles/new",
        data={"display_name": name, "full_name": f"{name} Example"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    return int(response.headers["location"].rstrip("/").split("/")[-1])


def _create_resume(
    client: TestClient, profile_id: int, name: str = "Backend CV"
) -> int:
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
    return int(response.headers["location"].rstrip("/").split("/")[-1])


def _adapt(client: TestClient, resume_id: int) -> int:
    response = client.post(
        "/applications/adapt",
        data={
            "resume_id": str(resume_id),
            "source_url": "https://example.test/job",
            "raw_job_text": "Python FastAPI SQL testing role",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    return int(response.headers["location"].rstrip("/").split("/")[-1])


def test_active_profile_facts_pages_and_settings_link(app_client: TestClient):
    no_profile = app_client.get("/settings/facts")
    assert no_profile.status_code == 200
    assert "No active profile" in no_profile.text
    assert "/profiles/new" in no_profile.text

    profile_id = _create_profile(app_client)
    settings = app_client.get("/settings")
    assert "/settings/facts" in settings.text
    facts = app_client.get("/settings/facts")
    assert facts.status_code == 200
    assert f"/profiles/{profile_id}/facts/new" in facts.text


def test_adapt_empty_states_and_profile_scoped_resume(app_client: TestClient):
    no_profile = app_client.post(
        "/applications/adapt",
        data={"resume_id": "1", "raw_job_text": "Python"},
    )
    assert no_profile.status_code == 400
    assert "Select an active profile first" in no_profile.text

    profile_id = _create_profile(app_client)
    page = app_client.get("/applications")
    assert "Create resume first" in page.text

    other_profile_id = _create_profile(app_client, "Sam")
    other_resume_id = _create_resume(app_client, other_profile_id, "Other CV")
    app_client.post(
        f"/profiles/{profile_id}/set-active",
        follow_redirects=False,
    )
    wrong_resume = app_client.post(
        "/applications/adapt",
        data={"resume_id": str(other_resume_id), "raw_job_text": "Python"},
    )
    assert wrong_resume.status_code == 404
    assert "Resume must belong to the active profile" in wrong_resume.text

    resume_id = _create_resume(app_client, profile_id)
    application_id = _adapt(app_client, resume_id)
    result = app_client.get(f"/applications/{application_id}")
    assert "Adapted result / review" in result.text
    assert "Cover letter" in result.text


def test_snapshot_errors_accept_edited_export_and_events(
    app_client: TestClient,
    session,
    tmp_path: Path,
):
    profile_id = _create_profile(app_client)
    resume_id = _create_resume(app_client, profile_id)
    app_service_session = session

    application = Application(
        profile_id=profile_id,
        resume_id=resume_id,
        application_number=999,
        raw_job_text="Python",
    )
    app_service_session.add(application)
    app_service_session.commit()
    no_run = app_client.post(f"/applications/{application.id}/snapshot")
    assert no_run.status_code == 400
    assert "Run tailoring before creating" in no_run.text

    application_id = _adapt(app_client, resume_id)
    no_accept = app_client.post(f"/applications/{application_id}/snapshot")
    assert no_accept.status_code == 400
    assert "Accept or accept-edit" in no_accept.text

    proposals = list(
        session.scalars(
            select(AiChangeProposal)
            .join(AiChangeProposal.tailoring_run)
            .where(AiChangeProposal.tailoring_run.has(application_id=application_id))
        )
    )
    assert proposals
    proposal = proposals[0]
    response = app_client.post(
        f"/applications/{application_id}/review",
        data={
            f"decision_{proposal.id}": ProposalStatus.ACCEPTED_EDITED.value,
            f"after_text_{proposal.id}": "Edited tailored first-release text.",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    snapshot_response = app_client.post(
        f"/applications/{application_id}/snapshot", follow_redirects=False
    )
    assert snapshot_response.status_code == 303
    assert "/exports?snapshot_id=" in snapshot_response.headers["location"]
    snapshot = session.scalar(
        select(TailoredResumeSnapshot).where(
            TailoredResumeSnapshot.application_id == application_id
        )
    )
    assert snapshot is not None
    assert "Edited tailored first-release text." in snapshot.rendered_markdown

    export_response = app_client.post(
        f"/applications/{application_id}/exports",
        data={"snapshot_id": str(snapshot.id)},
        follow_redirects=False,
    )
    assert export_response.status_code == 303
    download_event = app_client.post(
        f"/applications/{application_id}/events/copy",
        data={"target_type": "resume_text", "target_id": "snapshot", "label": "resume"},
        follow_redirects=False,
    )
    assert download_event.status_code == 303
    assert session.scalar(
        select(ApplicationEvent).where(ApplicationEvent.event_type == "likely_applied")
    )


def test_application_detail_requires_active_profile_and_scope(app_client: TestClient):
    profile_id = _create_profile(app_client)
    resume_id = _create_resume(app_client, profile_id)
    application_id = _adapt(app_client, resume_id)

    with app_client.app.state.session_factory() as db_session:
        SettingsService(db_session).set_active_profile(None)
    missing = app_client.get(f"/applications/{application_id}")
    assert missing.status_code == 400
    assert "Select an active profile first" in missing.text

    wrong_profile_id = _create_profile(app_client, "Wrong")
    app_client.post(f"/profiles/{wrong_profile_id}/set-active", follow_redirects=False)
    wrong = app_client.post(f"/applications/{application_id}/mark-applied")
    assert wrong.status_code == 404

    app_client.post(f"/profiles/{profile_id}/set-active", follow_redirects=False)
    correct = app_client.get(f"/applications/{application_id}")
    assert correct.status_code == 200


def test_resume_builder_rendering_metadata_and_upload(app_client: TestClient, session):
    profile_id = _create_profile(app_client)
    response = app_client.post(
        f"/profiles/{profile_id}/resumes/new",
        data={
            "name": "Uploaded CV",
            "target_role": "Engineer",
            "language": "en",
            "create_standard_sections": "on",
        },
        files={"resume_upload": ("../unsafe.pdf", b"%PDF-1.4", "application/pdf")},
        follow_redirects=False,
    )
    assert response.status_code == 303
    resume_id = int(response.headers["location"].rstrip("/").split("/")[-1])
    upload = session.scalar(
        select(ResumeUpload).where(ResumeUpload.resume_id == resume_id)
    )
    assert upload is not None
    assert ".." not in upload.relative_path
    assert upload.relative_path.startswith("artifacts/uploads/")

    rejected = app_client.post(
        f"/profiles/{profile_id}/resumes/new",
        data={"name": "Bad", "target_role": "Engineer", "language": "en"},
        files={"resume_upload": ("bad.exe", b"no", "application/octet-stream")},
    )
    assert rejected.status_code == 400
    assert "PDF, DOC, or DOCX" in rejected.text

    edit = app_client.post(
        f"/resumes/{resume_id}/edit",
        data={"name": "Renamed CV", "target_role": "Lead Engineer", "language": "en"},
        follow_redirects=False,
    )
    assert edit.status_code == 303
    builder = app_client.get(f"/resumes/{resume_id}")
    assert "Renamed CV" in builder.text
    assert "Move section up" in builder.text
    assert "add work experience" in builder.text.lower()

    resume = session.get(Resume, resume_id)
    assert resume is not None
    markdown = render_resume_markdown(ResumeService(session).get_resume(resume_id))
    assert "## SUMMARY" not in markdown


def test_prompt_scope_resolution_and_error_pages(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("APP_DATA_DIR", str(tmp_path / "data"))
    app = create_app(openai_secret_service=MemorySecretService())

    @app.get("/raise-domain-error")
    def raise_domain_error():
        raise ValidationAppError("Domain validation failed.")

    @app.get("/raise-unexpected-error")
    def raise_unexpected_error():
        raise RuntimeError("boom")

    with TestClient(app, raise_server_exceptions=False) as client:
        domain = client.get("/raise-domain-error")
        assert domain.status_code == 400
        assert "Domain validation failed" in domain.text
        assert "Dashboard" in domain.text and "Application" in domain.text

        unexpected = client.get("/raise-unexpected-error")
        assert unexpected.status_code == 500
        assert "Something went wrong" in unexpected.text

        profile_id = _create_profile(client)
        resume_id = _create_resume(client, profile_id)
        with app.state.session_factory() as db_session:
            resume = ResumeService(db_session).get_resume(resume_id)
            section_id = resume.sections[0].id
            settings = SettingsService(db_session)
            settings.upsert_scoped_prompt_template(
                scope="profile",
                block_type="summary",
                user_prompt_template="Profile instruction",
                profile_id=profile_id,
            )
            settings.upsert_scoped_prompt_template(
                scope="resume",
                block_type="summary",
                user_prompt_template="Resume instruction",
                resume_id=resume_id,
            )
            settings.upsert_scoped_prompt_template(
                scope="section",
                block_type="summary",
                user_prompt_template="Section instruction",
                section_id=section_id,
            )
            assert (
                settings.get_prompt_instruction("summary", profile_id=profile_id)
                == "Profile instruction"
            )
            assert (
                settings.get_prompt_instruction(
                    "summary", profile_id=profile_id, resume_id=resume_id
                )
                == "Resume instruction"
            )
            assert (
                settings.get_prompt_instruction(
                    "summary",
                    profile_id=profile_id,
                    resume_id=resume_id,
                    section_id=section_id,
                )
                == "Section instruction"
            )
        prompt_page = client.get("/settings/prompts")
        assert "Protected safety rules<textarea" not in prompt_page.text


def test_work_experience_block_bullets_present_and_render(
    app_client: TestClient, session
):
    profile_id = _create_profile(app_client)
    resume_id = _create_resume(app_client, profile_id)
    resume = ResumeService(session).get_resume(resume_id)
    work_section = next(
        section
        for section in resume.sections
        if section.section_type == "work_experience"
    )
    block_response = app_client.post(
        f"/resumes/{resume_id}/blocks/new",
        data={
            "section_id": str(work_section.id),
            "block_type": "work_experience",
            "role_title": "Senior Backend Engineer",
            "organisation": "Local First Ltd",
            "start_date": "2024-01",
            "end_date": "",
            "is_current": "on",
            "ai_edit_enabled": "on",
            "is_visible": "on",
        },
        follow_redirects=False,
    )
    assert block_response.status_code == 303
    session.expire_all()
    resume = ResumeService(session).get_resume(resume_id)
    work_block = next(
        block
        for section in resume.sections
        for block in section.blocks
        if block.role_title == "Senior Backend Engineer"
    )
    bullet_response = app_client.post(
        f"/resumes/{resume_id}/blocks/{work_block.id}/bullets/new",
        data={
            "text": "Built profile-scoped FastAPI workflows.",
            "ai_edit_enabled": "on",
            "fact_link_required": "on",
        },
        follow_redirects=False,
    )
    assert bullet_response.status_code == 303
    session.expire_all()
    builder = app_client.get(f"/resumes/{resume_id}")
    assert "Senior Backend Engineer" in builder.text
    assert "Present" in builder.text
    rendered = render_resume_markdown(ResumeService(session).get_resume(resume_id))
    assert "## WORK EXPERIENCE" in rendered
    assert "Built profile-scoped FastAPI workflows." in rendered
