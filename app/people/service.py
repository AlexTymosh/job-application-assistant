from __future__ import annotations

from pathlib import Path

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError, ValidationAppError
from app.db.models import (
    Application,
    Artifact,
    Fact,
    PersonProfile,
    ProfileContact,
    PromptTemplate,
    Resume,
    ResumeSection,
    ResumeUpload,
)


class PeopleService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_profiles(self) -> list[PersonProfile]:
        return list(
            self.session.scalars(
                select(PersonProfile).order_by(PersonProfile.display_name)
            )
        )

    def create_profile(
        self, display_name: str, full_name: str = "", location: str = ""
    ) -> PersonProfile:
        profile = PersonProfile(
            display_name=display_name, full_name=full_name, location=location
        )
        profile.contact = ProfileContact()
        self.session.add(profile)
        self.session.commit()
        return profile

    def update_profile(
        self,
        profile_id: int,
        *,
        display_name: str,
        full_name: str,
        preferred_name: str,
        location: str,
        email: str,
        phone: str,
        address_line: str,
        city: str,
        country: str,
    ) -> PersonProfile:
        profile = self.session.get(PersonProfile, profile_id)
        if profile is None:
            raise ValueError("Profile not found.")
        profile.display_name = display_name
        profile.full_name = full_name
        profile.preferred_name = preferred_name
        profile.location = location
        if profile.contact is None:
            profile.contact = ProfileContact(profile_id=profile.id)
        profile.contact.email = email
        profile.contact.phone = phone
        profile.contact.address_line = address_line
        profile.contact.city = city
        profile.contact.country = country
        self.session.commit()
        return profile

    def create_fact(
        self,
        profile_id: int,
        *,
        fact_key: str,
        category: str,
        claim: str,
        evidence: str,
        source: str,
        allowed_claim_level: str,
    ) -> Fact:
        fact = Fact(
            profile_id=profile_id,
            fact_key=fact_key,
            category=category,
            claim=claim,
            evidence=evidence,
            source=source,
            allowed_claim_level=allowed_claim_level,
        )
        self.session.add(fact)
        self.session.commit()
        return fact

    def list_facts(self, profile_id: int) -> list[Fact]:
        return list(
            self.session.scalars(
                select(Fact)
                .where(Fact.profile_id == profile_id)
                .order_by(Fact.fact_key)
            )
        )

    def delete_profile(
        self, profile_id: int, app_data_root: Path | None = None
    ) -> None:
        profile = self.session.get(PersonProfile, profile_id)
        if profile is None:
            raise NotFoundError("Profile not found.")
        if app_data_root is not None:
            self._delete_profile_files(profile_id, app_data_root)
        resume_ids = [resume.id for resume in profile.resumes]
        section_ids = list(
            self.session.scalars(
                select(ResumeSection.id).where(ResumeSection.resume_id.in_(resume_ids))
            )
        )
        prompt_conditions = [PromptTemplate.profile_id == profile_id]
        if resume_ids:
            prompt_conditions.append(PromptTemplate.resume_id.in_(resume_ids))
        if section_ids:
            prompt_conditions.append(PromptTemplate.section_id.in_(section_ids))
        self.session.execute(delete(PromptTemplate).where(or_(*prompt_conditions)))
        self.session.delete(profile)
        self.session.commit()

    def require_delete_confirmation(self, profile_id: int, confirmation: str) -> None:
        profile = self.session.get(PersonProfile, profile_id)
        if profile is None:
            raise NotFoundError("Profile not found.")
        if confirmation.strip() != profile.display_name:
            raise ValidationAppError(
                "Type the profile display name to confirm deletion."
            )

    def _delete_profile_files(self, profile_id: int, app_data_root: Path) -> None:
        root = app_data_root.resolve()
        resume_ids = select(Resume.id).where(Resume.profile_id == profile_id)
        application_ids = select(Application.id).where(
            Application.profile_id == profile_id
        )
        uploads = list(
            self.session.scalars(
                select(ResumeUpload).where(ResumeUpload.resume_id.in_(resume_ids))
            )
        )
        artifacts = list(
            self.session.scalars(
                select(Artifact).where(Artifact.application_id.in_(application_ids))
            )
        )
        relative_paths = [
            *(item.relative_path for item in uploads),
            *(item.relative_path for item in artifacts),
        ]
        for relative_path in relative_paths:
            path = (root / relative_path).resolve()
            if root in path.parents and path.exists():
                path.unlink()
