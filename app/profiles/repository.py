from __future__ import annotations

from pathlib import Path

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.profiles.models import ManagedProfile
from app.profiles.schema import ManagedProfileRecord, ManagedProfileType


class DuplicateProfileNameError(ValueError):
    pass


class ManagedProfileRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def create_profile(
        self,
        *,
        profile_id: str,
        name: str,
        display_name: str | None,
        profile_type: ManagedProfileType,
        data_dir: Path,
        is_active: bool,
    ) -> ManagedProfileRecord:
        with self._session_factory() as session:
            if is_active:
                session.execute(update(ManagedProfile).values(is_active=False))
            row = ManagedProfile(
                id=profile_id,
                name=name,
                display_name=display_name,
                profile_type=profile_type.value,
                data_dir=data_dir.as_posix(),
                is_active=is_active,
            )
            session.add(row)
            try:
                session.commit()
            except IntegrityError as exc:
                session.rollback()
                raise DuplicateProfileNameError(
                    f"A managed profile named {name!r} already exists."
                ) from exc
            session.refresh(row)
            return _record_from_row(row)

    def list_profiles(self) -> list[ManagedProfileRecord]:
        with self._session_factory() as session:
            rows = session.scalars(select(ManagedProfile).order_by(ManagedProfile.name))
            return [_record_from_row(row) for row in rows]

    def get_profile(self, profile_id: str) -> ManagedProfileRecord | None:
        with self._session_factory() as session:
            row = session.get(ManagedProfile, profile_id)
            return _record_from_row(row) if row is not None else None

    def get_active_profile(self) -> ManagedProfileRecord | None:
        with self._session_factory() as session:
            row = session.scalar(
                select(ManagedProfile).where(ManagedProfile.is_active.is_(True))
            )
            return _record_from_row(row) if row is not None else None

    def set_active_profile(self, profile_id: str) -> ManagedProfileRecord:
        with self._session_factory() as session:
            row = session.get(ManagedProfile, profile_id)
            if row is None:
                raise ValueError("Managed profile was not found.")
            session.execute(update(ManagedProfile).values(is_active=False))
            row.is_active = True
            session.commit()
            session.refresh(row)
            return _record_from_row(row)


def _record_from_row(row: ManagedProfile) -> ManagedProfileRecord:
    return ManagedProfileRecord(
        id=row.id,
        name=row.name,
        display_name=row.display_name,
        profile_type=ManagedProfileType(row.profile_type),
        data_dir=Path(row.data_dir),
        is_active=bool(row.is_active),
    )
