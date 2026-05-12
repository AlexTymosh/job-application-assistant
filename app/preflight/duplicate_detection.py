from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Application


def find_duplicate_by_job_text_hash(
    *,
    session: Session,
    profile_name: str,
    job_text_hash: str | None,
    exclude_application_id: UUID | None = None,
) -> Application | None:
    if job_text_hash is None:
        return None

    statement = (
        select(Application)
        .where(Application.profile_name == profile_name)
        .where(Application.job_text_hash == job_text_hash)
    )

    if exclude_application_id is not None:
        statement = statement.where(Application.id != exclude_application_id)

    statement = statement.order_by(Application.created_at.desc())

    return session.scalars(statement).first()
