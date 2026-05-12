from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Application


def find_duplicate_by_job_text_hash(
    *,
    session: Session,
    profile_name: str,
    job_text_hash: str | None,
) -> Application | None:
    if job_text_hash is None:
        return None

    statement = (
        select(Application)
        .where(Application.profile_name == profile_name)
        .where(Application.job_text_hash == job_text_hash)
        .order_by(Application.created_at.desc())
    )

    return session.scalars(statement).first()
