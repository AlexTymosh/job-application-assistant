from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Fact, PersonProfile, ProfileContact


class PeopleService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_profiles(self) -> list[PersonProfile]:
        return list(self.session.scalars(select(PersonProfile).order_by(PersonProfile.display_name)))

    def create_profile(self, display_name: str, full_name: str = "", location: str = "") -> PersonProfile:
        profile = PersonProfile(display_name=display_name, full_name=full_name, location=location)
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
        return list(self.session.scalars(select(Fact).where(Fact.profile_id == profile_id).order_by(Fact.fact_key)))
