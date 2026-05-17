from __future__ import annotations

from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.applications.service import ApplicationService
from app.core.errors import NotFoundError, ProfileScopeError
from app.db.models import (
    Fact,
    PersonProfile,
    ProfileContact,
    PromptTemplate,
    Resume,
    ResumeBlock,
    ResumeBlockFactLink,
    ResumeBullet,
    ResumeBulletFactLink,
    ResumeSection,
    ResumeUpload,
)
from app.settings.service import SettingsService


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
            raise NotFoundError("Profile not found.")
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
        self, profile_id: int, *, confirmation: str, app_data_root: Path | None = None
    ) -> None:
        profile = self.session.get(PersonProfile, profile_id)
        if profile is None:
            raise NotFoundError("Profile not found.")
        if confirmation != profile.display_name:
            raise ProfileScopeError(
                "Type the profile display name to confirm deletion."
            )

        ApplicationService(self.session).delete_profile_applications(
            profile_id, app_data_root=app_data_root
        )
        resume_ids = list(
            self.session.scalars(
                select(Resume.id).where(Resume.profile_id == profile_id)
            )
        )
        section_ids: list[int] = []
        block_ids: list[int] = []
        bullet_ids: list[int] = []
        upload_paths: list[str] = []
        if resume_ids:
            section_ids = list(
                self.session.scalars(
                    select(ResumeSection.id).where(
                        ResumeSection.resume_id.in_(resume_ids)
                    )
                )
            )
        if section_ids:
            block_ids = list(
                self.session.scalars(
                    select(ResumeBlock.id).where(
                        ResumeBlock.section_id.in_(section_ids)
                    )
                )
            )
        if block_ids:
            bullet_ids = list(
                self.session.scalars(
                    select(ResumeBullet.id).where(ResumeBullet.block_id.in_(block_ids))
                )
            )
            upload_paths = list(
                self.session.scalars(
                    select(ResumeUpload.relative_path).where(
                        ResumeUpload.resume_id.in_(resume_ids)
                    )
                )
            )
        if app_data_root is not None:
            root = app_data_root.resolve()
            for relative_path in upload_paths:
                path = (root / relative_path).resolve()
                if (root in path.parents or path == root) and path.exists():
                    path.unlink()
        if bullet_ids:
            self.session.execute(
                delete(ResumeBulletFactLink).where(
                    ResumeBulletFactLink.bullet_id.in_(bullet_ids)
                )
            )
        if block_ids:
            self.session.execute(
                delete(ResumeBlockFactLink).where(
                    ResumeBlockFactLink.block_id.in_(block_ids)
                )
            )
        if resume_ids:
            self.session.execute(
                delete(PromptTemplate).where(
                    (PromptTemplate.profile_id == profile_id)
                    | (PromptTemplate.resume_id.in_(resume_ids))
                    | (PromptTemplate.section_id.in_(section_ids or [-1]))
                )
            )
        else:
            self.session.execute(
                delete(PromptTemplate).where(PromptTemplate.profile_id == profile_id)
            )
        active_profile_id = SettingsService(self.session).get_active_profile_id()
        self.session.delete(profile)
        if active_profile_id == profile_id:
            SettingsService(self.session).set_active_profile(None)
        self.session.commit()
