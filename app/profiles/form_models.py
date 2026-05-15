from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ConnectProfileForm(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    display_name: str | None = None
    data_dir: str
    make_active: bool = False
