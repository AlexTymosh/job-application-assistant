"""add application artefact directory name

Revision ID: 0002_add_application_artifact_dir_name
Revises: 0001_initial_application_tables
Create Date: 2026-05-14 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002_add_application_artifact_dir_name"
down_revision: str | None = "0001_initial_application_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "applications",
        sa.Column("artifact_dir_name", sa.String(length=160), nullable=True),
    )
    op.create_index(
        op.f("ix_applications_artifact_dir_name"),
        "applications",
        ["artifact_dir_name"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_applications_artifact_dir_name"), table_name="applications")
    op.drop_column("applications", "artifact_dir_name")
