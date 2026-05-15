from __future__ import annotations

from sqlalchemy.orm import Session, sessionmaker

from app.managed_cv.repository import ManagedCvRepository


def build_managed_cv_repository(
    session_factory: sessionmaker[Session],
) -> ManagedCvRepository:
    return ManagedCvRepository(session_factory)
