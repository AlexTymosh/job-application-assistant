from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict


class ManagedProfileType(StrEnum):
    FILE_BASED = "file_based"


class ManagedProfileRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    display_name: str | None = None
    profile_type: ManagedProfileType = ManagedProfileType.FILE_BASED
    data_dir: Path
    is_active: bool = False


class ProfileValidationResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    ok: bool
    message: str
