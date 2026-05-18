from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import NotFoundError, ProfileScopeError, ValidationAppError
from app.db.models import MasterCV, MasterCVEntry, PersonProfile, ProfileContact

AI_SAFE_MASTER_CV_CATEGORIES = {"summary", "skills", "work_experience", "education"}


class PeopleService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_profiles(self) -> list[PersonProfile]:
        return list(
            self.session.scalars(
                select(PersonProfile).order_by(PersonProfile.display_name)
            )
        )

    def get_profile(self, profile_id: int) -> PersonProfile:
        profile = self.session.scalar(
            select(PersonProfile)
            .where(PersonProfile.id == profile_id)
            .options(
                selectinload(PersonProfile.contact),
                selectinload(PersonProfile.master_cv).selectinload(MasterCV.entries),
            )
        )
        if profile is None:
            raise NotFoundError("Profile not found.")
        return profile

    def create_profile(
        self, display_name: str, full_name: str = "", preferred_name: str = ""
    ) -> PersonProfile:
        first_name, surname = _split_name(full_name or display_name)
        profile = PersonProfile(
            display_name=display_name.strip() or full_name.strip() or "Profile",
            full_name=full_name.strip(),
            preferred_name=preferred_name.strip(),
            first_name=first_name,
            surname=surname,
        )
        self.session.add(profile)
        self.session.flush()
        self.session.add(
            ProfileContact(
                profile_id=profile.id, first_name=first_name, surname=surname
            )
        )
        self.session.add(MasterCV(profile_id=profile.id, title="Master CV"))
        self.session.commit()
        return profile

    def update_profile(
        self,
        profile_id: int,
        *,
        display_name: str,
        full_name: str = "",
        preferred_name: str = "",
        location: str = "",
        email: str = "",
        phone: str = "",
        address_line: str = "",
        city: str = "",
        country: str = "",
        linkedin_url: str = "",
        github_url: str = "",
        extra_text: str = "",
    ) -> PersonProfile:
        profile = self.get_profile(profile_id)
        first_name, surname = _split_name(full_name or display_name)
        profile.display_name = display_name.strip() or profile.display_name
        profile.full_name = full_name.strip()
        profile.preferred_name = preferred_name.strip()
        profile.first_name = first_name
        profile.surname = surname
        profile.location = location.strip() or profile.location
        contact = profile.contact or ProfileContact(profile_id=profile.id)
        contact.first_name = first_name
        contact.surname = surname
        contact.location = location.strip() or ", ".join(
            part for part in [city, country] if part
        )
        contact.email = email.strip()
        contact.phone = phone.strip()
        contact.address_line = address_line.strip()
        contact.city = city.strip()
        contact.country = country.strip()
        contact.linkedin_url = linkedin_url.strip()
        contact.github_url = github_url.strip()
        contact.extra_text = extra_text.strip()
        self.session.add(contact)
        self.session.commit()
        return profile

    def get_or_create_master_cv(self, profile_id: int) -> MasterCV:
        profile = self.get_profile(profile_id)
        if profile.master_cv is not None:
            return profile.master_cv
        master_cv = MasterCV(profile_id=profile.id, title="Master CV")
        self.session.add(master_cv)
        self.session.commit()
        return master_cv

    def list_master_entries(
        self, profile_id: int, *, ai_safe_only: bool = False
    ) -> list[MasterCVEntry]:
        master_cv = self.get_or_create_master_cv(profile_id)
        stmt = select(MasterCVEntry).where(MasterCVEntry.master_cv_id == master_cv.id)
        if ai_safe_only:
            stmt = stmt.where(MasterCVEntry.category.in_(AI_SAFE_MASTER_CV_CATEGORIES))
        return list(
            self.session.scalars(
                stmt.order_by(MasterCVEntry.display_order, MasterCVEntry.id)
            )
        )

    def create_master_entry(
        self,
        profile_id: int,
        *,
        category: str,
        title: str,
        content: str,
        keywords: str = "",
        allowed_wording: str = "",
        forbidden_wording: str = "",
        inference_notes: str = "",
        claim_strength: str = "normal",
    ) -> MasterCVEntry:
        master_cv = self.get_or_create_master_cv(profile_id)
        display_order = len(master_cv.entries) * 10 + 10
        entry = MasterCVEntry(
            master_cv_id=master_cv.id,
            category=category.strip() or "work_experience",
            title=title.strip(),
            content=content.strip(),
            keywords_json=[
                item.strip() for item in keywords.split(",") if item.strip()
            ],
            allowed_wording=allowed_wording.strip(),
            forbidden_wording=forbidden_wording.strip(),
            inference_notes=inference_notes.strip(),
            claim_strength=claim_strength,
            display_order=display_order,
        )
        self.session.add(entry)
        self.session.commit()
        return entry

    def get_profile_master_entry(
        self, profile_id: int, entry_id: int, *, ai_safe_only: bool = False
    ) -> MasterCVEntry:
        master_cv = self.get_or_create_master_cv(profile_id)
        entry = self.session.get(MasterCVEntry, entry_id)
        if entry is None or entry.master_cv_id != master_cv.id:
            raise ProfileScopeError(
                "Master CV entry not found in this profile workspace."
            )
        if ai_safe_only and entry.category not in AI_SAFE_MASTER_CV_CATEGORIES:
            raise ProfileScopeError(
                "This legacy Master CV item is not editable in the AI source workspace."
            )
        return entry

    def update_master_entry(self, entry_id: int, **values: str) -> MasterCVEntry:
        entry = self.session.get(MasterCVEntry, entry_id)
        if entry is None:
            raise NotFoundError("Master CV entry not found.")
        for field in [
            "category",
            "title",
            "content",
            "allowed_wording",
            "forbidden_wording",
            "inference_notes",
            "claim_strength",
        ]:
            if field in values:
                setattr(entry, field, values[field].strip())
        if "keywords" in values:
            entry.keywords_json = [
                item.strip() for item in values["keywords"].split(",") if item.strip()
            ]
        self.session.commit()
        return entry

    def delete_master_entry(self, entry_id: int, *, confirm: str) -> None:
        if confirm != "delete":
            raise ValidationAppError(
                "Tick the delete confirmation before deleting this Master CV item."
            )
        entry = self.session.get(MasterCVEntry, entry_id)
        if entry is None:
            raise NotFoundError("Master CV entry not found.")
        self.session.delete(entry)
        self.session.commit()

    def require_delete_confirmation(self, profile_id: int, confirmation: str) -> None:
        profile = self.get_profile(profile_id)
        if confirmation.strip() != profile.display_name:
            raise ValidationAppError(
                "Type the profile display name to confirm deletion."
            )

    def delete_profile(
        self, profile_id: int, app_data_root: Path | None = None
    ) -> None:
        profile = self.get_profile(profile_id)
        self.session.delete(profile)
        self.session.commit()


def _split_name(value: str) -> tuple[str, str]:
    parts = value.strip().split()
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], " ".join(parts[1:])
