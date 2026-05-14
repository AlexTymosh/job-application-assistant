from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class SetupCheck(BaseModel):
    model_config = ConfigDict(frozen=True)

    code: str
    label: str
    ok: bool
    message: str
    action_hint: str | None = None


class SetupStatus(BaseModel):
    model_config = ConfigDict(frozen=True)

    checks: list[SetupCheck]

    @property
    def is_complete(self) -> bool:
        return all(check.ok for check in self.checks)
