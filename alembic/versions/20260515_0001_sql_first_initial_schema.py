"""SQL-first initial schema placeholder.

The local application currently uses deterministic SQLAlchemy metadata creation for
fresh app data folders. This revision documents the clean reset point for future
Alembic-managed migrations.
"""

from __future__ import annotations

revision = "20260515_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
