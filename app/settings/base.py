from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class SettingsBase(DeclarativeBase):
    """SQLAlchemy metadata boundary for the app-level settings database."""
